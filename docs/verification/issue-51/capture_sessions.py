"""Native layout evidence using temporary records and synthetic text, no Key."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

from sukuna_pet.chat_controller import ChatController
from sukuna_pet.chat_window import ChatWindow
from sukuna_pet.credentials import CredentialStore
from sukuna_pet.session_store import SessionStore


class UnavailableVault:
    def read(self) -> str:
        raise OSError()

    def write(self, value: str) -> None:
        raise OSError()

    def delete(self) -> None:
        raise OSError()


app = QApplication([])
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
with TemporaryDirectory(prefix="sessions-", dir=output) as folder:
    store = SessionStore(Path(folder))
    controller = ChatController(CredentialStore(UnavailableVault()), store=store)
    controller.session.add_message("user", "一个小时怎么复习？")
    controller.session.add_message("assistant", "先做题找薄弱点，再集中订正。", state="incomplete")
    first = controller.session.id
    controller.save_all()
    controller.new_session()
    controller.session.add_message("user", "另一段独立对话")
    controller.save_all()
    controller.select_session(first)
    assert store.flush()
    chat = ChatWindow(controller)
    chat.show()
    QTest.qWait(80)
    assert chat.session_list.count() == 2
    assert chat.grab().save(str(output / "sessions.png"))
    chat.resize(560, 480)
    QTest.qWait(50)
    assert not chat.sidebar.isVisible()
    next(b for b in chat.findChildren(QPushButton) if b.text() == "◫").click()
    QTest.qWait(50)
    assert chat.sidebar.isVisible()
    for widget in (chat.session_list, chat.new_session_button, chat.delete_session_button, chat.send_button):
        assert chat.rect().contains(widget.mapTo(chat, widget.rect().bottomRight()))
    assert chat.grab().save(str(output / "narrow-sidebar.png"))
    chat.resize(1040, 760)
    captured: list[bool] = []

    def capture_dialog() -> None:
        dialog = QApplication.activeModalWidget()
        if not isinstance(dialog, QMessageBox):
            QTimer.singleShot(10, capture_dialog)
            return
        assert dialog.grab().save(str(output / "save-failed-close.png"))
        next(b for b in dialog.buttons() if b.text() == "取消关闭").click()
        captured.append(True)

    with patch("os.replace", side_effect=PermissionError()):
        controller.session.add_message("user", "这条消息尚未保存")
        controller.save_all()
        assert not store.flush()
        QTest.qWait(80)
        assert "尚未保存" in chat.status.text()
        assert chat.grab().save(str(output / "unsaved.png"))
        assert not chat.close()
        QTimer.singleShot(10, capture_dialog)
        for _ in range(100):
            if captured:
                break
            QTest.qWait(10)
        assert captured and chat.isVisible()
    controller.save_all()
    assert store.flush()
    metrics = {"dpr": chat.devicePixelRatioF(), "sessions": chat.session_list.count(),
               "narrow_sidebar_controls_reachable": True, "cancel_close_preserved_window": True}
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    chat.close()
    store.close()
print(metrics)
