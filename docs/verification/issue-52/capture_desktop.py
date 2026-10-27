"""Windows Qt evidence: temporary sessions and synthetic credentials only.

Run with PYTHONPATH=src;tests and QT_SCALE_FACTOR=1, 1.25 or 1.5.
No service request is made; network lifecycle is covered by the native tests.
"""

import json
import os
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PySide6 import __version__ as qt_binding
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QWidget

from sukuna_pet.chat_window import ChatWindow
from sukuna_pet.credentials import CredentialStore
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.settings_window import SettingsWindow
from test_credentials import CredentialVault
from test_chat_controller import wait_for


app = QApplication([])
assert app.platformName() == "windows"
output = Path(sys.argv[1]).resolve()
output.mkdir(parents=True, exist_ok=True)
metrics: dict = {"os": platform.platform(), "python": platform.python_version(), "pyside6": qt_binding,
                 "platform": app.platformName(), "scale_factor": os.environ.get("QT_SCALE_FACTOR", "1"),
                 "screens": [{"name": s.name(), "geometry": s.geometry().getRect(),
                              "available": s.availableGeometry().getRect(), "dpr": s.devicePixelRatio()}
                             for s in app.screens()], "captures": {}}


def capture(name: str, window: QWidget, controls: tuple[QWidget, ...] = ()) -> None:
    QTest.qWait(80)
    if isinstance(window, ChatWindow) and controls and window.content_scroll.isAncestorOf(controls[-1]):
        window.content_scroll.ensureWidgetVisible(controls[-1], 0, 12)
    wait_for(lambda: all(window.rect().contains(w.mapTo(window, w.rect().bottomRight())) for w in controls))
    for widget in controls:
        assert widget.isVisible(), (name, widget.accessibleName())
        assert window.rect().contains(widget.mapTo(window, widget.rect().topLeft())), name
        assert window.rect().contains(widget.mapTo(window, widget.rect().bottomRight())), (
            name, widget.accessibleName(), widget.objectName(), widget.mapTo(window, widget.rect().bottomRight()))
    assert window.grab().save(str(output / f"{name}.png"))
    metrics["captures"][name] = {"size": [window.width(), window.height()], "dpr": window.devicePixelRatioF(),
                                  "controls_reachable": len(controls)}
    if isinstance(window, ChatWindow):
        metrics["captures"][name]["outer_scroll"] = window.content_scroll.verticalScrollBar().value()


