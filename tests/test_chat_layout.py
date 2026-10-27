"""Confirmed native window boundary: layout remains usable with real content."""

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from sukuna_pet.chat_controller import ChatController
from sukuna_pet.chat_window import ChatWindow
from test_chat_controller import configured


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_empty_composer_matches_confirmed_compact_width_and_height(app: QApplication) -> None:
    controller = ChatController(configured())
    chat = ChatWindow(controller)
    chat.resize(1440, 900)
    chat.show()
    try:
        QTest.qWait(40)
        composer = chat.input.parentWidget()
        assert composer is not None
        assert composer.width() == 720
        assert 100 <= composer.height() <= 120
        assert abs(composer.mapTo(chat, composer.rect().center()).y() - chat.height() / 2) < 180
    finally:
        chat.close()
        chat.deleteLater()
        controller.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_long_title_and_multiline_draft_do_not_expand_narrow_window(app: QApplication) -> None:
    controller = ChatController(configured())
    controller.session.add_message("user", "W" * 200)
    controller.session.add_message("assistant", "正文\n" * 100, state="incomplete")
    chat = ChatWindow(controller)
    chat.resize(560, 480)
    chat.show()
    try:
        chat.input.setPlainText("下一条草稿\n" * 20)
        QTest.qWait(60)
        assert chat.width() == 560
        next(b for b in chat.findChildren(QPushButton) if b.text() == "◫").click()
        QTest.qWait(40)
        assert chat.width() == 560
        for widget in (chat.new_session_button, chat.delete_session_button, chat.send_button,
                       chat.retry_button, chat.input):
            assert widget.isVisible()
            assert chat.rect().contains(widget.mapTo(chat, widget.rect().bottomRight()))
        assert chat.transcript.verticalScrollBar().maximum() > 0
        assert chat.transcript.horizontalScrollBar().maximum() == 0
    finally:
        chat.close()
        chat.deleteLater()
        controller.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_wrapped_draft_grows_when_window_becomes_narrow(app: QApplication) -> None:
    controller = ChatController(configured())
    chat = ChatWindow(controller)
    chat.resize(1440, 900)
    chat.show()
    try:
        chat.input.setPlainText("需要自动换行的草稿" * 12)
        QTest.qWait(40)
        wide_height = chat.input.height()
        chat.resize(560, 480)
        QTest.qWait(60)
        assert chat.input.height() > wide_height
        assert chat.input.height() <= 160
        assert chat.rect().contains(chat.send_button.mapTo(chat, chat.send_button.rect().bottomRight()))
    finally:
        chat.close()
        chat.deleteLater()
        controller.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
