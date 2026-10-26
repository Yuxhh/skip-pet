"""Agreed public installation boundary: a real profile, never a new one."""

import json
from pathlib import Path
import shutil
import subprocess
import os

import pytest

from sukuna_pet.bridge_install import BridgeInstaller, PLUGIN


def profile_at(root: Path, name: str = "desktop") -> Path:
    profile = root / "profiles" / name
    profile.mkdir(parents=True)
    (profile / "package.json").write_text(json.dumps({
        "name": f"dsh-profile-{name}", "private": True,
        "dependencies": {},
        "dsh": {"profile": {"bundles": ["@deepseek-ai/dsh-base"]}},
    }), encoding="utf-8")
    return profile


def test_preflight_identifies_existing_desktop_and_never_creates_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "dsh"))
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    with pytest.raises(FileNotFoundError, match="desktop"):
        installer.preflight()
    assert not (tmp_path / "dsh").exists()
    desktop = profile_at(tmp_path / "dsh")
    profile_at(tmp_path / "dsh", "unrelated")
    before = (desktop / "package.json").read_bytes()
    plan = installer.preflight()
    assert plan.profiles == (desktop.resolve(),)
    assert plan.node and plan.pnpm.is_file() and (plan.plugin / "index.js").is_file()
    assert str(desktop) in plan.description
    assert (desktop / "package.json").read_bytes() == before


def test_install_backs_up_and_registers_only_own_bundle(tmp_path: Path) -> None:
    profile = profile_at(tmp_path)
    before = (profile / "package.json").read_bytes()
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    result = installer.install(installer.preflight((profile,)))
    assert result.ok, result.message
    state = installer.inspect(profile)
    assert state.registered and state.target == installer.plugin.resolve() and state.owned
    assert state.bundles == ("@deepseek-ai/dsh-base", PLUGIN)
    assert result.results[0].backup.joinpath("package.json").read_bytes() == before
    assert "重开" in result.message


def test_refresh_repairs_old_build_but_does_not_install_or_replace_registry(tmp_path: Path) -> None:
    profile = profile_at(tmp_path)
    empty = profile_at(tmp_path, "empty")
    registry = profile_at(tmp_path, "registry")
    value = json.loads((registry / "package.json").read_text())
    value["dependencies"][PLUGIN] = "^9.0.0"
    (registry / "package.json").write_text(json.dumps(value))
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    assert installer.install(installer.preflight((profile,))).ok
    relocated = tmp_path / "new build" / "dsh-bridge"
    shutil.copytree(installer.plugin, relocated)
    upgraded = BridgeInstaller(data_dir=tmp_path / "data", plugin=relocated)
    result = upgraded.refresh((profile, empty, registry))
    assert result.ok, result.message
    assert upgraded.inspect(profile).target == relocated.resolve()
    assert not upgraded.inspect(empty).dependency
    assert upgraded.inspect(registry).dependency == "^9.0.0"


def test_install_rejects_changes_since_confirmation_without_overwriting(tmp_path: Path) -> None:
    profile = profile_at(tmp_path)
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    plan = installer.preflight((profile,))
    path = profile / "package.json"
    value = json.loads(path.read_text())
    value["user-added"] = "keep this"
    path.write_text(json.dumps(value))
    result = installer.install(plan)
    assert not result.ok and "预检后已变化" in result.message
    assert not installer.inspect(profile).dependency
    assert json.loads(path.read_text())["user-added"] == "keep this"


def test_remove_keeps_shared_plugin_then_falls_back_without_pnpm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = profile_at(tmp_path)
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    assert installer.install(installer.preflight((profile,))).ok
    lease = installer.acquire_use((profile,))
    try:
        kept = installer.remove((profile,))
        assert kept.ok and "其他实例" in kept.message
        assert installer.inspect(profile).registered
    finally:
        lease.close()
    # Explorer can lose PATH, or pnpm can be removed after installation.
    monkeypatch.setenv("PATH", "")
    removed = installer.remove((profile,))
    assert removed.ok, removed.message
    assert not installer.inspect(profile).dependency and not installer.inspect(profile).registered
    assert installer.inspect(profile).bundles == ("@deepseek-ai/dsh-base",)
    assert installer.plugin.joinpath("index.js").is_file()


