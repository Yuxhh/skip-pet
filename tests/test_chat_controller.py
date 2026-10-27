"""Conversation behavior through the public controller boundary."""

import threading
import time

from PySide6.QtCore import QEvent, QObject
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sukuna_pet.chat_controller import ChatController
from sukuna_pet.chat_provider import DeepSeekProvider
from sukuna_pet.chat_session import AuthorPrompt, ChatSession
from sukuna_pet.credentials import CredentialStore
from test_credentials import CredentialVault
from test_chat_provider import event, sse_server


def wait_for(predicate, seconds: float = 4) -> None:
    deadline = time.monotonic() + seconds
    while not predicate():
        assert time.monotonic() < deadline
        QTest.qWait(10)
        time.sleep(.005)


def configured() -> CredentialStore:
    store = CredentialStore(CredentialVault())
    store.save("unit-controller")
    return store


def test_session_retains_author_snapshot_and_complete_history_but_bounds_request() -> None:
    app = QApplication.instance() or QApplication([])
    controller = ChatController(CredentialStore(CredentialVault()))
    snapshot = controller.session.prompt
    assert snapshot.version == "sukuna-2026-10-27-v1"
    assert snapshot.body.startswith("你将扮演《咒术回战》中的两面宿傩 ——")
    assert "嘴上狂傲，内容有用" in snapshot.supplement
    for index in range(45):
        controller.session.add_message("user", f"旧问题{index}")
    messages = controller.session.request_messages("本轮" + "长" * 24001)
    assert len(controller.session.messages) == 45
    assert len(messages) == 42
    assert messages[1] == {"role": "user", "content": "旧问题5"}
    assert messages[-1]["content"].startswith("本轮") and len(messages[-1]["content"]) == 24003
    assert messages[0]["content"] == snapshot.body + "\n\n" + snapshot.supplement
    assert app is not None


def test_char_budget_matches_upstream_selection_without_truncating_session() -> None:
    controller = ChatController(configured())
    controller.session.add_message("user", "旧" * 10000)
    controller.session.add_message("assistant", "答" * 14000)
    assert len(controller.session.request_messages("本轮")) == 4  # exact 24,000 history + system + user
    controller.session.add_message("user", "新" * 10001)
    request = controller.session.request_messages("本轮")
    assert request[1] == {"role": "user", "content": "新" * 10001}
    assert len(request) == 3  # older 14,000 cannot fit; do not fill gaps or partly trim it
    controller.session.add_message("assistant", "不要传入" + "尾" * 24000)
    request = controller.session.request_messages("本轮")
    assert request[1] == {"role": "assistant", "content": "尾" * 24000}
    assert len(controller.session.messages[-1].content) == 24004


def test_restorable_old_author_snapshot_remains_the_request_system() -> None:
    old = AuthorPrompt("older-version", "旧作者原文", "旧补充规则")
    session = ChatSession(prompt=old)
    assert session.request_messages("你好")[0] == {"role": "system", "content": "旧作者原文\n\n旧补充规则"}
    assert session.prompt is old


def test_stop_is_immediate_but_worker_exits_later_and_retry_replaces_partial() -> None:
    app = QApplication.instance() or QApplication([])
    gate = threading.Event()
    with sse_server([event("部分")], gate=gate) as (endpoint, requests):
        controller = ChatController(configured(), provider=DeepSeekProvider(endpoint=endpoint))
        assert controller.send("原问题")
        assert controller.busy and controller.session.messages[-1].state == "generating"
        wait_for(lambda: controller.session.messages[-1].content == "部分")
        controller.stop()
        assert not controller.busy and controller.running_workers == 1
        assert controller.session.messages[-1].state == "incomplete"
        gate.set()
        wait_for(lambda: controller.running_workers == 0)
        QTest.qWait(30)
        assert controller.session.messages[-1].content == "部分"
        assert len(requests) == 1  # No automatic billable retry.
        assert controller.retry()
        wait_for(lambda: not controller.busy)
        assert len(requests) == 2
        assert len(controller.session.messages) == 2
        assert requests[-1]["payload"]["messages"][-1] == {"role": "user", "content": "原问题"}
        assert len(requests[-1]["payload"]["messages"]) == 2  # system + original question only.
        assert controller.session.messages[-1].content == "部分迟到"
        assert controller.session.messages[-1].state == "complete"
        assert "再次消耗" in controller.retry_notice
    assert app is not None


