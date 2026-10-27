"""Native input and lifecycle at the agreed Qt window seam."""

from pathlib import Path
import threading

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QInputMethodEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sukuna_pet.chat_controller import ChatController
from sukuna_pet.chat_provider import DeepSeekProvider
from sukuna_pet.chat_window import ChatWindow
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.task_bubble import TaskBubble
from sukuna_pet.settings_window import SettingsWindow
from test_chat_controller import configured, wait_for
from test_chat_provider import event, sse_server
from test_modes_desktop import choose


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_menu_opens_one_independent_window_and_close_preserves_running_session(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pet = PetWindow(PetApplication(), credentials=configured())
    pet.show()
    try:
        choose(pet, "AI 对话", monkeypatch)
        QTest.qWait(40)
        chat = pet.findChild(ChatWindow)
        assert chat is not None and chat.isVisible() and chat.isWindow()
        pet.open_chat()
        assert pet.findChildren(ChatWindow) == [chat]
        chat.close()
        assert pet.isVisible() and not chat.isVisible()
        pet.open_chat()
        assert pet.findChild(ChatWindow) is chat and chat.isVisible()
    finally:
        pet.close()
        pet.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_native_input_wait_stop_close_reopen_and_manual_retry(app: QApplication) -> None:
    gate = threading.Event()
    with sse_server([], gate=gate) as (endpoint, requests):
        controller = ChatController(configured(), provider=DeepSeekProvider(endpoint=endpoint))
        chat = ChatWindow(controller)
        chat.show()
        try:
            chat.input.setPlainText("第一行")
            QTest.keyClick(chat.input, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
            chat.input.insertPlainText("第二行")
            assert "\n" in chat.input.toPlainText()
            QTest.keyClick(chat.input, Qt.Key.Key_Return)
            wait_for(lambda: len(requests) == 1)
            assert controller.busy and "正在生成" in chat.status.text()
            assert chat.send_button.text() == "停止" and not chat.input.toPlainText()
            chat.send_button.click()
            assert not controller.busy and controller.can_retry
            assert "未完成" in chat.transcript.toPlainText()
            assert chat.retry_button.isVisible() and "再次消耗" in chat.retry_button.toolTip()
            chat.close()
            gate.set()
            wait_for(lambda: controller.running_workers == 0)
            chat.open_window()
            assert len(requests) == 1 and controller.session.messages[-1].content == ""
            chat.retry_button.click()
            wait_for(lambda: not controller.busy)
            assert len(requests) == 2
            assert controller.session.messages[-1].content == "迟到"
            assert "迟到" in chat.transcript.toPlainText()
        finally:
            gate.set()
            chat.close()
            chat.deleteLater()
            controller.deleteLater()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_narrow_window_and_multiline_growth_keep_composer_controls_reachable(app: QApplication) -> None:
    controller = ChatController(configured())
    chat = ChatWindow(controller)
    try:
        chat.resize(560, 480)
        chat.show()
        QTest.qWait(40)
        assert not chat.sidebar.isVisible()
        start_height = chat.input.height()
        chat.input.setPlainText("一行\n" * 10)
        QTest.qWait(40)
        assert start_height < chat.input.height() <= 160
        assert chat.rect().contains(chat.send_button.mapTo(chat, chat.send_button.rect().bottomRight()))
        assert chat.input.verticalScrollBar().maximum() > 0
    finally:
        chat.close()
        chat.deleteLater()
        controller.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_missing_key_preserves_input_and_opens_existing_settings(app: QApplication) -> None:
    store = configured()
    store.clear()
    pet = PetWindow(PetApplication(), credentials=store)
    try:
        pet.show()
        pet.open_chat()
        chat = pet.findChild(ChatWindow)
        assert chat is not None
        chat.input.setPlainText("保留我的问题")
        chat.send_button.click()
        assert chat.input.toPlainText() == "保留我的问题"
        assert not chat.controller.session.messages
        chat.configure_button.click()
        settings = pet.findChild(SettingsWindow)
        assert settings is not None and settings.isVisible()
        assert settings.navigation.currentItem().text() == "AI 对话"
    finally:
        pet.close()
        pet.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_ime_enter_does_not_send_and_close_midstream_cannot_change_pet_state(app: QApplication) -> None:
    gate = threading.Event()
    with sse_server([event("部分内容")], gate=gate) as (endpoint, requests):
        pet_application = PetApplication()
        pet_application.select_mode("task")
        pet = PetWindow(pet_application, credentials=configured())
        controller = ChatController(pet.credentials, provider=DeepSeekProvider(endpoint=endpoint))
        chat = ChatWindow(controller, pet)
        try:
            pet.show()
            chat.show()
            chat.input.setPlainText("问题")
            QApplication.sendEvent(chat.input, QInputMethodEvent("拼音", []))
            QTest.keyClick(chat.input, Qt.Key.Key_Return)
            assert not requests and not controller.session.messages
            QApplication.sendEvent(chat.input, QInputMethodEvent("", []))
            chat.input.setPlainText("问题")
            QTest.keyClick(chat.input, Qt.Key.Key_Return)
            wait_for(lambda: controller.session.messages[-1].content == "部分内容")
            unchanged = pet_application.view
            QTest.qWait(80)
            assert pet_application.view == unchanged and unchanged.holding
            bubble = pet.findChild(TaskBubble)
            assert bubble is not None and not bubble.isVisible()
            chat.close()
            assert not controller.busy and controller.session.messages[-1].state == "incomplete"
            gate.set()
            wait_for(lambda: controller.running_workers == 0)
            chat.open_window()
            assert controller.session.messages[-1].content == "部分内容" and len(requests) == 1
            assert pet.isVisible()
        finally:
            gate.set()
            chat.close()
            pet.close()
            pet.deleteLater()
            controller.deleteLater()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
