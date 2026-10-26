"""Public release commands keep an accepted installer separate from a candidate."""

from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_invalid_compiler_does_not_write_candidate_or_existing_delivery(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted" / "Setup.exe"
    accepted.parent.mkdir()
    accepted.write_bytes(b"previous accepted installer")
    candidate = tmp_path / "candidate"
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/build_release.py"),
         "--output-root", str(candidate), "--iscc", str(tmp_path / "missing.exe")],
        capture_output=True,
    )
    assert result.returncode != 0 and b"FileNotFoundError" in result.stderr
    assert not candidate.exists()
    assert accepted.read_bytes() == b"previous accepted installer"


def test_release_rejects_a_bundle_missing_the_host_adapter(tmp_path: Path) -> None:
    release = runpy.run_path(str(ROOT / "tools/build_release.py"))
    package = tmp_path / "_internal" / "sukuna_pet"
    source = ROOT / "src" / "sukuna_pet"
    shutil.copytree(source / "assets", package / "assets")
    plugin = package / "integrations" / "dsh-bridge"
    shutil.copytree(source / "integrations" / "dsh-bridge", plugin)
    (plugin / "host-state.js").unlink()
    with pytest.raises(RuntimeError, match="host-state.js"):
        release["check_bundle"](tmp_path)

