"""Interactive Windows check: use OS mouse input against this pet and Notepad.

Run python tools/verify_pointer_native.py [--output docs/verification/issue-16].
The production window receives real
input; this observer only records its public application view and Qt geometry.
No synthetic Qt events or OS input injection are used here. Preferences are not
read or written. Exit using the pet's real context menu.
"""

import argparse
import ctypes
from dataclasses import asdict
import json
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QMenu

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/verification/issue-15"))
    args = parser.parse_args()
    app = QApplication(sys.argv)
    assert app.platformName() == "windows", "Requires the real Windows desktop"
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    pet = PetApplication()
    window = PetWindow(pet)
    window.move(550, 400)
    window.show()
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    previous = ""
    sample = 0
    menu_saved = False

    def screens() -> list[dict]:
        return [{"name": screen.name(), "geometry": screen.geometry().getRect(),
                 "available_geometry": screen.availableGeometry().getRect(),
                 "device_pixel_ratio": screen.devicePixelRatio()}
                for screen in app.screens()]

    (output / "screen-layout.json").write_text(json.dumps({
        "platform": app.platformName(), "screens": screens(),
    }, indent=2), encoding="utf-8")

    with (output / "native-trace.jsonl").open("w", encoding="utf-8") as trace:
        def observe() -> None:
            nonlocal previous, sample, menu_saved
            popup = QApplication.activePopupWidget()
            if isinstance(popup, QMenu) and not menu_saved:
                popup.grab().save(str(output / "native-menu.png"))
                menu_saved = True
            record = {
                "position": [window.x(), window.y()],
                "visible_bounds": window.visible_region.boundingRect().translated(window.pos()).getRect(),
                "screen": window.screen().name(),
                "available_geometry": window.screen().availableGeometry().getRect(),
                "fully_visible": window.screen().availableGeometry().contains(
                    window.visible_region.boundingRect().translated(window.pos())),
                "screens": screens(),
                "cursor": [QCursor.pos().x(), QCursor.pos().y()],
                "left_pressed": bool(QApplication.mouseButtons() & Qt.MouseButton.LeftButton),
                "view": asdict(pet.view),
                "mode": pet.mode,
                "foreground_is_pet": user32.GetForegroundWindow() == int(window.winId()),
                "native_topmost": bool(user32.GetWindowLongPtrW(int(window.winId()), -20) & 8),
                "device_pixel_ratio": window.devicePixelRatioF(),
                "drag_distance": QApplication.startDragDistance(),
                "menu_visible": isinstance(popup, QMenu),
            }
            encoded = json.dumps(record, ensure_ascii=True)
            if encoded != previous:
                trace.write(encoded + "\n")
                trace.flush()
                previous = encoded
                if pet.view.holding:
                    window.grab().save(str(output / f"holding-stage-{pet.view.stage}.png"))
            sample += 1

        timer = QTimer()
        timer.timeout.connect(observe)
        timer.start(50)
        result = app.exec()
    print(f"Recorded {sample} observations to {output}; exit={result}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