with TemporaryDirectory(prefix="desktop-", dir=output) as folder:
    root = Path(folder)
    preferences = root / "mode.json"
    credentials = CredentialStore(CredentialVault())
    pet = PetWindow(PetApplication(), settings_path=preferences, credentials=credentials,
                    chat_data_dir=root / "sessions")
    pet.show()
    pet.open_chat()
    chat = pet.findChild(ChatWindow)
    assert chat is not None
    controller = chat.controller
    store = controller.store
    assert store is not None
    chat.resize(1000, 640)
    chat.move(20, 30)
    controls = (chat.input, chat.send_button, chat.new_session_button, chat.delete_session_button)
    capture("empty", chat, controls)
    composer = chat.input.parentWidget()
    metrics["empty_composer"] = [composer.width(), composer.height()]
    chat.input.setPlainText("第一行草稿\n第二行草稿\n第三行草稿\n第四行草稿\n第五行草稿")
    capture("multiline", chat, controls)
    chat.resize(560, 480)
    chat.input.setPlainText("空会话中的长草稿\n" * 40)
    chat.send_button.click()
    capture("narrow-empty-multiline", chat, (chat.input, chat.send_button, chat.configure_button))
    assert chat.input.mapTo(chat, chat.input.rect().bottomRight()).y() < chat.send_button.mapTo(
        chat, chat.send_button.rect().topLeft()).y()
    metrics["empty_input_controls_do_not_overlap"] = True
    chat.input.clear()
    controller.new_session()
    chat.resize(1000, 640)
    chat.sidebar.show()
    controller.session.add_message("user", "我只有一个小时，怎么复习？")
    controller.session.add_message("assistant", "先挑最薄弱的两章。\n用四十分钟做题，剩下二十分钟只订正错题。")
    controller.save_all()
    capture("conversation", chat, controls)
    first = controller.session.id
    controller.new_session()
    for index in range(80):
        controller.session.add_message("user", f"第 {index + 1} 个问题：" + "连续内容" * 14)
        controller.session.add_message("assistant", "合成验证正文。\n" * 5)
    controller.session.add_message("user", "如何继续？")
    controller.session.add_message("assistant", "这段是停止后保留的部分回复。", state="incomplete")
    controller.save_all()
    capture("long-incomplete", chat, (*controls, chat.retry_button))
    assert chat.transcript.verticalScrollBar().maximum() > 0
    chat.transcript.verticalScrollBar().setValue(0)
    capture("history", chat, controls)
    next(b for b in chat.findChildren(QPushButton) if b.text() == "◫").click()
    capture("collapsed", chat, (chat.input, chat.send_button))
    chat.resize(560, 480)
    chat.input.setPlainText("多行草稿\n" * 20)
    capture("narrow", chat, (chat.input, chat.send_button, chat.retry_button))
    chat.input.clear()
    next(b for b in chat.findChildren(QPushButton) if b.text() == "◫").click()
    capture("narrow-sidebar", chat, controls)
    controller.select_session(first)
    chat.resize(1000, 640)
    chat.sidebar.show()
    assert store.flush()
    seen: list[str] = []

    def dialog_capture() -> None:
        dialog = QApplication.activeModalWidget()
        if not isinstance(dialog, QMessageBox):
            QTimer.singleShot(10, dialog_capture)
            return
        capture("unsaved-close", dialog, tuple(dialog.buttons()))
        seen.extend(button.text() for button in dialog.buttons())
        next(b for b in dialog.buttons() if b.text() == "取消关闭").click()

    with patch("os.replace", side_effect=PermissionError()):
        controller.session.add_message("user", "写盘失败时仍可见的内容")
        controller.save_all()
        assert not store.flush()
        wait_for(lambda: chat.save_retry_button.isVisible())
        capture("unsaved", chat, (*controls, chat.save_retry_button))
        assert not chat.close()
        QTimer.singleShot(10, dialog_capture)
        wait_for(lambda: bool(seen))
        assert chat.isVisible()
    controller.save_all()
    assert store.flush()
    metrics["close_choices"] = seen
    credentials.clear()
    chat.input.setPlainText("缺失 Key 时保留问题")
    chat.send_button.click()
    capture("missing-key", chat, (*controls, chat.configure_button))
    for page, suffix in (("桌宠", "pet"), ("任务联动", "bridge"), ("AI 对话", "ai"), ("关于", "about")):
        pet.open_settings(page)
        settings = pet.findChild(SettingsWindow)
        assert settings is not None
        settings.resize(560, 440)
        settings.move(80, 60)
        capture(f"settings-{suffix}", settings, (settings.navigation,))
        if page == "AI 对话":
            settings.key_input.setText("synthetic-validation-key")
            settings.save_key.click()
            assert credentials.safely_saved
            settings.key_input.setText("synthetic-unsaved-draft")
            settings.clear_key.click()
            assert not settings.key_input.text() and not credentials.snapshot()
            metrics["key_save_clear_draft"] = True
        settings.close()
    for _ in range(3):
        assert chat.close()
        pet.open_chat()
        assert pet.findChild(ChatWindow) is chat
        pet.open_settings()
        settings = pet.findChild(SettingsWindow)
        settings.close()
    metrics["repeated_open_close"] = 3
    assert pet.close()
    assert store.close()
    metrics["storage_closed_cleanly"] = True
(output / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"output": str(output), "captures": len(metrics["captures"]), "platform": app.platformName()}))
