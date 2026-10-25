"""Record real Windows edge contact and OS input on the production window.

Run with computer-use or manual mouse input; exit through the pet menu.
--capture compares settled desktop pixels at exact application times.
Only the output directory's isolated preferences are read or written.
"""

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import sys
from time import perf_counter

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QCursor, QImage, QMouseEvent, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.settings import save_size
from verify_v5_native import Receiver


def capture(app: QApplication, receiver: Receiver, output: Path) -> int:
    """Exact application time, public Qt input, then settled native pixels."""
    import sukuna_pet.desktop as desktop
    desktop.perf_counter = lambda: 0.0
    records = []
    for height in (188, 271, 320):
        path = output / f"capture-{height}-preferences.json"
        save_size(path, height)
        pet = PetApplication()
        window = PetWindow(pet, settings_path=path)
        window.show()
        window.raise_()
        QTest.qWait(80)
        area = window.screen().availableGeometry()

        def pointer(kind: QEvent.Type, point: QPoint) -> None:
            button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
            buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
            QApplication.sendEvent(window, QMouseEvent(
                kind, QPointF(point - window.pos()), QPointF(point), button, buttons,
                Qt.KeyboardModifier.NoModifier))

        def drag(end: QPoint) -> None:
            start = window.mapToGlobal(window.mask().boundingRect().center())
            before = pet.view
            pointer(QEvent.Type.MouseButtonPress, start)
            pointer(QEvent.Type.MouseMove, end)
            pointer(QEvent.Type.MouseButtonRelease, end)
            assert pet.view == before

        for horizontal, vertical in ((None, "top"), (None, "bottom"), ("left", None), ("right", None),
                                     ("left", "top"), ("left", "bottom"),
                                     ("right", "top"), ("right", "bottom")):
            drag(area.center())
            end = window.mapToGlobal(window.mask().boundingRect().center())
            if horizontal:
                end.setX(area.left() - window.width() if horizontal == "left" else area.right() + window.width())
            if vertical:
                end.setY(area.top() - window.height() if vertical == "top" else area.bottom() + window.height())
            drag(end)
            for stage in (1, 2, 3, 0):
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.mask().boundingRect().center())
                for label, elapsed in (("peak", 110), ("held", 890)):
                    pet.advance(elapsed)
                    # A timer observer can run before Qt paints/uploads a new
                    # layered frame. Wait with virtual time fixed before taking
                    # pixel evidence; otherwise grabs may contain old buffers.
                    QTest.qWait(60)
                    bounds = window.mask().boundingRect().translated(window.pos())
                    assert area.contains(bounds)
                    for edge in (horizontal, vertical):
                        if edge:
                            assert getattr(bounds, edge)() == getattr(area, edge)()
                    crop = window.geometry().intersected(area)
                    expected = receiver.grab().toImage().copy(crop.translated(-receiver.pos()))
                    painter = QPainter(expected)
                    painter.drawImage(window.pos() - crop.topLeft(), window.frame)
                    painter.end()
                    actual = window.screen().grabWindow(0, *crop.getRect()).toImage()
                    actual = actual.convertToFormat(QImage.Format.Format_RGBA8888)
                    expected = expected.convertToFormat(QImage.Format.Format_RGBA8888)
                    av, ev = bytes(actual.constBits()), bytes(expected.constBits())
                    assert actual.size() == expected.size()
                    mismatches = sum(max(abs(av[j+c]-ev[j+c]) for c in range(3)) > 3
                                     for j in range(0, len(av), 4))
                    name = f"{height}-{'-'.join(e for e in (horizontal, vertical) if e)}-stage{stage}-{label}"
                    if mismatches:
                        actual.save(str(output / f"failure-{name}-actual.png"))
                        expected.save(str(output / f"failure-{name}-expected.png"))
                    assert mismatches == 0, (name, mismatches)
                    if stage == 1 and label == "peak":
                        actual.save(str(output / f"settled-{name}.png"))
                    records.append({"name": name, "position": [window.x(), window.y()],
                                    "bounds": bounds.getRect(), "work_area": area.getRect(),
                                    "view": asdict(pet.view), "pixel_mismatches_over_3": mismatches})
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    (output / "native-capture.json").write_text(json.dumps({
        "input": "Qt public mouse events and exact application virtual time; not OS injection",
        "pixels": "Windows desktop composition vs final frame over receiver; 60ms fixed-time upload wait",
        "samples": records,
    }, indent=2), encoding="utf-8")
    receiver.close()
    print(f"PASS: {len(records)} Windows samples match final-frame pixels and edge geometry")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/verification/issue-26"))
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    assert app.platformName() == "windows"
    receiver = Receiver()
    receiver.setWindowTitle("V5 #26 edge verification background")
    flags = Qt.WindowType.FramelessWindowHint
    if args.capture:
        flags |= Qt.WindowType.WindowStaysOnTopHint
    receiver.setWindowFlags(flags)
    screen = app.primaryScreen()
    assert screen is not None
    receiver.setGeometry(screen.availableGeometry())
    receiver.show()
    if args.capture:
        return capture(app, receiver, output)
    path = output / "os-preferences.json"
    path.write_text('{"mode":"click","size":320}\n')
    pet = PetApplication(settings_path=path)
    window = PetWindow(pet, settings_path=path)
    window.move(650, 300)
    window.show()
    user32 = ctypes.windll.user32
    user32.GetCapture.restype = wintypes.HWND
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    (output / "environment.json").write_text(json.dumps({
        "platform": app.platformName(), "input": "Real OS mouse via computer-use or manual input",
        "screens": [{"name": s.name(), "geometry": s.geometry().getRect(),
                     "work_area": s.availableGeometry().getRect(), "dpr": s.devicePixelRatio()}
                    for s in app.screens()],
        "limitations": ["Single-screen Windows evidence; no physical mixed-DPI/multi-screen acceptance"],
    }, indent=2), encoding="utf-8")
    trace = gzip.open(output / "os-input-trace.jsonl.gz", "wt", encoding="utf-8")
    started = perf_counter()
    captures: set[tuple] = set()
    samples = 0

    def observe() -> None:
        nonlocal samples
        area = window.screen().availableGeometry()
        bounds = window.mask().boundingRect().translated(window.pos())
        contact = [edge for edge in ("left", "right", "top", "bottom")
                   if getattr(bounds, edge)() == getattr(area, edge)()]
        cursor = QCursor.pos()
        popup = QApplication.activePopupWidget()
        entry = {
            "elapsed_ms": (perf_counter() - started) * 1000,
            "mode": pet.mode, "view": asdict(pet.view),
            "position": [window.x(), window.y()], "height": window.height(),
            "visible_bounds": bounds.getRect(), "work_area": area.getRect(),
            "contact": contact, "fully_visible": area.contains(bounds),
            "cursor": [cursor.x(), cursor.y()],
            "left_pressed": bool(QApplication.mouseButtons() & Qt.MouseButton.LeftButton),
            "native_capture_is_pet": int(user32.GetCapture() or 0) == int(window.winId()),
            "cursor_target": int(user32.WindowFromPoint(wintypes.POINT(cursor.x(), cursor.y())) or 0),
            "pet_handle": int(window.winId()), "receiver_handle": int(receiver.winId()),
            "receiver_clicks": receiver.clicks, "menu_visible": isinstance(popup, QMenu),
        }
        trace.write(json.dumps(entry) + "\n")
        trace.flush()
        samples += 1
        # Real desktop images of distinct contacts/size/stage and bounce peaks.
        peak = pet.view.bounce_scale[0] > 1.095
        key = (window.height(), tuple(contact), pet.view.stage, peak)
        if window.isVisible() and contact and key not in captures:
            captures.add(key)
            label = f"{window.height()}-{'-'.join(contact)}-stage{pet.view.stage}-{'peak' if peak else 'other'}"
            window.screen().grabWindow(0).save(str(output / f"desktop-{label}.png"))
        if not window.isVisible():
            app.quit()

    timer = QTimer()
    timer.timeout.connect(observe)
    timer.start(8)
    QTimer.singleShot(900_000, app.quit)
    result = app.exec()
    trace.close()
    (output / "os-result.json").write_text(json.dumps({
        "exit_code": result, "closed": not window.isVisible(),
        "receiver_clicks": receiver.clicks, "samples": samples,
        "saved": json.loads(path.read_text()), "captures": len(captures),
    }, indent=2), encoding="utf-8")
    receiver.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
