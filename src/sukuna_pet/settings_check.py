"""Opt-in native settings-menu regression check with isolated preferences."""

import json
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from .desktop import PetWindow
from .settings_window import SettingsWindow


def main(arguments: list[str]) -> int:
    root = Path(arguments[0]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    app.setQuitOnLastWindowClosed(False)
    pet = PetWindow(settings_path=root / "mode.json", chat_data_dir=root / "sessions")
    pet.show()
    result: dict[str, object] = {"frozen": bool(getattr(sys, "frozen", False))}
    inside: list[bool] = []
    errors: list[str] = []

    def finish() -> None:
        settings = pet.findChild(SettingsWindow)
        result.update(visible=bool(settings and settings.isVisible()),
                      active=bool(settings and settings.isActiveWindow()),
                      regular_window=bool(settings and settings.windowType() == Qt.WindowType.Window),
                      created_inside_popup=any(inside), errors=errors)
        result["passed"] = bool(result["visible"] and result["active"]
                                and result["regular_window"]
                                and not result["created_inside_popup"] and not errors)
        if settings is not None and settings.isVisible():
            settings.grab().save(str(root / "settings.png"))
            settings.close()
        pet.close()
        (root / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        app.exit(0 if result["passed"] else 1)

    def click() -> None:
        menu = app.activePopupWidget()
        if not isinstance(menu, QMenu):
            errors.append("popup missing")
            return
        action = next(a for a in menu.actions() if a.text() == "桌宠设置")
        QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
        inside.append(pet.findChild(SettingsWindow) is not None)

    def start() -> None:
        QTimer.singleShot(100, click)
        def dismiss() -> None:
            popup = app.activePopupWidget()
            if popup is not None:
                popup.close()
        QTimer.singleShot(2500, dismiss)
        point = pet.visible_region.boundingRect().center()
        QApplication.sendEvent(pet, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, point, pet.mapToGlobal(point)))
        QTimer.singleShot(500, finish)

    QTimer.singleShot(100, start)
    return app.exec()