def test_remove_preserves_dependency_user_changed_after_install(tmp_path: Path) -> None:
    profile = profile_at(tmp_path)
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    assert installer.install(installer.preflight((profile,))).ok
    path = profile / "package.json"
    value = json.loads(path.read_text())
    value["dependencies"][PLUGIN] = "^10.0.0"
    value["user-new-setting"] = "keep"
    path.write_text(json.dumps(value))
    result = installer.remove((profile,))
    assert result.ok and "用户" in result.message
    assert installer.inspect(profile).dependency == "^10.0.0"
    assert json.loads(path.read_text())["user-new-setting"] == "keep"


def test_partial_failure_reports_backup_and_retry_preserves_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    good = profile_at(tmp_path)
    bad = profile_at(tmp_path, "second")
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    real_run = subprocess.run

    def fail_second(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if kwargs["cwd"] == bad:
            return subprocess.CompletedProcess(command, 1, "ERR_PNPM_TEST injected failure", "")
        return real_run(command, **kwargs)  # type: ignore[call-overload,no-any-return]

    monkeypatch.setattr(subprocess, "run", fail_second)
    result = installer.install(installer.preflight((good, bad)))
    assert not result.ok and result.results[0].ok and not result.results[1].ok
    assert result.results[1].backup.joinpath("package.json").is_file()
    assert installer.inspect(good).registered and not installer.inspect(bad).registered
    monkeypatch.setattr(subprocess, "run", real_run)
    retry = installer.install(installer.preflight((bad,)))
    assert retry.ok and installer.inspect(good).registered and installer.inspect(bad).registered


def test_broken_foreign_dependency_is_named_without_rewriting_it(tmp_path: Path) -> None:
    profile = profile_at(tmp_path)
    path = profile / "package.json"
    value = json.loads(path.read_text())
    value["dependencies"]["other-plugin"] = "file:./missing-plugin.tgz"
    path.write_text(json.dumps(value))
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    result = installer.install(installer.preflight((profile,)))
    assert not result.ok and "other-plugin" in result.message
    assert json.loads(path.read_text())["dependencies"]["other-plugin"] == "file:./missing-plugin.tgz"


def test_refresh_repairs_a_missing_owned_target(tmp_path: Path) -> None:
    from sukuna_pet.bridge_install import OWNER_FILE

    profile = profile_at(tmp_path)
    path = profile / "package.json"
    value = json.loads(path.read_text())
    missing = "link:../../deleted-build/dsh-bridge"
    value["dependencies"][PLUGIN] = missing
    value["dsh"]["profile"]["bundles"].append(PLUGIN)
    path.write_text(json.dumps(value))
    (profile / OWNER_FILE).write_text(json.dumps({"dependency": missing}))
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    result = installer.refresh((profile,))
    assert result.ok, result.message
    assert installer.inspect(profile).target == installer.plugin.resolve()


def test_startup_repairs_missing_physical_plugin_link(tmp_path: Path) -> None:
    profile = profile_at(tmp_path)
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    assert installer.install(installer.preflight((profile,))).ok
    link = profile / "node_modules/@sukuna-pet/dsh-bridge"
    if link.is_symlink():
        link.unlink()
    else:
        assert link.is_junction()
        link.rmdir()
    report = installer.refresh((profile,))
    assert report.ok and link.joinpath("index.js").is_file(), report.message


def test_remove_can_retry_after_pnpm_succeeded_but_bundle_write_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = profile_at(tmp_path)
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    assert installer.install(installer.preflight((profile,))).ok
    real_replace = os.replace

    def denied(source: Path, destination: Path) -> None:
        if Path(destination) == profile / "package.json":
            raise PermissionError("injected bundle write failure")
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", denied)
    failed = installer.remove((profile,))
    assert not failed.ok and "injected" in failed.message
    monkeypatch.setattr(os, "replace", real_replace)
    retry = installer.remove((profile,))
    assert retry.ok and not installer.inspect(profile).registered, retry.message


def test_registry_override_with_missing_actual_plugin_is_not_install_success(tmp_path: Path) -> None:
    profile = profile_at(tmp_path)
    path = profile / "package.json"
    value = json.loads(path.read_text())
    value["dependencies"][PLUGIN] = "^9.0.0"
    value["dsh"]["profile"]["bundles"].append(PLUGIN)
    path.write_text(json.dumps(value))
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    result = installer.install(installer.preflight((profile,)))
    assert not result.ok and "实际插件缺失" in result.message
    assert installer.inspect(profile).dependency == "^9.0.0"
