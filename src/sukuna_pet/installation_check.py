"""Opt-in frozen-runtime verification with synthetic data and an isolated vault.

No service request, production credential or host profile is accessed.
Run SukunaPet.exe --verify-installation NEW_DIRECTORY; inspect result.json.
"""

import json
import ctypes
from pathlib import Path
import ssl
import subprocess
import sys
from uuid import uuid4

from PySide6.QtCore import QStandardPaths, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu
from PySide6.QtTest import QTest

from .chat_session import AUTHOR_PROMPT, ChatSession
from .credentials import CredentialStore, WindowsCredentialBackend
from .session_store import SessionStore


def _readback(root: Path, target: str) -> None:
    assert WindowsCredentialBackend(target).read() == "synthetic-installation-probe"
    store = SessionStore(root / "sessions")
    try:
        sessions = store.load_all()
        assert len(sessions) == 1
        assert sessions[0].prompt == AUTHOR_PROMPT
        assert sessions[0].messages[-1].content == "合成的未完成回复"
        assert sessions[0].messages[-1].state == "incomplete"
    finally:
        assert store.close()
    (root / "readback.json").write_text(json.dumps({
        "credential_read_in_second_process": True,
        "session_and_prompt_restored_in_second_process": True,
        "generating_restored_as_incomplete": True,
    }), encoding="utf-8")


