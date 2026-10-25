"""Measure the production Qt window through public inputs, without diagnostics in the app.

Profiling adds overhead. Results describe this source process and machine only;
installed-process CPU and OS interaction evidence must be collected separately.
"""

import argparse
import cProfile
from dataclasses import asdict
import json
from pathlib import Path
import platform
import sys
from time import perf_counter, process_time

from PySide6 import __version__ as qt_version
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    pet = PetApplication()
    window = PetWindow(pet)
    window.show()
    QTest.qWait(100)
    results = []
    for name, duration in (("idle", 1200), ("click", 1400),
                           ("rapid-click", 1800), ("continuous", 4500),
                           ("settled", 1200)):
        profile = cProfile.Profile()
        profile.enable()
        start, cpu_start = perf_counter(), process_time()
        samples: list[dict[str, object]] = []
        next_click = 0.0
        if name == "continuous":
            pet.select_mode("always")
        elif name == "settled":
            pet.select_mode("click")
            QTest.qWait(400)
            # Exclude the natural finish from the settled measurement.
            profile.disable()
            profile = cProfile.Profile()
            profile.enable()
            start, cpu_start = perf_counter(), process_time()
        while (elapsed := (perf_counter() - start) * 1000) < duration:
            if (name == "click" and not samples) or (name == "rapid-click" and elapsed >= next_click and elapsed < 600):
                QTest.mouseClick(window, Qt.MouseButton.LeftButton,
                                 pos=window.visible_region.boundingRect().center())
                next_click += 75
            samples.append({"elapsed_ms": elapsed, "view": asdict(pet.view)})
            QTest.qWait(8)
        cpu_ms = (process_time() - cpu_start) * 1000
        wall_ms = (perf_counter() - start) * 1000
        profile.disable()
        functions = []
        for entry in profile.getstats():
            code = entry.code
            if isinstance(code, str):
                continue
            if (Path(code.co_filename).name, code.co_name) not in (("rendering.py", "render"), ("desktop.py", "_character_region")):
                continue
            functions.append({"file": Path(code.co_filename).name, "function": code.co_name,
                              "calls": entry.callcount, "total_ms": entry.inlinetime * 1000,
                              "cumulative_ms": entry.totaltime * 1000,
                              "mean_cumulative_ms": entry.totaltime * 1000 / entry.callcount})
        results.append({"scenario": name, "wall_ms": wall_ms, "cpu_ms": cpu_ms,
                        "cpu_percent_of_one_core": cpu_ms / wall_ms * 100,
                        "profile": functions, "samples": samples})
    report = {"python": sys.version, "platform": platform.platform(), "qt": qt_version,
              "qt_platform": app.platformName(), "canvas": [window.width(), window.height()],
              "dpr": window.devicePixelRatioF(),
              "screens": [{"name": s.name(), "geometry": s.geometry().getRect(),
                           "available": s.availableGeometry().getRect(), "dpr": s.devicePixelRatio()}
                          for s in app.screens()],
              "scope": "Source Qt process with cProfile overhead; public Qt clicks and real event-loop time. Not an installed binary or cross-machine frame-rate guarantee.",
              "results": results}
    (args.output / "performance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
