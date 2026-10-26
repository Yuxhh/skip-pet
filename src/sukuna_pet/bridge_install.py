"""Install/remove our bundled bridge in one existing desktop profile.

Like dsh-pet, call pnpm's JS entry directly and maintain dsh.profile.bundles.
This avoids Windows shell splitting of paths containing spaces. No global
package installation, profile creation, or unrelated dependency repairs.
"""

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

from PySide6.QtCore import QLockFile, QStandardPaths


PLUGIN = "@sukuna-pet/dsh-bridge"
OWNER_FILE = ".sukuna-bridge.json"


class MaintenanceBusyError(RuntimeError):
    """Another process currently owns the bridge mutation boundary."""


@dataclass(frozen=True)
class ProfileState:
    profile: Path
    dependency: str
    target: Path | None
    bundles: tuple[str, ...]
    owned: bool

    @property
    def registered(self) -> bool:
        return PLUGIN in self.bundles


@dataclass(frozen=True)
class ProfileResult:
    profile: Path
    ok: bool
    detail: str
    backup: Path | None = None


@dataclass(frozen=True)
class InstallReport:
    results: tuple[ProfileResult, ...]

    @property
    def ok(self) -> bool:
        return all(result.ok for result in self.results)

    @property
    def message(self) -> str:
        rows = [f"{r.profile}: {r.detail}" + (f"；备份：{r.backup}" if r.backup else "")
                for r in self.results]
        return "\n".join(rows) + "\n请正常重开 DeepSeek Harness 使变更生效。"


@dataclass(frozen=True)
class InstallPlan:
    profiles: tuple[Path, ...]
    plugin: Path
    node: str
    pnpm: Path
    manifests: tuple[bytes, ...]

    @property
    def description(self) -> str:
        return ("将为以下现有 DeepSeek profile 安装本机状态桥：\n"
                + "\n".join(str(path) for path in self.profiles)
                + f"\n\n插件：{self.plugin}\nNode：{self.node}\npnpm：{self.pnpm}"
                + "\n\n修改 package.json、pnpm 锁文件及本项目安装记录；先备份配置。"
                + "\n只传任务身份和状态。安装后需正常重开 DeepSeek Harness。")


class BridgeUse:
    """A process-owned claim; QLockFile also detects crashed peer processes."""

    def __init__(self, directory: Path, profiles: tuple[Path, ...]) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"{uuid4().hex}.json"
        self.lock = QLockFile(str(self.path.with_suffix(".lock")))
        self.lock.setStaleLockTime(0)
        if not self.lock.tryLock(0):
            raise RuntimeError("无法登记桌宠接入占用")
        try:
            _write_json(self.path, {"profiles": [str(p.resolve()) for p in profiles]})
        except BaseException:
            self.lock.unlock()
            raise

    def close(self) -> None:
        self.path.unlink(missing_ok=True)
        self.lock.unlock()


