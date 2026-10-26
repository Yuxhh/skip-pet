"""Install/remove our bundled bridge in one existing desktop profile.

Like dsh-pet, call pnpm's JS entry directly and maintain dsh.profile.bundles.
This avoids Windows shell splitting of paths containing spaces. No global
package installation, profile creation, or unrelated dependency repairs.
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


PLUGIN = "@sukuna-pet/dsh-bridge"


def bundled_plugin() -> Path:
    return Path(__file__).resolve().parent / "integrations/dsh-bridge"


def desktop_profile() -> Path:
    return Path(os.environ.get("DSH_HOME", str(Path.home() / ".dsh"))) / "profiles/desktop"


def pnpm_cli() -> Path:
    for name in ("pnpm", "pnpm.cmd"):
        found = shutil.which(name)
        if not found:
            continue
        shim = Path(found).resolve()
        for parent in (shim.parent, *list(shim.parents)[:3]):
            for extension in ("mjs", "cjs", "js"):
                candidate = parent / f"node_modules/pnpm/bin/pnpm.{extension}"
                if candidate.is_file():
                    return candidate
        if shim.suffix.lower() == ".cmd":
            for raw in re.findall(r'"([^"\r\n]+\.(?:mjs|cjs|js))"', shim.read_text(encoding="utf-8")):
                raw = raw.replace("%~dp0", str(shim.parent) + os.sep).replace("%dp0%", str(shim.parent) + os.sep)
                candidate = Path(raw).resolve()
                if candidate.is_file():
                    return candidate
    raise FileNotFoundError("找不到 pnpm JS 入口；可用 --pnpm-cli 指定现有入口。")


def _read_manifest(profile: Path) -> dict[str, Any]:
    value = json.loads((profile / "package.json").read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("无效的 profile package.json")
    return value


def _set_bundle(profile: Path, present: bool) -> None:
    value = _read_manifest(profile)
    bundles = value.setdefault("dsh", {}).setdefault("profile", {}).setdefault("bundles", [])
    if not isinstance(bundles, list):
        raise ValueError("无效的 profile bundles")
    bundles[:] = [entry for entry in bundles if entry != PLUGIN]
    if present:
        bundles.append(PLUGIN)
    target = profile / "package.json"
    temporary = profile / "package.json.sukuna-tmp"
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, target)


def configure(profile: Path, *, remove: bool = False, node: str | None = None,
              pnpm: Path | None = None) -> Path:
    profile = profile.resolve(strict=True)
    _read_manifest(profile)
    node = node or shutil.which("node")
    if node is None:
        raise FileNotFoundError("找不到 Node.js")
    cli = pnpm if pnpm is not None else pnpm_cli()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = profile / f"sukuna-bridge-backup-{stamp}"
    backup.mkdir()
    for name in ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml"):
        if (profile / name).is_file():
            shutil.copy2(profile / name, backup / name)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    target = PLUGIN if remove else str(bundled_plugin())
    # No scripts, registry access or implicit global installation for this
    # dependency-free local bridge. Failure leaves backups and an explicit error.
    command = [node, str(cli), "remove" if remove else "add", target]
    if not remove:
        command.extend(("--offline", "--ignore-scripts"))
    environment = dict(os.environ, npm_config_ignore_scripts="true", npm_config_offline="true")
    result = subprocess.run(command, cwd=profile, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=120,
                            creationflags=flags, env=environment)
    if result.returncode:
        raise RuntimeError(f"pnpm 失败，备份在 {backup}\n{result.stdout[-1800:]}{result.stderr[-800:]}")
    _set_bundle(profile, not remove)
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "install", "remove"))
    parser.add_argument("--profile", type=Path, default=desktop_profile())
    parser.add_argument("--pnpm-cli", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "inspect":
            value = _read_manifest(args.profile)
            print(json.dumps({"profile": str(args.profile), "plugin": PLUGIN,
                              "bundled_plugin": str(bundled_plugin()),
                              "installed": value.get("dependencies", {}).get(PLUGIN),
                              "registered": PLUGIN in value.get("dsh", {}).get("profile", {}).get("bundles", [])},
                             ensure_ascii=False, indent=2))
        else:
            backup = configure(args.profile, remove=args.action == "remove", pnpm=args.pnpm_cli)
            print(f"{args.action}: 完成；配置备份：{backup}。请正常重开 Harness 以加载变更。")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