def test_followup_includes_partial_reply_but_not_reasoning() -> None:
    app = QApplication.instance() or QApplication([])
    with sse_server([event("有用的部分", reasoning="secret-reasoning")]) as (endpoint, requests):
        controller = ChatController(configured(), provider=DeepSeekProvider(endpoint=endpoint))
        controller.send("问题一")
        wait_for(lambda: not controller.busy)
        assert controller.error_kind == "interrupted"
        assert controller.send("接着说")
        wait_for(lambda: not controller.busy)
    assert requests[1]["payload"]["messages"][1:] == [
        {"role": "user", "content": "问题一"}, {"role": "assistant", "content": "有用的部分"},
        {"role": "user", "content": "接着说"},
    ]
    assert "secret-reasoning" not in repr(controller.session)
    assert app is not None


def test_missing_key_sends_nothing_and_invalid_key_requires_manual_retry_with_new_snapshot() -> None:
    app = QApplication.instance() or QApplication([])
    store = CredentialStore(CredentialVault())
    with sse_server([], status=401) as (endpoint, requests):
        controller = ChatController(store, provider=DeepSeekProvider(endpoint=endpoint))
        assert not controller.send("待发送问题") and controller.needs_settings
        assert not controller.session.messages and not requests
        store.save("unit-wrong")
        assert controller.send("待发送问题")
        wait_for(lambda: not controller.busy)
        assert controller.error_kind == "invalid_key" and controller.needs_settings
        store.save("unit-updated")
        QTest.qWait(40)
        assert len(requests) == 1
        assert controller.retry()
        wait_for(lambda: not controller.busy)
        assert requests[-1]["authorization"] == "Bearer unit-updated"
        assert len(requests) == 2 and len(controller.session.messages) == 2
        store.clear()
        assert not controller.retry() and len(requests) == 2
    assert app is not None


def test_watchdog_stops_gui_before_worker_cleanup_and_destroyed_owner_ignores_events() -> None:
    app = QApplication.instance() or QApplication([])
    gate = threading.Event()
    with sse_server([], gate=gate) as (endpoint, requests):
        owner = QObject()
        controller = ChatController(configured(), owner, provider=DeepSeekProvider(endpoint=endpoint),
                                    generation_timeout_ms=300)
        assert controller.send("等不到首字")
        wait_for(lambda: bool(requests))
        wait_for(lambda: not controller.busy)
        assert controller.error_kind == "timeout" and controller.running_workers == 1
        assert controller.session.messages[-1].state == "incomplete"
        owner.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gate.set()
        wait_for(lambda: controller.running_workers == 0)
        assert controller.session.messages[-1].content == ""


def test_cancel_cleanup_is_bounded_even_when_user_repeatedly_retries() -> None:
    app = QApplication.instance() or QApplication([])
    gate = threading.Event()
    with sse_server([], gate=gate) as (endpoint, requests):
        controller = ChatController(configured(), provider=DeepSeekProvider(endpoint=endpoint))
        try:
            controller.send("原问题")
            for count in range(1, 5):
                wait_for(lambda: len(requests) == count)
                controller.stop()
                if count < 4:
                    assert controller.retry()
            assert not controller.retry()
            assert controller.error_kind == "cleanup" and controller.running_workers == 4
            assert len(requests) == 4 and len(controller.session.messages) == 2
            gate.set()
            wait_for(lambda: controller.running_workers == 0)
            assert controller.retry()
            wait_for(lambda: not controller.busy)
            assert len(requests) == 5
        finally:
            gate.set()
            controller.stop()
    assert app is not None


def test_credentials_changed_midstream_affect_only_next_manually_sent_request() -> None:
    app = QApplication.instance() or QApplication([])
    gate = threading.Event()
    store = configured()
    with sse_server([event("正文")], gate=gate) as (endpoint, requests):
        controller = ChatController(store, provider=DeepSeekProvider(endpoint=endpoint))
        controller.send("第一问")
        wait_for(lambda: controller.session.messages[-1].content == "正文")
        store.clear()
        store.save("unit-next-snapshot")
        QTest.qWait(30)
        assert len(requests) == 1 and requests[0]["authorization"] == "Bearer unit-controller"
        assert controller.busy
        gate.set()
        wait_for(lambda: not controller.busy)
        assert controller.session.messages[-1].state == "complete"
        assert controller.send("追问")
        wait_for(lambda: not controller.busy)
        assert len(requests) == 2 and requests[-1]["authorization"] == "Bearer unit-next-snapshot"
        assert "unit-next-snapshot" not in repr(controller.session)
    assert app is not None
