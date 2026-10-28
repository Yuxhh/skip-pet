"""Windows/Qt resize menu smoke check using isolated workspace preferences.

Uses Qt input events on real widgets, not OS mouse injection. Each selection
runs in a fresh process to verify restored sizes. No user preferences change.
"""

import json
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from sukuna_pet.desktop import PetWindow
from sukuna_pet.settings import save_mode, save_size


OUTPUT = Path(__file__).resolve().parents[1] / "docs/verification/issue-18/corrected-sizes"
SETTINGS = OUTPUT / "test-preferences.json"


def session(height: int, expected: int) -> int:
    app = QApplication([])
    assert app.platformName() == "windows"
    window = PetWindow(settings_path=SETTINGS)
    window.show()
    failures: list[str] = []

    def open_menu(select: bool) -> None:
        def inspect_parent() -> None:
            try:
                menu = QApplication.activePopupWidget()
                assert isinstance(menu, QMenu)
                action = next(action for action in menu.actions() if action.text() == "调整大小")
                menu.setActiveAction(action)
                QTest.keyClick(menu, Qt.Key.Key_Right)
                QTimer.singleShot(100, lambda: inspect_sizes(menu))
            except Exception as error:
                failures.append(repr(error))
                app.exit(1)

        def inspect_sizes(parent: QMenu) -> None:
            try:
                menu = QApplication.activePopupWidget()
                assert isinstance(menu, QMenu) and menu is not parent
                actions = menu.actions()
                assert [action.text() for action in actions] == ["188px", "271px", "320px"]
                checked = expected if select else height
                assert [action.text() for action in actions if action.isChecked()] == [f"{checked}px"]
                if select:
                    action = next(action for action in actions if action.text() == f"{height}px")
                    QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
                else:
                    assert parent.grab().save(str(OUTPUT / f"{height}-menu.png"))
                    assert menu.grab().save(str(OUTPUT / f"{height}-sizes.png"))
                    menu.close()
                    parent.close()
            except Exception as error:
                failures.append(repr(error))
                app.exit(1)

        QTimer.singleShot(100, inspect_parent)
        point = QPoint(window.width() // 2, window.height() // 2)
        QApplication.sendEvent(window, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, point, window.mapToGlobal(point),
        ))

    def run() -> None:
        try:
            assert window.height() == expected
            open_menu(True)
            assert not failures, failures
            assert window.height() == height
            assert window.height() <= 320
            assert window.screen().availableGeometry().contains(
                window.visible_region.boundingRect().translated(window.pos()))
            assert window.grab().save(str(OUTPUT / f"{height}-character.png"))
            open_menu(False)
            assert not failures, failures
            window.close()
        except Exception as error:
            failures.append(repr(error))
            app.exit(1)

    QTimer.singleShot(300, run)
    QTimer.singleShot(8000, lambda: app.exit(2))
    result = app.exec()
    record = {"height": height, "restored_height": expected, "width": window.width(),
              "platform": app.platformName(), "exit_code": result, "failures": failures}
    (OUTPUT / f"{height}-result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record))
    return 1 if failures else result


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) == 3:
        raise SystemExit(session(int(sys.argv[1]), int(sys.argv[2])))
    save_mode(SETTINGS, "click")
    save_size(SETTINGS, 320)
    for height, expected in ((188, 320), (271, 188), (320, 271)):
        subprocess.run([sys.executable, __file__, str(height), str(expected)], check=True, timeout=15)
    print("PASS: all three native sizes, menu checks and process restarts")
