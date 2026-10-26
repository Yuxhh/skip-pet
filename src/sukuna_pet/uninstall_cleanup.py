"""Installer cleanup entry, without constructing QApplication or a pet window."""

import argparse
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from .bridge_install import BridgeInstaller, desktop_profile
from .settings import load_bridge, save_bridge


def main(argv: list[str] | None = None) -> int:
    root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, default=root / "skip-pet/sukuna-pet/mode.json")
    parser.add_argument("--maintenance-dir", type=Path, default=root / "sukuna-pet")
    args = parser.parse_args(argv)
    try:
        saved = load_bridge(args.settings)
        profiles = saved.profiles or (desktop_profile(),)
        if saved.enabled:
            save_bridge(args.settings, False, profiles)
        report = BridgeInstaller(data_dir=args.maintenance_dir).remove(profiles, preserve_shared=True)
        code, detail = (0 if report.ok else 1), report.message
    except Exception as error:
        code, detail = 1, f"清理失败：{error}"
    try:
        args.maintenance_dir.mkdir(parents=True, exist_ok=True)
        with (args.maintenance_dir / "uninstall-cleanup.log").open("a", encoding="utf-8") as stream:
            stream.write(f"[{datetime.now().isoformat(timespec='seconds')}] exit={code}\n{detail}\n")
    except OSError:
        return 1
    return code
