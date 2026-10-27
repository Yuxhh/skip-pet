"""Multi-session operations and restart through the controller boundary."""

from pathlib import Path
import threading

import pytest
from PySide6.QtWidgets import QApplication

from sukuna_pet.chat_controller import ChatController
from sukuna_pet.chat_provider import DeepSeekProvider
from sukuna_pet.chat_session import AuthorPrompt
from sukuna_pet.session_store import SessionStore
from sukuna_pet.chat_window import ChatWindow
from test_chat_controller import configured, wait_for
from test_chat_provider import event, sse_server


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_new_and_switch_stop_original_and_restart_isolates_prompt_snapshots(
    app: QApplication, tmp_path: Path,
) -> None:
    gate = threading.Event()
    old = AuthorPrompt("v1", "旧作者正文", "旧补充")
    new = AuthorPrompt("v2", "新版正文", "新版补充")
    store = SessionStore(tmp_path)
    with sse_server([event("部分内容")], gate=gate) as (endpoint, requests):
        controller = ChatController(configured(), provider=DeepSeekProvider(endpoint=endpoint),
                                    store=store, author_prompt=old)
        original = controller.session.id
        try:
            assert controller.send("原问题")
            wait_for(lambda: controller.session.messages[-1].content == "部分内容")
            second = controller.new_session()
            assert second != original and not controller.busy
            assert not controller.session.messages
            gate.set()
            wait_for(lambda: controller.running_workers == 0)
            assert controller.select_session(original)
            assert controller.session.messages[-1].content == "部分内容"
            assert controller.session.messages[-1].state == "incomplete"
            assert controller.session.messages[0].request_id == controller.session.messages[-1].request_id
            assert store.flush()
            restored_store = SessionStore(tmp_path)
            restarted = ChatController(configured(), store=restored_store, author_prompt=new)
            try:
                assert restarted.select_session(original)
                assert restarted.session.prompt == old
                assert restarted.can_retry
                third = restarted.new_session()
                assert restarted.session.prompt == new
                assert restarted.select_session(second)
                assert restarted.session.prompt == old and not restarted.session.messages
                assert len({s.id for s in restarted.sessions}) == 3
                assert third not in (original, second)
            finally:
                restored_store.close()
                restarted.deleteLater()
        finally:
            gate.set()
            controller.stop()
            store.close()
            controller.deleteLater()


@pytest.mark.parametrize("retry", [False, True])
def test_close_restart_partial_reply_supports_followup_or_replacement(
    app: QApplication, tmp_path: Path, retry: bool,
) -> None:
    gate = threading.Event()
    store = SessionStore(tmp_path)
    with sse_server([event("已收部分")], gate=gate) as (endpoint, requests):
        controller = ChatController(configured(), store=store, provider=DeepSeekProvider(endpoint=endpoint))
        chat = ChatWindow(controller)
        chat.show()
        try:
            assert controller.send("原问题")
            wait_for(lambda: controller.session.messages[-1].content == "已收部分")
            user_id = controller.session.messages[0].id
            chat.close()
            wait_for(lambda: not chat.isVisible())
            assert store.flush()
            store.close()
            gate.set()
            restored_store = SessionStore(tmp_path)
            restored = ChatController(configured(), store=restored_store,
                                      provider=DeepSeekProvider(endpoint=endpoint))
            try:
                assert restored.session.messages[-1].state == "incomplete"
                assert restored.retry() if retry else restored.send("接着回答")
                wait_for(lambda: not restored.busy)
                assert restored_store.flush()
                messages = requests[-1]["payload"]["messages"]
                if retry:
                    assert messages[1:] == [{"role": "user", "content": "原问题"}]
                    assert len(restored.session.messages) == 2
                else:
                    assert messages[1:] == [
                        {"role": "user", "content": "原问题"},
                        {"role": "assistant", "content": "已收部分"},
                        {"role": "user", "content": "接着回答"},
                    ]
                assert restored.session.messages[0].id == user_id
                saved = SessionStore(tmp_path).load_all()[0]
                assert saved.messages[-1].state == "complete"
                assert saved.messages[-1].content == "已收部分迟到"
            finally:
                restored_store.close()
                restored.deleteLater()
        finally:
            gate.set()
            controller.stop()
            store.close()
            chat.deleteLater()
            controller.deleteLater()


def test_switch_running_request_then_return_cannot_accept_old_completion(
    app: QApplication, tmp_path: Path,
) -> None:
    store = SessionStore(tmp_path)
    gate = threading.Event()
    with sse_server([event("切走前正文")], gate=gate) as (endpoint, requests):
        controller = ChatController(configured(), store=store, provider=DeepSeekProvider(endpoint=endpoint))
        first = controller.session.id
        second = controller.new_session()
        controller.select_session(first)
        try:
            controller.send("旧问题")
            wait_for(lambda: controller.session.messages[-1].content == "切走前正文")
            assert controller.select_session(second)
            assert not controller.busy and not controller.session.messages
            assert controller.select_session(first)
            gate.set()
            wait_for(lambda: controller.running_workers == 0)
            assert controller.session.messages[-1].content == "切走前正文"
            assert controller.session.messages[-1].state == "incomplete"
            assert store.flush()
            first_saved = next(s for s in SessionStore(tmp_path).load_all() if s.id == first)
            assert first_saved.messages[-1].content == "切走前正文"
        finally:
            gate.set()
            controller.stop()
            store.close()
            controller.deleteLater()


def test_delete_active_generation_does_not_revive_or_touch_other_session(
    app: QApplication, tmp_path: Path,
) -> None:
    store = SessionStore(tmp_path)
    gate = threading.Event()
    with sse_server([event("将被删除")], gate=gate) as (endpoint, requests):
        controller = ChatController(configured(), store=store, provider=DeepSeekProvider(endpoint=endpoint))
        survivor = controller.session.id
        doomed = controller.new_session()
        try:
            assert controller.send("删掉这一段")
            wait_for(lambda: controller.session.messages[-1].content == "将被删除")
            assert controller.delete_session(doomed)
            assert not controller.busy and controller.session.id == survivor
            gate.set()
            wait_for(lambda: controller.running_workers == 0)
            assert not controller.select_session(doomed)
            assert store.flush()
            assert [s.id for s in SessionStore(tmp_path).load_all()] == [survivor]
            assert not controller.session.messages
            assert controller.delete_session(survivor)
            assert controller.session.id not in (survivor, doomed)
            assert len(controller.sessions) == 1
        finally:
            gate.set()
            controller.stop()
            store.close()
            controller.deleteLater()
