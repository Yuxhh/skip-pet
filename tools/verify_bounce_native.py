"""Production #24 Windows evidence; no normal user preferences are read.

--capture uses Qt public events and exact application time. Interactive mode
records real OS input separately. Range diagnostics sample independent extrema;
they are not reachable trajectories or a proof of continuous-space containment.
"""

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
from time import perf_counter

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QCursor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.rendering import CharacterRenderer
from sukuna_pet.settings import save_size
from verify_v5_native import Receiver


def alpha_bounds(frame: QImage) -> tuple[int, int, int, int]:
    rgba = frame.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = bytes(rgba.constBits())
    runs = []
    for y in range(rgba.height()):
        row = pixels[y * rgba.bytesPerLine() + 3:y * rgba.bytesPerLine() + rgba.width() * 4:4]
        xs = [x for x, alpha in enumerate(row) if alpha]
        if xs:
            runs.append((xs[0], y, xs[-1], y))
    return (min(r[0] for r in runs), min(r[1] for r in runs),
            max(r[2] for r in runs), max(r[3] for r in runs))


def range_diagnostics() -> list[dict]:
    renderer = CharacterRenderer()
    views = []
    for i in range(165):
        phase = i * 41 / 164
        pet = PetApplication()
        for start, end, duration in ((0, 13, 13 / .072), (13, 24, 11 / .072),
                                     (24, 34, 240), (34, 41, 7 / .072)):
            if phase <= start:
                break
            pet.click()
            pet.advance(duration * min(1, (phase - start) / (end - start)))
            if phase <= end:
                break
        views.append(pet.view)
    records = []
    for height in (188, 271, 320):
        bounds = []
        for view in views:
            for scale in ((1, 1), (1.1, .85)):
                # Diagnostic product space only. Public-event tests separately
                # cover genuinely reachable head/eye/blink/bounce combinations.
                frame = renderer.render(replace(view, bounce_scale=scale), height)
                b = alpha_bounds(frame)
                assert b[0] > 0 and b[1] > 0
                assert b[2] < frame.width() - 1 and b[3] < frame.height() - 1
                bounds.append(b)
        records.append({"height": height, "head_phases": 165, "bounce_extrema": 2,
                        "frames": len(bounds), "all_inside": True,
                        "union_bounds": [min(b[0] for b in bounds), min(b[1] for b in bounds),
                                         max(b[2] for b in bounds), max(b[3] for b in bounds)],
                        "boundary": "165 uniform source phases 0..41, step .25; two bounce extrema. "
                                    "Diagnostic raster sampling, not an analytic proof or input seam."})
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("docs/verification/issue-24"))
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    assert app.platformName() == "windows"
    receiver = Receiver()
    receiver.setWindowTitle("V5 #24 bounce background receiver (L/D/T)")
    receiver.show()
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetCapture.restype = wintypes.HWND
    record = {"platform": app.platformName(),
              "screens": [{"name": s.name(), "geometry": s.geometry().getRect(),
                           "work_area": s.availableGeometry().getRect(), "dpr": s.devicePixelRatio()}
                          for s in app.screens()],
              "input": "Qt public events and exact PetApplication virtual time" if args.capture else "Real OS input",
              "limits": ["Single screen DPR 1.0 only; no real multi-screen/mixed-DPI validation.",
                         "V5 automatic scheduler, dynamic edge pinning and installer are later tickets."],
              "sizes": []}

    def hit(window: PetWindow, point: QPoint) -> int:
        point = window.mapToGlobal(point)
        return int(user32.WindowFromPoint(wintypes.POINT(point.x(), point.y())) or 0)

    if args.capture:
        import sukuna_pet.desktop as desktop
        desktop.perf_counter = lambda: 0.0
        for height in (188, 271, 320):
            path = output / f"capture-{height}-preferences.json"
            save_size(path, height)
            pet = PetApplication()
            window = PetWindow(pet, settings_path=path)
            window.move(650, 300)
            window.show()
            QTest.qWait(40)
            origin = window.pos()
            entry = {"height": height, "canvas": [window.width(), window.height()], "samples": []}
            previous = window.visible_region

            def capture(name: str) -> None:
                nonlocal previous
                QTest.qWait(60)  # Allow the layered-window upload after the Qt timer/paint.
                mask = window.visible_region
                bounds = mask.boundingRect()
                assert window.rect().contains(bounds) and window.pos() == origin
                assert hit(window, bounds.center()) == int(window.winId())
                assert hit(window, QPoint(2, 2)) == int(receiver.winId())
                changed, checked = mask ^ previous, 0
                for y in range(window.height()):
                    for x in range(window.width()):
                        point = QPoint(x, y)
                        if changed.contains(point):
                            expected = window.winId() if mask.contains(point) else receiver.winId()
                            actual = hit(window, point)
                            assert actual == int(expected), (height, name, x, y, mask.contains(point), actual,
                                                              int(expected), int(window.winId()), int(receiver.winId()))
                            checked += 1
                            if checked >= 20:
                                break
                    if checked >= 20:
                        break
                window.frame.save(str(output / f"{height}-{name}.png"))
                entry["samples"].append({"name": name, "view": asdict(pet.view),
                                         "bounds": bounds.getRect(), "changed_native_hits": checked,
                                         "visible_target": "pet", "transparent_target": "receiver"})
                previous = mask

            capture("initial")
            for stage in (1, 2, 3, 0):
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.visible_region.boundingRect().center())
                pet.advance(110)
                assert pet.view.bounce_scale == (1.1, .85)
                capture(f"to-{stage}-peak")
                if height == 320:
                    for background in ("light", "dark", "texture"):
                        receiver.background = background
                        receiver.update()
                        QTest.qWait(30)
                        receiver.screen().grabWindow(0, receiver.x(), receiver.y(), receiver.width(), receiver.height()).save(
                            str(output / f"desktop-{background}-to-{stage}-peak.png"))
                pet.advance(110)
                assert pet.view.bounce_scale == (1, 1)
                capture(f"to-{stage}-220ms")
                pet.advance(1000)
                capture(f"stage-{stage}-held")
            for i in range(5):
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.visible_region.boundingRect().center())
                assert pet.view.bounce_scale == (1, 1)
                pet.advance(45 if i < 4 else 110)
            capture("rapid-five-peak")
            pet.advance(2000)
            assert pet.view.stage == 1 and pet.view.holding and pet.view.bounce_scale == (1, 1)
            capture("rapid-five-held")
            record["sizes"].append(entry)
            window.close()
            window.deleteLater()
            app.processEvents()
        record["range_diagnostics"] = range_diagnostics()
        (output / "native-capture.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        receiver.close()
        print("PASS: production combined Windows frames, current alpha routing, three sizes and 990 diagnostic frames")
        return 0

    pet = PetApplication()
    window = PetWindow(pet)
    window.move(650, 300)
    window.show()
    (output / "interactive-environment.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    trace = (output / "os-input-trace.jsonl").open("w", encoding="utf-8")
    previous = ""
    started = perf_counter()

    def observe() -> None:
        nonlocal previous
        popup = QApplication.activePopupWidget()
        entry = {"view": asdict(pet.view), "position": [window.x(), window.y()],
                 "bounds": window.visible_region.boundingRect().getRect(), "receiver_clicks": receiver.clicks,
                 "cursor": [QCursor.pos().x(), QCursor.pos().y()], "visible": window.isVisible(),
                 "menu_visible": isinstance(popup, QMenu),
                 "mouse_grabbed": QApplication.mouseButtons() != Qt.MouseButton.NoButton,
                 "native_capture_is_pet": int(user32.GetCapture() or 0) == int(window.winId()),
                 "native_topmost": bool(user32.GetWindowLongPtrW(int(window.winId()), -20) & 8)}
        encoded = json.dumps(entry, ensure_ascii=False)
        if encoded != previous:
            trace.write(json.dumps({"elapsed_ms": (perf_counter() - started) * 1000, **entry}, ensure_ascii=False) + "\n")
            trace.flush()
            previous = encoded
        if not window.isVisible():
            app.quit()

    timer = QTimer()
    timer.timeout.connect(observe)
    timer.start(8)
    QTimer.singleShot(600_000, app.quit)
    result = app.exec()
    trace.close()
    receiver.close()
    (output / "os-session-result.json").write_text(json.dumps({
        "exit_code": result, "pet_closed": not window.isVisible(),
        "receiver_clicks": receiver.clicks, "final_view": asdict(pet.view),
    }, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