def verify(root: Path) -> dict[str, object]:
    from .chat_window import ChatWindow
    from .desktop import PetWindow
    from .settings_window import SettingsWindow, product_version

    root.mkdir(parents=True, exist_ok=False)
    target = "skip-pet/installation-check/" + uuid4().hex
    backend = WindowsCredentialBackend(target)
    credentials = CredentialStore(backend)
    assert not credentials.snapshot()
    try:
        credentials.save("synthetic-installation-probe")
        assert credentials.safely_saved
        store = SessionStore(root / "sessions")
        session = ChatSession()
        session.add_message("user", "安装验证合成问题")
        session.add_message("assistant", "合成的未完成回复", state="generating")
        store.save(session)
        assert store.close()
        command = ([sys.executable] if getattr(sys, "frozen", False) else
                   [sys.executable, "-m", "sukuna_pet"])
        child = subprocess.run(command + ["--verify-installation-readback", str(root), target],
                               capture_output=True, timeout=30)
        assert child.returncode == 0, "Frozen child readback failed"
        result: dict[str, object] = json.loads((root / "readback.json").read_text())
        assert credentials.clear() and not backend.read()
        # Force the real Windows adapter's documented 2560-byte size failure.
        credentials.save("x" * 1300)
        assert not credentials.safely_saved and len(credentials.snapshot()) == 1300
        assert "重启" in credentials.notice and not backend.read()
        credentials.release()
        assert not CredentialStore(backend).snapshot()
        result["credential_delete_and_memory_fallback"] = True

        app = QApplication.instance() or QApplication([])
        assert isinstance(app, QApplication)
        app.setOrganizationName("skip-pet")
        app.setApplicationName("sukuna-pet")
        app.setQuitOnLastWindowClosed(False)
        result["default_config_directory"] = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation)
        result["default_data_directory"] = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation)
        path = root / "mode.json"
        original = {"mode": "always", "size": 271, "future": {"keep": True},
                    "dsh_bridge": {"enabled": False, "profiles": [], "future": "keep"}}
        path.write_text(json.dumps(original), encoding="utf-8")
        pet = PetWindow(settings_path=path, credentials=credentials,
                        chat_data_dir=root / "sessions")
        try:
            pet.show()
            assert pet.pet_mode == "always" and pet.height() == 271
            # Exercise the real right-click dispatcher in the frozen runtime.
            # A direct open_chat call misses native popup activation failures.
            deferred: list[bool] = []
            select = QTimer(pet)
            select.setSingleShot(True)
            watchdog = QTimer(pet)
            watchdog.setSingleShot(True)

            def select_chat() -> None:
                popup = app.activePopupWidget()
                if not isinstance(popup, QMenu):
                    select.start(10)
                    return
                action = next(a for a in popup.actions() if a.text() == "AI 对话")
                action.trigger()
                # Deliver queued slots while the popup is still tracking.
                QTest.qWait(120)
                deferred.append(pet.findChild(ChatWindow) is None)
                popup.close()

            def dismiss_popup() -> None:
                popup = app.activePopupWidget()
                if popup is not None:
                    popup.close()

            select.timeout.connect(select_chat)
            watchdog.timeout.connect(dismiss_popup)
            select.start(100)
            watchdog.start(3000)
            point = pet.visible_region.boundingRect().center()
            QApplication.sendEvent(pet, QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, point, pet.mapToGlobal(point)))
            select.stop()
            watchdog.stop()
            QTest.qWait(150)
            assert deferred == [True], "Chat opened inside the native menu loop"
            chat = pet.findChild(ChatWindow)
            assert chat is not None and chat.isVisible()
            result["native_context_menu_opens_chat_after_popup"] = True
            result["native_menu_tracking_defers_chat"] = True
            if sys.platform == "win32" and app.platformName() == "windows":
                visible = ctypes.WinDLL("user32").IsWindowVisible
                visible.argtypes = [ctypes.c_void_p]
                visible.restype = ctypes.c_int
                assert visible(int(chat.winId())), "Chat is hidden in Windows"
                result["windows_chat_visible"] = True
            pet.open_chat()
            assert len(pet.findChildren(ChatWindow)) == 1
            assert chat.controller.session.messages[-1].state == "incomplete"
            assert chat.controller.store is not None and chat.controller.store.flush()
            assert chat.close() and pet.isVisible()
            pet.open_chat()
            assert pet.findChild(ChatWindow) is chat and chat.isVisible()
            if sys.platform == "win32" and app.platformName() == "windows":
                assert visible(int(chat.winId())), "Reopened chat is hidden in Windows"
                result["windows_reopened_chat_visible"] = True
            pet.open_settings("AI 对话")
            settings = pet.findChild(SettingsWindow)
            assert settings is not None
            pet.open_settings("关于")
            assert len(pet.findChildren(SettingsWindow)) == 1
            settings.close()
            pet.select_mode("click")
            pet.select_size(188)
            saved = json.loads(path.read_text())
            assert saved == dict(original, mode="click", size=188)
            app.processEvents()
            chat.grab().save(str(root / "chat.png"))
            pet.open_settings("AI 对话")
            settings.grab().save(str(root / "settings.png"))
            assert pet.close()
            assert chat.controller.store.close()
        finally:
            pet.close()
        result.update(native_window_lifecycle=True, preferences_upgrade_compatible=True,
                      version=product_version(), prompt_version=AUTHOR_PROMPT.version,
                      qt_platform=app.platformName(), frozen=bool(getattr(sys, "frozen", False)),
                      executable=str(Path(sys.executable).resolve()))
        assert ssl.create_default_context().cert_store_stats()["x509_ca"] > 0
        result["windows_tls_ca_store_available"] = True
        for record in root.rglob("*.json"):
            assert "synthetic-installation-probe" not in record.read_text(encoding="utf-8")
        result["synthetic_credential_absent_from_records"] = True
        return result
    finally:
        backend.delete()
        credentials.release()


def main(arguments: list[str], *, readback: bool = False) -> int:
    if len(arguments) != (2 if readback else 1):
        return 2
    root = Path(arguments[0]).resolve()
    if not readback and root.exists():
        return 2
    try:
        if readback:
            _readback(root, arguments[1])
        else:
            result = verify(root)
            (root / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False),
                                             encoding="utf-8")
        return 0
    except Exception as error:
        # Exception messages may contain sensitive data; record only the type.
        root.mkdir(parents=True, exist_ok=True)
        (root / "failure.json").write_text(json.dumps({"error_type": type(error).__name__}),
                                          encoding="utf-8")
        return 1