class BridgeInstaller:
    def __init__(self, *, data_dir: Path, plugin: Path | None = None,
                 node: str | None = None, pnpm: Path | None = None) -> None:
        self.data_dir = data_dir
        self.plugin = plugin if plugin is not None else bundled_plugin()
        self.node = node
        self.pnpm = pnpm

    def preflight(self, profiles: tuple[Path, ...] | None = None) -> InstallPlan:
        selected = tuple(path.resolve() for path in (profiles or (desktop_profile(),)))
        manifests = []
        for profile in selected:
            _read_manifest(profile)
            manifests.append((profile / "package.json").read_bytes())
        _plugin_files(self.plugin)
        pnpm = self.pnpm if self.pnpm is not None else pnpm_cli()
        if not pnpm.is_file():
            raise FileNotFoundError(f"找不到 pnpm 入口：{pnpm}")
        node = self.node or _which("node") or ""
        if not node and pnpm.suffix.lower() != ".exe":
            raise FileNotFoundError("找不到 Node.js；请安装现有运行环境后重试。")
        return InstallPlan(selected, self.plugin.resolve(), node, pnpm, tuple(manifests))

    def inspect(self, profile: Path) -> ProfileState:
        value = _read_manifest(profile)
        dependency = str(value.get("dependencies", {}).get(PLUGIN, ""))
        bundles = value.get("dsh", {}).get("profile", {}).get("bundles", [])
        owner = _read_owner(profile)
        return ProfileState(profile, dependency, path_target(dependency, profile),
                            tuple(bundles), bool(owner.get("dependency")
                            and (not dependency or dependency in (owner.get("dependency"),
                                                                 owner.get("pending_dependency")))))

    def install(self, plan: InstallPlan) -> InstallReport:
        lock = self._lock()
        try:
            results = []
            for profile, original in zip(plan.profiles, plan.manifests, strict=True):
                backup = None
                try:
                    if (profile / "package.json").read_bytes() != original:
                        raise RuntimeError("配置在预检后已变化，请重新预检并确认。")
                    state = self.inspect(profile)
                    if state.dependency and state.target is None:
                        if not state.registered:
                            raise RuntimeError("保留用户指定的 registry 依赖；请先确认其 bundles 配置。")
                        if not (profile / "node_modules" / PLUGIN / "index.js").is_file():
                            raise RuntimeError("保留用户指定的 registry 依赖，但其实际插件缺失；请在该 profile 安装指定版本后重试。")
                        results.append(ProfileResult(profile, True, "保留用户指定的 registry 依赖"))
                        continue
                    backup = _backup(profile)
                    _run_pnpm(profile, plan.node, plan.pnpm, "add", str(plan.plugin))
                    installed = self.inspect(profile)
                    if installed.target != plan.plugin:
                        raise RuntimeError("pnpm 未建立预期的随包插件依赖")
                    _write_json(profile / OWNER_FILE, {"dependency": installed.dependency})
                    _set_bundle(profile, True)
                    results.append(ProfileResult(profile, True, "安装完成", backup))
                except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                    results.append(ProfileResult(profile, False, str(error), backup))
            return InstallReport(tuple(results))
        finally:
            lock.unlock()

    def refresh(self, profiles: tuple[Path, ...] | None = None) -> InstallReport:
        results: list[ProfileResult] = []
        for profile in profiles or (desktop_profile(),):
            try:
                state = self.inspect(profile)
                # Startup only maintains previously installed path dependencies.
                # A registry override is the user's choice, even with our marker.
                if state.target is None or not state.owned:
                    continue
                link = profile / "node_modules" / PLUGIN
                if (state.target == self.plugin.resolve() and state.target.is_dir() and state.registered
                        and (link / "index.js").is_file() and link.resolve() == state.target):
                    continue
                results.extend(self.install(self.preflight((profile,))).results)
            except (OSError, ValueError, RuntimeError) as error:
                results.append(ProfileResult(profile, False, str(error)))
        return InstallReport(tuple(results))

    def acquire_use(self, profiles: tuple[Path, ...]) -> BridgeUse:
        lock = self._lock()
        try:
            return BridgeUse(self.data_dir / "uses", profiles)
        finally:
            lock.unlock()

    def _in_use(self, profile: Path) -> bool:
        for path in (self.data_dir / "uses").glob("*.json"):
            lock = QLockFile(str(path.with_suffix(".lock")))
            lock.setStaleLockTime(0)
            if lock.tryLock(0):
                lock.unlock()
                path.unlink(missing_ok=True)
                continue
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if str(profile.resolve()) in value["profiles"]:
                    return True
            except (OSError, ValueError, KeyError, TypeError):
                return True  # Unreadable live claims are not permission to remove.
        return False

    def remove(self, profiles: tuple[Path, ...] | None = None, *,
               preserve_shared: bool = False) -> InstallReport:
        lock = self._lock()
        try:
            results = []
            for profile in profiles or (desktop_profile(),):
                backup = None
                try:
                    if not (profile / "package.json").exists():
                        results.append(ProfileResult(profile, True, "profile 已不存在"))
                        continue
                    state = self.inspect(profile)
                    if self._in_use(profile):
                        if preserve_shared and state.owned and state.target is not None:
                            backup = self._preserve_shared(profile, state)
                            results.append(ProfileResult(profile, True,
                                "其他实例仍在使用，已保留独立插件副本，卸载程序目录不影响共享链接", backup))
                        else:
                            results.append(ProfileResult(profile, True, "其他实例仍在使用，保留插件"))
                        continue
                    if not state.owned:
                        results.append(ProfileResult(profile, True, "保留用户修改或非本项目拥有的配置"))
                        continue
                    backup = _backup(profile)
                    try:
                        node = self.node or _which("node")
                        cli = self.pnpm if self.pnpm is not None else pnpm_cli()
                    except FileNotFoundError:
                        node, cli = None, None
                    if state.dependency and cli and cli.is_file() and (node or cli.suffix.lower() == ".exe"):
                        _run_pnpm(profile, node or "", cli, "remove", PLUGIN)
                    else:
                        # Read the latest file; never restore an old whole manifest.
                        value = _read_manifest(profile)
                        value.get("dependencies", {}).pop(PLUGIN, None)
                        _write_json(profile / "package.json", value)
                        link = profile / "node_modules/@sukuna-pet/dsh-bridge"
                        if link.is_symlink():
                            link.unlink()
                        elif link.is_junction():
                            link.rmdir()  # Remove only the junction, never its target.
                    _set_bundle(profile, False)
                    (profile / OWNER_FILE).unlink(missing_ok=True)
                    results.append(ProfileResult(profile, True, "移除完成", backup))
                except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                    results.append(ProfileResult(profile, False, str(error), backup))
            return InstallReport(tuple(results))
        finally:
            lock.unlock()

    def _preserve_shared(self, profile: Path, state: ProfileState) -> Path:
        assert state.target is not None
        backup = _backup(profile)
        files = _plugin_files(state.target)
        saved = self.data_dir / "preserved-bridge" / uuid4().hex
        saved.mkdir(parents=True)
        for name in files:
            source = (state.target / name).resolve()
            if not source.is_relative_to(state.target.resolve()) or not source.is_file():
                raise ValueError(f"共享插件文件不完整：{name}；备份：{backup}")
            destination = saved / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        if not (saved / "index.js").is_file():
            raise ValueError("共享插件缺少入口")
        value = _read_manifest(profile)
        if value.get("dependencies", {}).get(PLUGIN) != state.dependency:
            raise RuntimeError(f"共享配置在维护期间已改变；备份：{backup}")
        link = profile / "node_modules" / PLUGIN
        if link.exists() and link.resolve() != state.target:
            raise RuntimeError(f"共享插件链接在维护期间已改变；备份：{backup}")
        dependency = "link:" + saved.resolve().as_posix()
        # A migration journal proves ownership on either side of a partial
        # write. Publish it before changing the link or dependency manifest.
        _write_json(profile / OWNER_FILE, {"dependency": state.dependency,
                                          "pending_dependency": dependency})
        if link.is_symlink():
            link.unlink()
        elif link.is_junction():
            link.rmdir()
        elif link.exists():
            raise RuntimeError(f"插件入口不是本地链接，保留原目录；备份：{backup}")
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            from _winapi import CreateJunction
            CreateJunction(str(saved), str(link))
        else:
            link.symlink_to(saved, target_is_directory=True)
        value["dependencies"][PLUGIN] = dependency
        _write_json(profile / "package.json", value)
        _write_json(profile / OWNER_FILE, {"dependency": dependency})
        return backup

    def _lock(self) -> QLockFile:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(self.data_dir / "maintenance.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(1000):
            raise MaintenanceBusyError("另一个桌宠正在维护接入，请稍后重试。")
        return lock


def path_target(spec: str, profile: Path) -> Path | None:
    text = spec.strip()
    if text.startswith(("link:", "file:")):
        text = unquote(text.split(":", 1)[1])
        if text.startswith("///") and len(text) > 5 and text[4] == ":":
            text = text[3:]
    elif not re.match(r"^(?:\.{1,2}[\\/]|[\\/]|[A-Za-z]:[\\/])", text):
        return None
    path = Path(text)
    return (profile / path).resolve() if not path.is_absolute() else path.resolve()


def _plugin_files(plugin: Path) -> tuple[str, ...]:
    package = json.loads((plugin / "package.json").read_text(encoding="utf-8"))
    if not isinstance(package, dict) or package.get("name") != PLUGIN:
        raise ValueError("随包桥接插件身份不符")
    listed = package.get("files", [])
    if not isinstance(listed, list) or not all(isinstance(name, str) for name in listed):
        raise ValueError("随包桥接插件文件清单无效")
    names = tuple(dict.fromkeys(["package.json", "index.js", *listed]))
    for name in names:
        path = Path(name)
        source = (plugin / path).resolve()
        if (path.is_absolute() or ".." in path.parts or not source.is_relative_to(plugin.resolve())
                or not source.is_file()):
            raise ValueError(f"随包桥接插件文件不完整：{name}")
    return names


def _read_owner(profile: Path) -> dict[str, Any]:
    try:
        value = json.loads((profile / OWNER_FILE).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _backup(profile: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = profile / f"sukuna-bridge-backup-{stamp}"
    backup.mkdir()
    for name in ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", OWNER_FILE):
        if (profile / name).is_file():
            shutil.copy2(profile / name, backup / name)
    return backup


def _run_pnpm(profile: Path, node: str, cli: Path, action: str, target: str) -> None:
    command = ([str(cli)] if cli.suffix.lower() == ".exe" else [node, str(cli)]) + [action, target]
    if action == "add":
        command.extend(("--offline", "--ignore-scripts"))
    result = subprocess.run(command, cwd=profile, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                            env=dict(os.environ, npm_config_ignore_scripts="true", npm_config_offline="true"))
    if result.returncode:
        missing = []
        for name, spec in _read_manifest(profile).get("dependencies", {}).items():
            target_path = path_target(str(spec), profile)
            if target_path is not None and not target_path.exists():
                missing.append(f"{name} → {target_path}")
        hint = "\n缺失依赖路径（请核对后重试）：" + "；".join(missing) if missing else ""
        raise RuntimeError(f"pnpm {action} 失败：{result.stdout[-1400:]}{result.stderr[-800:]}{hint}")


def bundled_plugin() -> Path:
    return Path(__file__).resolve().parent / "integrations/dsh-bridge"


def desktop_profile() -> Path:
    return Path(os.environ.get("DSH_HOME", str(Path.home() / ".dsh"))) / "profiles/desktop"


def maintenance_directory() -> Path:
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)) / "sukuna-pet"


def pnpm_cli() -> Path:
    hint = os.environ.get("SUKUNA_PET_PNPM_CLI") or os.environ.get("DSH_PNPM_BIN")
    candidates = [Path(hint)] if hint else [Path(found) for name in ("pnpm", "pnpm.cmd", "pnpm.exe")
                                           if (found := _which(name))]
    for shim in candidates:
        shim = shim.expanduser().resolve()
        if shim.suffix.lower() in (".mjs", ".cjs", ".js", ".exe") and shim.is_file():
            return shim
        for parent in (shim.parent, *list(shim.parents)[:3]):
            for extension in ("mjs", "cjs", "js"):
                candidate = parent / f"node_modules/pnpm/bin/pnpm.{extension}"
                if candidate.is_file():
                    return candidate
        if shim.suffix.lower() == ".cmd" and shim.is_file():
            for raw in re.findall(r'"([^"\r\n]+\.(?:mjs|cjs|js))"', shim.read_text(encoding="utf-8")):
                raw = raw.replace("%~dp0", str(shim.parent) + os.sep).replace("%dp0%", str(shim.parent) + os.sep)
                candidate = Path(raw).resolve()
                if candidate.is_file():
                    return candidate
    raise FileNotFoundError("找不到 pnpm JS 入口；可用 --pnpm-cli 指定现有入口。")


def _which(name: str) -> str | None:
    """Keep the inherited PATH first, then inspect ordinary GUI tool locations."""
    entries = [os.environ.get("PATH", "")]
    if os.name == "nt":
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, "Environment"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
            try:
                with winreg.OpenKey(hive, key) as opened:
                    value, _ = winreg.QueryValueEx(opened, "Path")
                    entries.append(os.path.expandvars(str(value)))
            except OSError:
                pass
        for variable, suffix in (("APPDATA", "npm"), ("LOCALAPPDATA", "pnpm"),
                                 ("ProgramFiles", "nodejs"), ("LOCALAPPDATA", "Volta/bin"),
                                 ("NVM_SYMLINK", ""), ("PNPM_HOME", "")):
            if root := os.environ.get(variable):
                entries.append(str(Path(root) / suffix))
    return shutil.which(name, path=os.pathsep.join(entries))


def _read_manifest(profile: Path) -> dict[str, Any]:
    value = json.loads((profile / "package.json").read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("无效的 profile package.json")
    if not isinstance(value.get("dependencies", {}), dict):
        raise ValueError(f"无效的 dependencies：{profile}")
    dsh = value.get("dsh", {})
    if not isinstance(dsh, dict) or not isinstance(dsh.get("profile", {}), dict):
        raise ValueError(f"无效的 dsh.profile：{profile}")
    bundles = dsh.get("profile", {}).get("bundles", [])
    if not isinstance(bundles, list) or not all(isinstance(b, str) for b in bundles):
        raise ValueError(f"无效的 bundles：{profile}")
    return value


def _set_bundle(profile: Path, present: bool) -> None:
    value = _read_manifest(profile)
    bundles = value.setdefault("dsh", {}).setdefault("profile", {}).setdefault("bundles", [])
    bundles[:] = [entry for entry in bundles if entry != PLUGIN]
    if present:
        bundles.append(PLUGIN)
    _write_json(profile / "package.json", value)


def configure(profile: Path, *, remove: bool = False, node: str | None = None,
              pnpm: Path | None = None) -> Path | None:
    installer = BridgeInstaller(data_dir=maintenance_directory(), node=node, pnpm=pnpm)
    report = installer.remove((profile,)) if remove else installer.install(installer.preflight((profile,)))
    if not report.ok:
        raise RuntimeError(report.message)
    return report.results[0].backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "install", "refresh", "remove"))
    parser.add_argument("--profile", type=Path, action="append")
    parser.add_argument("--pnpm-cli", type=Path)
    parser.add_argument("--maintenance-dir", type=Path, default=maintenance_directory())
    args = parser.parse_args()
    try:
        profiles = tuple(args.profile or (desktop_profile(),))
        installer = BridgeInstaller(data_dir=args.maintenance_dir, pnpm=args.pnpm_cli)
        if args.action == "inspect":
            rows = []
            for profile in profiles:
                state = installer.inspect(profile)
                rows.append({"profile": str(profile), "plugin": PLUGIN,
                             "bundled_plugin": str(installer.plugin),
                             "installed": state.dependency, "registered": state.registered,
                             "owned": state.owned})
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            if args.action == "install":
                report = installer.install(installer.preflight(profiles))
            elif args.action == "refresh":
                report = installer.refresh(profiles)
            else:
                report = installer.remove(profiles)
            print(report.message)
            return 0 if report.ok else 1
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
