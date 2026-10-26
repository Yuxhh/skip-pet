"""Uninstall cleanup is callable without constructing a Qt application."""

import json
from pathlib import Path
import subprocess
import sys

from sukuna_pet.bridge_install import BridgeInstaller
from sukuna_pet.settings import save_bridge
from test_bridge_install import profile_at


def test_uninstall_entry_cleans_only_unclaimed_owned_bridge_and_leaves_diagnostics(tmp_path: Path) -> None:
    profile = profile_at(tmp_path)
    data = tmp_path / "data"
    installer = BridgeInstaller(data_dir=data)
    assert installer.install(installer.preflight((profile,))).ok
    settings = tmp_path / "mode.json"
    save_bridge(settings, True, (profile,))
    command = [sys.executable, "-m", "sukuna_pet", "--uninstall-cleanup",
               "--settings", str(settings), "--maintenance-dir", str(data)]
    lease = installer.acquire_use((profile,))
    try:
        kept = subprocess.run(command, capture_output=True, text=True, timeout=20)
        assert kept.returncode == 0, kept.stderr
        assert installer.inspect(profile).registered
    finally:
        lease.close()
    removed = subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert removed.returncode == 0, removed.stderr
    assert not installer.inspect(profile).dependency and not installer.inspect(profile).registered
    assert json.loads(settings.read_text())["dsh_bridge"]["enabled"] is False
    assert (data / "uninstall-cleanup.log").is_file()
