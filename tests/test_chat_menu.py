"""Open chat through a real popup, including its nested native event loop."""

import pytest
from PySide6.QtCore import QEvent, Qt, QTimer, QThread
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from sukuna_pet.chat_window import ChatWindow
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from test_chat_controller import configured
import sukuna_pet.desktop as desktop


@pytest.mark.parametrize("entry", ["pet", "tray"])
def test_real_popup_opens_and_restores_chat(entry: str, monkeypatch: pytest.MonkeyPatch) -> None:
    app = QApplication.instance() or QApplication([])
    opened_at_loop_level: list[int] = []

    class Chat(ChatWindow):
        def open_window(self) -> None:
            opened_at_loop_level.append(QThread.currentThread().loopLevel())
            super().open_window()

    monkeypatch.setattr(desktop, "ChatWindow", Chat)
    pet = PetWindow(PetApplication(), credentials=configured())
    pet.show()
    QTest.qWait(50)
    clicked: list[bool] = []
    select_timer = QTimer(pet)
    select_timer.setSingleShot(True)
    watchdog = QTimer(pet)
    watchdog.setSingleShot(True)
    watchdog.timeout.connect(lambda: app.activePopupWidget().close()
                             if app.activePopupWidget() is not None else None)

    def select_chat() -> None:
        menu = app.activePopupWidget()
        if not isinstance(menu, QMenu):
            select_timer.start(10)
            return
        action = next(a for a in menu.actions() if a.text() == "AI 对话")
        clicked.append(True)
        QTest.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())

    select_timer.timeout.connect(select_chat)

    def open_menu() -> None:
        before = len(clicked)
        select_timer.start(100)
        # Bound a failed selection so the regression cannot hang in exec().
        watchdog.start(1500)
        point = pet.visible_region.boundingRect().center()
        if entry == "pet":
            QApplication.sendEvent(pet, QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, point, pet.mapToGlobal(point)))
        else:
            tray = pet.findChild(QSystemTrayIcon)
            assert tray is not None
            tray.contextMenu().exec(pet.mapToGlobal(point))
        select_timer.stop()
        watchdog.stop()
        QTest.qWait(150)
        assert len(clicked) == before + 1

    try:
        open_menu()
        chat = pet.findChild(ChatWindow)
        assert clicked and chat is not None and chat.isVisible()
        assert opened_at_loop_level == [0], "Chat must open after the native menu loop returns"
        assert app.activeWindow() is chat
        chat.showMinimized()
        open_menu()
        assert chat.isVisible() and not chat.isMinimized()
        assert app.activeWindow() is chat
        chat.close()
        open_menu()
        assert chat.isVisible() and app.activeWindow() is chat
        assert pet.findChildren(ChatWindow) == [chat]
        assert opened_at_loop_level == [0, 0, 0]
    finally:
        pet.close()
        pet.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
