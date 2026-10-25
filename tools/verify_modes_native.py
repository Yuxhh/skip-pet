"""Opt-in Windows/Qt menu and process-restart smoke check for #14.

Run with the desktop visible: python tools/verify_modes_native.py
Uses real widgets and Qt input events, not Computer Use or OS mouse injection.
QStandardPaths test mode isolates preferences from the user's regular launch.
"""

import json
from pathlib import Path
import subprocess
import sys

from PySide6.QtCore import QPoint, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from sukuna_pet.desktop import PetWindow


OUTPUT = Path("docs/verification/issue-14")


def create_test_application() -> QApplication:
    app = QApplication(sys.argv)
    app.setOrganizationName("skip-pet")
    app.setApplicationName("sukuna-pet")
    app.setApplicationDisplayName("宿傩桌宠")
    QStandardPaths.setTestModeEnabled(True)
    assert app.platformName() == "windows", "This check requires a visible Windows desktop"
    return app


def test_settings_path() -> Path:
    return Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppConfigLocation,
    )) / "mode.json"


def session(name: str) -> int:
    app = create_test_application()
    settings = test_settings_path()
    if name == "select-always" and settings.exists():
        raise RuntimeError(f"Test settings already exist: {settings}. Use a clean test profile.")
    window = PetWindow()
    window.show()
    failures: list[str] = []
    expected = "点击跳动" if name in ("select-always", "restore-click") else "持续跳动"
    chosen = "持续跳动" if name == "select-always" else "点击跳动"

    def open_menu(choose: str, suffix: str) -> None:
        def inspect_and_click() -> None:
            try:
                menu = QApplication.activePopupWidget()
                assert isinstance(menu, QMenu)
                actions = [action for action in menu.actions() if not action.isSeparator()]
                assert [action.text() for action in actions] == ["点击跳动", "持续跳动", "调整大小", "退出"]
                checked = expected if suffix == "mode" else chosen
                assert [action.text() for action in actions if action.isChecked()] == [checked]
                assert menu.grab().save(str(OUTPUT / f"{name}-{suffix}-menu.png"))
                action = next(action for action in actions if action.text() == choose)
                QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
            except Exception as error:
                failures.append(repr(error))
                app.exit(1)

        QTimer.singleShot(100, inspect_and_click)
        point = QPoint(window.width() // 2, window.height() // 2)
        event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, point, window.mapToGlobal(point))
        QApplication.sendEvent(window, event)

    def run() -> None:
        try:
            assert window.grab().save(str(OUTPUT / f"{name}-startup.png"))
            open_menu(chosen, "mode")
            if failures:
                return
            assert json.loads(settings.read_text(encoding="utf-8")) == {
                "mode": "always" if chosen == "持续跳动" else "click",
            }
            # Ordinary clicks still reach the real window in either selected mode.
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(120, 140))
            QTimer.singleShot(1200, finish)
        except Exception as error:
            failures.append(repr(error))
            app.exit(1)

    def finish() -> None:
        try:
            assert window.grab().save(str(OUTPUT / f"{name}-after-click.png"))
            open_menu("退出", "exit")
        except Exception as error:
            failures.append(repr(error))
            app.exit(1)

    QTimer.singleShot(300, run)
    QTimer.singleShot(10_000, lambda: app.exit(2))
    result = app.exec()
    print(json.dumps({"session": name, "exit_code": result, "failures": failures,
                      "settings": str(settings)}, ensure_ascii=True))
    return 1 if failures else result


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1:
        raise SystemExit(session(sys.argv[1]))
    app = create_test_application()
    settings = test_settings_path()
    previous = settings.read_bytes() if settings.exists() else None
    try:
        settings.unlink(missing_ok=True)
        for name in ("select-always", "restore-always", "restore-click"):
            subprocess.run([sys.executable, __file__, name], check=True, timeout=20)
    finally:
        if previous is None:
            settings.unlink(missing_ok=True)
        else:
            settings.write_bytes(previous)
    print("PASS: three real Windows/Qt menu sessions exited and restored both modes")
