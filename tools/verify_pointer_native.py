"""Interactive Windows check: use OS mouse input against this pet and Notepad.

Run python tools/verify_pointer_native.py. The production window receives real
input; this observer only records its public application view and Qt geometry.
No synthetic Qt events or OS input injection are used here. Preferences are not
read or written. Exit using the pet's real context menu.
"""

import ctypes
from dataclasses import asdict
import json
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMenu

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication


def main() -> int:
    app = QApplication(sys.argv)
    assert app.platformName() == "windows", "Requires the real Windows desktop"
    output = Path("docs/verification/issue-15")
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

    with (output / "native-trace.jsonl").open("w", encoding="utf-8") as trace:
        def observe() -> None:
            nonlocal previous, sample, menu_saved
            popup = QApplication.activePopupWidget()
            if isinstance(popup, QMenu) and not menu_saved:
                popup.grab().save(str(output / "native-menu.png"))
                menu_saved = True
            record = {
                "position": [window.x(), window.y()],
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
