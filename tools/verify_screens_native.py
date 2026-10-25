"""Inventory real displays; optionally record manual Windows multi-screen QA.

No scenario is automatically accepted. Use a fresh --output directory per run.
Without --seconds this only records the environment and opens no pet window.
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

import PySide6
from PySide6.QtCore import QTimer, qVersion
from PySide6.QtGui import QCursor, QScreen
from PySide6.QtWidgets import QApplication

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication


def screen_info(screen: QScreen) -> dict:
    return {"name": screen.name(), "geometry": screen.geometry().getRect(),
            "work_area": screen.availableGeometry().getRect(),
            "dpr": screen.devicePixelRatio(), "logical_dpi": screen.logicalDotsPerInch()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=0,
                        help="Open the production pet for manual input; auto-close after this time")
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    if (output / "environment.json").exists():
        parser.error("Use a fresh output directory to preserve earlier evidence")
    app = QApplication(sys.argv)
    if app.platformName() != "windows":
        parser.error("Native inventory/observation requires the Windows Qt platform")
    (output / "environment.json").write_text(json.dumps({
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(), "python": sys.version, "pyside": PySide6.__version__,
        "qt": qVersion(), "qpa": app.platformName(),
        "screens": [screen_info(s) for s in QApplication.screens()],
        "evidence": "Real screen inventory only; no hardware scenario accepted by this tool",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.seconds <= 0:
        return 0
    path = output / "preferences.json"
    path.write_text('{"mode":"click","size":320}\n', encoding="utf-8")
    pet = PetApplication(settings_path=path)
    window = PetWindow(pet, settings_path=path)
    window.show()
    started = perf_counter()
    samples = 0
    with gzip.open(output / "trace.jsonl.gz", "wt", encoding="utf-8") as trace:
        def record(kind: str, **fields: object) -> None:
            trace.write(json.dumps({"ms": (perf_counter() - started) * 1000,
                                    "kind": kind, **fields}) + "\n")
            trace.flush()

        def watch(screen: QScreen) -> None:
            record("connected", screen=screen_info(screen))
            screen.availableGeometryChanged.connect(lambda: record("work_area", screen=screen_info(screen)))
            screen.geometryChanged.connect(lambda: record("geometry", screen=screen_info(screen)))
            screen.logicalDotsPerInchChanged.connect(lambda: record("dpi", screen=screen_info(screen)))

        def observe() -> None:
            nonlocal samples
            screen = window.screen()
            area = screen.availableGeometry()
            bounds = window.visible_region.boundingRect().translated(window.pos())
            cursor = QCursor.pos()
            record("sample", screen=screen_info(screen), position=[window.x(), window.y()],
                   height=window.height(), frame_dpr=window.frame.devicePixelRatio(),
                   visible_bounds=bounds.getRect(), fully_visible=area.contains(bounds),
                   cursor=[cursor.x(), cursor.y()], mode=pet.mode, view=asdict(pet.view))
            samples += 1

        for screen in QApplication.screens():
            watch(screen)
        app.screenAdded.connect(watch)
        app.screenRemoved.connect(lambda: record("removed", remaining=[
            screen_info(s) for s in QApplication.screens()]))
        timer = QTimer()
        timer.timeout.connect(observe)
        timer.start(40)
        QTimer.singleShot(args.seconds * 1000, window.close)
        result = app.exec()
    (output / "result.json").write_text(json.dumps({
        "exit_code": result, "samples": samples, "closed": not window.isVisible(),
        "acceptance": "Manual review required; samples are observations, not hardware scenario passes",
    }, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
