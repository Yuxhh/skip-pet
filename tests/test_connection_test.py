"""Provider requests and async delivery through the public connection boundary."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from collections.abc import Iterator

import pytest
from PySide6.QtCore import QObject, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import sukuna_pet.connection_test as connection
from sukuna_pet.connection_test import ConnectionResult, ConnectionTester


@contextmanager
def server(status: int = 200, body: bytes | None = None, *,
           redirect: str = "", gate: threading.Event | None = None) -> Iterator[tuple[str, list[dict]]]:
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            received.append({"path": self.path, "authorization": self.headers.get("Authorization"),
                             "payload": json.loads(self.rfile.read(int(self.headers["Content-Length"])))})
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if redirect:
                self.send_header("Location", redirect)
            self.end_headers()
            if gate is not None:
                gate.wait(15)
            try:
                self.wfile.write(body if body is not None else json.dumps({"choices": [
                    {"message": {"content": "OK"}, "finish_reason": "stop"}]}).encode())
            except (BrokenPipeError, ConnectionResetError):
                pass  # Expected when exercising the client's timeout.

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{http.server_port}/chat/completions", received
    finally:
        http.shutdown()
        http.server_close()
        thread.join(2)


def test_authorization_is_not_forwarded_on_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    with server() as (other_endpoint, other_requests):
        with server(307, redirect=other_endpoint) as (endpoint, requests):
            monkeypatch.setattr(connection, "ENDPOINT", endpoint)
            result = connection.test_connection("unit-redirect-key")
    assert not result.ok and len(requests) == 1 and not other_requests


def test_stalled_http_response_times_out_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    release = threading.Event()
    with server(gate=release) as (endpoint, requests):
        monkeypatch.setattr(connection, "ENDPOINT", endpoint)
        started = time.monotonic()
        try:
            result = connection.test_connection("unit-stalled")
        finally:
            release.set()
        assert not result.ok and "超时" in result.message
        assert time.monotonic() - started < 14
        assert len(requests) == 1


def test_probe_sends_one_fixed_short_request_and_does_not_return_response_content(monkeypatch: pytest.MonkeyPatch) -> None:
    with server() as (endpoint, requests):
        monkeypatch.setattr(connection, "ENDPOINT", endpoint)
        result = connection.test_connection("unit-test-key")
    assert result.ok and len(requests) == 1
    request = requests[0]
    assert request["path"] == "/chat/completions"
    assert request["authorization"] == "Bearer unit-test-key"
    assert request["payload"] == {
        "model": "deepseek-flash", "thinking": {"type": "disabled"}, "stream": False,
        "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 8,
    }
    assert "unit-test-key" not in repr(result) and "OK" not in result.message


@pytest.mark.parametrize("status,expected", [(401, "Key 无效"), (402, "余额不足"),
                                           (429, "限流"), (503, "繁忙"), (400, "参数")])
def test_errors_are_classified_without_echo_or_retry(status: int, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with server(status, b'{"error":"unit-sensitive-echo"}') as (endpoint, requests):
        monkeypatch.setattr(connection, "ENDPOINT", endpoint)
        result = connection.test_connection("unit-sensitive-echo")
    assert not result.ok and expected in result.message
    assert "unit-sensitive-echo" not in repr(result) and len(requests) == 1


@pytest.mark.parametrize("body", [b"bad-json", b"{}", b'{"choices":[]}',
                                   b'{"choices":[{"message":{"content":""},"finish_reason":"stop"}]}',
                                   b'{"choices":[{"message":{"content":"OK"},"finish_reason":null}]}',
                                   b"x" * 65537], ids=["invalid-json", "missing-choices", "empty-choices", "empty-content", "unfinished", "oversized"])
def test_invalid_or_incomplete_response_is_not_success(body: bytes, monkeypatch: pytest.MonkeyPatch) -> None:
    with server(body=body) as (endpoint, requests):
        monkeypatch.setattr(connection, "ENDPOINT", endpoint)
        assert not connection.test_connection("unit-key").ok
    assert len(requests) == 1


def test_missing_key_and_bad_header_fail_safely_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    with server() as (endpoint, requests):
        monkeypatch.setattr(connection, "ENDPOINT", endpoint)
        assert not connection.test_connection("").ok
        assert not connection.test_connection("unit-key\nprivate-header").ok
    assert not requests


def test_old_worker_cannot_complete_new_request_or_crash_destroyed_qt_owner() -> None:
    app = QApplication.instance() or QApplication([])
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def probe(key: str) -> ConnectionResult:
        if key == "old":
            started.set()
            release.wait(5)
        finished.set()
        return ConnectionResult(True, key)

    owner = QObject()
    tester = ConnectionTester(owner, probe)
    delivered: list[ConnectionResult] = []
    tester.completed.connect(delivered.append)
    tester.start("old")
    assert started.wait(2)
    tester.invalidate()
    tester.start("new")
    deadline = time.monotonic() + 3
    while not delivered and time.monotonic() < deadline:
        QTest.qWait(10)
        time.sleep(.005)
    assert [result.message for result in delivered] == ["new"]
    assert not tester.busy
    owner.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    finished.clear()
    release.set()
    assert finished.wait(2)
    QTest.qWait(30)
    assert [result.message for result in delivered] == ["new"]


def test_gui_watchdog_bounds_a_blocked_provider_and_ignores_its_late_result() -> None:
    app = QApplication.instance() or QApplication([])
    release = threading.Event()

    def blocked_provider(key: str) -> ConnectionResult:
        release.wait(40)
        return ConnectionResult(True, "late-result")

    owner = QObject()
    tester = ConnectionTester(owner, blocked_provider)
    delivered: list[ConnectionResult] = []
    tester.completed.connect(delivered.append)
    started = time.monotonic()
    try:
        tester.start("unit-watchdog")
        while not delivered and time.monotonic() - started < 35:
            QTest.qWait(20)
            time.sleep(.005)
        assert len(delivered) == 1 and not delivered[0].ok and "超时" in delivered[0].message
        assert not tester.busy
        release.set()
        QTest.qWait(50)
        time.sleep(.03)
        QTest.qWait(50)
        assert len(delivered) == 1
    finally:
        release.set()
        owner.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
