"""Native Qt layout evidence with synthetic text and no credential access."""

from pathlib import Path
import sys

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sukuna_pet.chat_controller import ChatController
from sukuna_pet.chat_window import ChatWindow
from sukuna_pet.credentials import CredentialStore


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
controller = ChatController(CredentialStore(UnavailableVault()))
chat = ChatWindow(controller)
chat.show()
QTest.qWait(80)
assert chat.grab().save(str(output / "empty.png"))
controller.session.add_message("user", "我只有一个小时复习，怎么安排？")
controller.session.add_message("assistant", "别拿翻书装用功。十分钟找薄弱点，三十五分钟做题并订正，最后十五分钟合上书自测。先收拾最容易丢分的地方。")
controller.session.add_message("user", "可我连自己的薄弱点都不知道。")
controller.session.add_message("assistant", "（嗤笑）那就先做几道不同题型的题，不看答案。哪类做不出、说不清理由，就从哪类下手。", state="incomplete")
controller.notice = "已停止，回复未完成；停止不保证服务端立即停止计算或计费。"
controller.changed.emit()
QTest.qWait(80)
assert chat.grab().save(str(output / "conversation.png"))
chat.resize(560, 480)
chat.input.setPlainText("先从哪门课开始？\n我想继续问具体的安排。")
QTest.qWait(80)
assert not chat.sidebar.isVisible()
for widget in (chat.input, chat.send_button, chat.retry_button, chat.status):
    assert chat.rect().contains(widget.mapTo(chat, widget.rect().bottomRight()))
assert chat.grab().save(str(output / "incomplete-narrow.png"))
print(f"DPR={chat.devicePixelRatioF()}, narrow={chat.width()}x{chat.height()}, controls reachable")
chat.close()
