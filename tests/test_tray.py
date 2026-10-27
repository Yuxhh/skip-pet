"""Tray entry points and native taskbar/exit behavior at the Qt boundary."""

import ctypes
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from sukuna_pet.chat_window import ChatWindow
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.settings_window import SettingsWindow
from test_chat_controller import configured


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def action(tray: QSystemTrayIcon, text: str) -> QAction:
    return next(item for item in tray.contextMenu().actions() if item.text() == text)


def test_tray_reuses_settings_and_chat_and_restores_pet(app: QApplication) -> None:
    pet = PetWindow(PetApplication(), credentials=configured())
    pet.show()
    tray = pet.findChild(QSystemTrayIcon)
    assert tray is not None and tray.isVisible() and not tray.icon().isNull()
    assert tray.toolTip() == "宿傩桌宠"
    try:
        action(tray, "桌宠设置").trigger()
        settings = pet.findChild(SettingsWindow)
        assert settings is not None and settings.isVisible()
        settings.close()
        action(tray, "桌宠设置").trigger()
        assert settings.isVisible() and pet.findChildren(SettingsWindow) == [settings]
        settings.close()
        action(tray, "AI 对话").trigger()
        QTest.qWait(40)
        chat = pet.findChild(ChatWindow)
        assert chat is not None and chat.isVisible()
        assert chat.windowType() == Qt.WindowType.Window
        chat.close()
        assert pet.isVisible() and tray.isVisible()
        action(tray, "AI 对话").trigger()
        QTest.qWait(40)
        assert chat.isVisible() and pet.findChildren(ChatWindow) == [chat]
        chat.close()
        pet.hide()
        action(tray, "显示桌宠").trigger()
        assert pet.isVisible()
        pet.hide()
        tray.activated.emit(QSystemTrayIcon.ActivationReason.DoubleClick)
        assert pet.isVisible() and tray.isVisible()
        action(tray, "退出").trigger()
        assert not pet.isVisible() and not tray.isVisible()
        assert not pet.credentials.snapshot()
    finally:
        pet.close()
        pet.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows native taskbar styles")
def test_only_pet_has_native_tool_window_style(app: QApplication) -> None:
    if app.platformName() != "windows":
        pytest.skip("Requires the native Windows Qt platform")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    get_style = user32.GetWindowLongPtrW
    get_style.argtypes = [ctypes.c_void_p, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    pet = PetWindow(PetApplication(), credentials=configured())
    try:
        pet.show()
        pet.open_chat()
        chat = pet.findChild(ChatWindow)
        assert chat is not None
        app.processEvents()
        pet_style = get_style(int(pet.winId()), -20)  # GWL_EXSTYLE
        chat_style = get_style(int(chat.winId()), -20)
        assert pet_style & 0x00000080  # WS_EX_TOOLWINDOW: skips taskbar/Alt+Tab
        assert not pet_style & 0x00040000  # WS_EX_APPWINDOW
        assert not chat_style & 0x00000080
    finally:
        pet.close()
        pet.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_real_event_loop_survives_child_close_and_exits_from_tray() -> None:
    # A Tool window defaults to WA_QuitOnClose=False. Test the actual event
    # loop so a visually closed pet cannot leave a tray-less background app.
    script = textwrap.dedent('''
        import sys
        sys.path.insert(0, "src")
        sys.path.insert(0, "tests")
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication, QSystemTrayIcon
        import sukuna_pet.desktop as desktop
        from sukuna_pet.playback import PetApplication
        from sukuna_pet.settings_window import SettingsWindow
        from sukuna_pet.chat_window import ChatWindow
        from test_chat_controller import configured

        original = desktop.PetWindow
        seen = []
        def create():
            pet = original(PetApplication(), credentials=configured())
            tray = pet.findChild(QSystemTrayIcon)
            def close_children():
                pet.open_settings()
                pet.findChild(SettingsWindow).close()
                pet.open_chat()
                pet.findChild(ChatWindow).close()
            def exit_tray():
                assert pet.isVisible() and tray.isVisible()
                seen.append("still_running")
                next(a for a in tray.contextMenu().actions() if a.text() == "退出").trigger()
                assert not tray.isVisible()
            QTimer.singleShot(50, close_children)
            QTimer.singleShot(250, exit_tray)
            QTimer.singleShot(4000, lambda: QApplication.instance().exit(97))
            return pet
        desktop.PetWindow = create
        result = desktop.main()
        assert result == 0 and seen == ["still_running"], (result, seen)
        print("tray_lifecycle_ok")
    ''')
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "tray_lifecycle_ok" in result.stdout
