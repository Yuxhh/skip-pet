"""Observe the production V5 window on Windows, with isolated preferences.

--capture records current native alpha routing and light/dark/textured desktop
screenshots. Without it, use real OS input and exit from the pet's context menu.
The receiver's L/D/T keys change background; no regular preferences are read.
"""

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.settings import save_size


class Receiver(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("V5 #23 native background receiver (L/D/T)")
        self.background = "light"
        self.clicks = 0
        self.setGeometry(400, 170, 900, 650)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#263347" if self.background == "dark" else "#f3f2ee"))
        if self.background == "texture":
            for x in range(0, self.width(), 18):
                for y in range(0, self.height(), 18):
                    painter.fillRect(x, y, 18, 18, QColor("#c7c7c7" if (x // 18 + y // 18) % 2 else "#eeeeee"))
        painter.setPen(QColor("#dde4ee" if self.background == "dark" else "#25332e"))
        painter.drawText(20, 30, f"Production V5 / {self.background} / receiver clicks: {self.clicks}")

    def mouseReleaseEvent(self, event) -> None:
        self.clicks += 1
        self.update()

    def keyPressEvent(self, event) -> None:
        self.background = {Qt.Key.Key_L: "light", Qt.Key.Key_D: "dark", Qt.Key.Key_T: "texture"}.get(event.key(), self.background)
        self.update()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--compare-frozen", action="store_true", help="Compare captures with immutable native prototype images; needs the historical Git object")
    parser.add_argument("--output", type=Path, default=Path("docs/verification/issue-23"))
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    assert app.platformName() == "windows", "Requires the real Windows platform"
    receiver = Receiver()
    receiver.show()
    user32 = ctypes.windll.user32
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    record = {
        "platform": app.platformName(),
        "screens": [{"name": s.name(), "geometry": s.geometry().getRect(),
                     "work_area": s.availableGeometry().getRect(), "dpr": s.devicePixelRatio()}
                    for s in app.screens()],
        "input_kind": "Qt events and application virtual time in --capture; real OS input in interactive mode",
        "limitations": ["No real multi-monitor or mixed-DPI hardware validation.",
                        "No click bounce or V5 automatic scheduling in issue #23.",
                        "Desktop screenshots and OS routing are current production results, not historical prototype evidence."],
        "sizes": [],
    }

    def hit(window: PetWindow, point: QPoint) -> int:
        global_point = window.mapToGlobal(point)
        return int(user32.WindowFromPoint(wintypes.POINT(global_point.x(), global_point.y())) or 0)

    if args.capture:
        # Freeze only the wall-clock adapter. Virtual time and real public
        # window inputs still enter through the existing agreed seams.
        import sukuna_pet.desktop as desktop
        desktop.perf_counter = lambda: 0.0
        for height in (188, 271, 320):
            path = output / f"capture-{height}-preferences.json"
            save_size(path, height)
            pet = PetApplication()
            window = PetWindow(pet, settings_path=path)
            window.move(650, 300)
            window.show()
            QTest.qWait(60)
            entry = {"height": height, "canvas": [window.width(), window.height()], "stages": []}
            previous = window.visible_region
            for stage in range(4):
                assert pet.view.stage == stage and pet.view.holding
                frame, mask = window.frame, window.visible_region
                bounds = mask.boundingRect()
                assert window.rect().contains(bounds)
                assert bounds.left() > 0 and bounds.top() > 0
                assert bounds.right() < window.width() - 1 and bounds.bottom() < window.height() - 1
                point = bounds.center()
                assert mask.contains(point)
                assert hit(window, point) == int(window.winId())
                assert hit(window, QPoint(2, 2)) == int(receiver.winId())
                changed = previous ^ mask
                checked = 0
                for y in range(window.height()):
                    for x in range(window.width()):
                        candidate = QPoint(x, y)
                        if changed.contains(candidate):
                            expected = int(window.winId()) if mask.contains(candidate) else int(receiver.winId())
                            assert hit(window, candidate) == expected, (height, stage, x, y)
                            checked += 1
                            if checked >= 20:
                                break
                    if checked >= 20:
                        break
                frame.save(str(output / f"{height}-stage-{stage}.png"))
                entry["stages"].append({"stage": stage, "view": asdict(pet.view),
                                        "bounds": bounds.getRect(), "visible_hit": "pet",
                                        "transparent_hit": "receiver", "changed_pixels_checked": checked})
                if height == 320:
                    for background in ("light", "dark", "texture"):
                        receiver.background = background
                        receiver.update()
                        QTest.qWait(40)
                        screen = receiver.screen()
                        screenshot = screen.grabWindow(0, receiver.x(), receiver.y(), receiver.width(), receiver.height())
                        screenshot.save(str(output / f"desktop-{background}-stage-{stage}.png"))
                previous = mask
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point)
                pet.advance(1000)
                QTest.qWait(16)
            if height == 320:
                sampled_bounds = [window.visible_region.boundingRect()]
                for stage, duration in ((1, 13 / .072), (2, 11 / .072), (3, 240), (0, 7 / .072)):
                    QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.visible_region.boundingRect().center())
                    for sample in range(41):
                        pet.advance(duration / 41)
                        QTest.qWait(10)
                        bounds = window.visible_region.boundingRect()
                        assert bounds.left() > 0 and bounds.top() > 0
                        assert bounds.right() < window.width() - 1 and bounds.bottom() < window.height() - 1
                        sampled_bounds.append(bounds)
                        if sample == 20:
                            window.frame.save(str(output / f"transition-to-{stage}.png"))
                    pet.advance(1)  # Absorb floating-point endpoint roundoff.
                    QTest.qWait(10)
                entry["sampling"] = {"frames": len(sampled_bounds), "all_inside_canvas": True,
                                     "input": "Four real Qt clicks; 41 equal virtual time samples per stage, no bounce.",
                                     "union_bounds": [min(b.left() for b in sampled_bounds), min(b.top() for b in sampled_bounds),
                                                      max(b.right() for b in sampled_bounds), max(b.bottom() for b in sampled_bounds)],
                                     "note": "165 reachable head phases; raster samples, not a continuous-space proof."}
            # Animated drag via Qt events, recorded distinctly from OS input.
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.visible_region.boundingRect().center())
            pet.advance(60)
            QTest.qWait(16)
            stage = pet.view.stage
            position = window.pos()
            point = window.visible_region.boundingRect().center()
            QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=point)
            QTest.mouseMove(window, point + QPoint(65, 40))
            pet.advance(60)
            QTest.qWait(16)
            QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=point)
            assert pet.view.stage == stage
            assert window.pos() != position
            entry["animated_qt_drag"] = {"moved": True, "stage_unchanged": True}
            entry["native_topmost"] = bool(user32.GetWindowLongPtrW(int(window.winId()), -20) & 8)
            assert entry["native_topmost"]
            record["sizes"].append(entry)
            window.close()
            window.deleteLater()
            app.processEvents()
        (output / "native-capture.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.compare_frozen:
            commit = "4ecb85c8a087ca89fb99a3a2125c826801b53e1c"
            comparisons = []
            for height in (188, 271, 320):
                for stage in range(4):
                    path = f".scratch/sukuna-pet/prototypes/native-v5/evidence/{height}-stage{stage}-rest.png"
                    data = subprocess.check_output(["git", "show", f"{commit}:{path}"])
                    reference = QImage.fromData(data).convertToFormat(QImage.Format.Format_RGBA8888)
                    current = QImage(str(output / f"{height}-stage-{stage}.png")).convertToFormat(QImage.Format.Format_RGBA8888)
                    assert reference.size() == current.size()
                    differences = [abs(a - b) for a, b in zip(bytes(reference.constBits()), bytes(current.constBits()))]
                    comparisons.append({"size": height, "stage": stage, "channels_differ": sum(d > 0 for d in differences),
                                        "channels_over_4": sum(d > 4 for d in differences), "max_channel_difference": max(differences),
                                        "mean_channel_difference": sum(differences) / len(differences)})
                    assert max(differences) <= 1
            (output / "frozen-native-comparison.json").write_text(json.dumps({
                "reference_commit": commit,
                "note": "Current production final frames versus frozen native rest images, same Qt and DPR 1.0; no bounce.",
                "results": comparisons,
            }, indent=2), encoding="utf-8")
        receiver.close()
        print("PASS: production Windows frames, native routing, three sizes and animated Qt drag")
        return 0

    pet = PetApplication()
    window = PetWindow(pet)
    window.move(650, 300)
    window.show()
    (output / "interactive-environment.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    trace = (output / "os-input-trace.jsonl").open("w", encoding="utf-8")
    previous = ""

    def observe() -> None:
        nonlocal previous
        popup = QApplication.activePopupWidget()
        record = {"view": asdict(pet.view), "position": [window.x(), window.y()],
                  "bounds": window.visible_region.boundingRect().getRect(), "receiver_clicks": receiver.clicks,
                  "cursor": [QCursor.pos().x(), QCursor.pos().y()], "menu_visible": isinstance(popup, QMenu),
                  "visible": window.isVisible(), "background": receiver.background,
                  "native_topmost": bool(user32.GetWindowLongPtrW(int(window.winId()), -20) & 8)}
        encoded = json.dumps(record, ensure_ascii=False)
        if encoded != previous:
            trace.write(encoded + "\n")
            trace.flush()
            previous = encoded
            if pet.view.holding:
                window.frame.save(str(output / f"os-holding-stage-{pet.view.stage}.png"))
            if isinstance(popup, QMenu):
                popup.grab().save(str(output / "os-context-menu.png"))
        if not window.isVisible():
            app.quit()

    timer = QTimer()
    timer.timeout.connect(observe)
    timer.start(30)
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
