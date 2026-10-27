"""Desktop launches must find Harness tools without a developer terminal PATH."""

from pathlib import Path
import json

import pytest

from sukuna_pet import bridge_install as bridge


def runtime_at(home: Path) -> tuple[Path, Path]:
    dependencies = home / "dsh-runtimes/dsh-primary-runtime/dependencies"
    node = dependencies / "node/bin/node.exe"
    pnpm = dependencies / "pnpm/bin/pnpm.mjs"
    for path in (node, pnpm):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// tool fixture", encoding="utf-8")
    return node, pnpm


def test_preflight_uses_harness_runtime_without_terminal_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "DeepSeek home with spaces"
    node, pnpm = runtime_at(home)
    profile = home / "profiles/desktop"
    profile.mkdir(parents=True)
    manifest = profile / "package.json"
    manifest.write_text(json.dumps({"private": True}), encoding="utf-8")
    before = manifest.read_bytes()
    monkeypatch.setenv("DSH_HOME", str(home))
    monkeypatch.delenv("SUKUNA_PET_PNPM_CLI", raising=False)
    monkeypatch.delenv("DSH_PNPM_BIN", raising=False)
    monkeypatch.setattr(bridge, "_which", lambda name: None)
    plan = bridge.BridgeInstaller(data_dir=tmp_path / "data").preflight()
    assert plan.pnpm == pnpm.resolve()
    assert Path(plan.node) == node.resolve()
    assert plan.profiles == (profile.resolve(),)
    assert manifest.read_bytes() == before


def test_runtime_defaults_to_user_dsh_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, pnpm = runtime_at(tmp_path / ".dsh")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.delenv("DSH_HOME", raising=False)
    monkeypatch.delenv("SUKUNA_PET_PNPM_CLI", raising=False)
    monkeypatch.delenv("DSH_PNPM_BIN", raising=False)
    monkeypatch.setattr(bridge, "_which", lambda name: None)
    assert bridge.pnpm_cli() == pnpm.resolve()


@pytest.mark.parametrize("hint_kind", ["file", "directory", "invalid"])
def test_pnpm_hint_and_runtime_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hint_kind: str,
) -> None:
    _, runtime_pnpm = runtime_at(tmp_path)
    explicit = tmp_path / "chosen tools/pnpm.cjs"
    explicit.parent.mkdir()
    explicit.write_text("// explicit tool", encoding="utf-8")
    hint = explicit if hint_kind == "file" else explicit.parent
    if hint_kind == "invalid":
        hint = tmp_path / "removed-pnpm.cjs"
    monkeypatch.setenv("DSH_HOME", str(tmp_path))
    monkeypatch.setenv("SUKUNA_PET_PNPM_CLI", str(hint))
    monkeypatch.delenv("DSH_PNPM_BIN", raising=False)
    monkeypatch.setattr(bridge, "_which", lambda name: None)
    assert bridge.pnpm_cli() == (runtime_pnpm if hint_kind == "invalid" else explicit).resolve()
