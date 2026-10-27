"""Controlled HTTP/SSE responses exercise the real provider boundary."""

from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
from unittest.mock import patch

import pytest

from sukuna_pet.chat_provider import ChatError, DeepSeekProvider


def event(text: str = "", *, reason: str | None = None, reasoning: str = "") -> bytes:
    return ("data: " + json.dumps({"choices": [{"delta": {"content": text,
             "reasoning_content": reasoning}, "finish_reason": reason}]}, ensure_ascii=False) + "\r\n\r\n").encode()


@contextmanager
def sse_server(chunks: list[bytes], *, status: int = 200,
               gate: threading.Event | None = None, redirect: str = "",
               chunked: bool = False, disconnect: bool = False,
               truncate: bool = False) -> Iterator[tuple[str, list[dict]]]:
    requests: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: object) -> None:
            pass

        def do_POST(self) -> None:
            requests.append({"authorization": self.headers.get("Authorization"),
                             "payload": json.loads(self.rfile.read(int(self.headers["Content-Length"])))})
            if disconnect:
                self.close_connection = True
                return
            self.send_response(status)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.close_connection = True
            if chunked:
                self.send_header("Transfer-Encoding", "chunked")
            if redirect:
                self.send_header("Location", redirect)
            self.end_headers()
            try:
                for chunk in chunks:
                    self.wfile.write((f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n") if chunked else chunk)
                    self.wfile.flush()
                if gate is not None:
                    gate.wait(5)
                    self.wfile.write(event("迟到", reason="stop") + b"data: [DONE]\n\n")
                    self.wfile.flush()
                if chunked and not truncate:
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # The user's system proxy must never mediate deterministic localhost
        # fixtures (some proxies strip HTTP/1.0 Transfer-Encoding headers).
        with patch.dict(os.environ, {"no_proxy": "127.0.0.1,localhost", "NO_PROXY": "127.0.0.1,localhost"}):
            yield f"http://127.0.0.1:{server.server_port}/chat/completions", requests
    finally:
        if gate is not None:
            gate.set()
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_split_utf8_events_finish_and_thinking_disabled() -> None:
    wire = b": heartbeat\r\n\r\n" + event(reasoning="private-thought") + event("小鬼") + event("。", reason="stop") + b"data: [DONE]\n\n"
    # HTTP chunk framing forces read1 to split *every* UTF-8 code point/event;
    # TCP coalescing cannot accidentally turn this into a whole-event test.
    with sse_server([wire[i:i+1] for i in range(len(wire))], chunked=True) as (endpoint, requests):
        events = list(DeepSeekProvider(endpoint=endpoint).stream(
            [{"role": "user", "content": "你好"}], "unit-stream", threading.Event()))
    assert "".join(item.text for item in events if item.kind == "delta") == "小鬼。"
    assert events[-1].kind == "complete"
    assert "private-thought" not in repr(events)
    assert len(requests) == 1
    assert requests[0]["payload"] == {"model": "deepseek-flash", "thinking": {"type": "disabled"},
                                     "stream": True, "messages": [{"role": "user", "content": "你好"}]}
    assert requests[0]["authorization"] == "Bearer unit-stream"


@pytest.mark.parametrize("wire,kind", [
    (event("部分"), "interrupted"),
    (event("部分", reason="stop"), "interrupted"),
    (event("部分") + b"data: [DONE]\n\n", "interrupted"),
    (event("部分", reason="length") + b"data: [DONE]\n\n", "length"),
    (event(reason="stop") + b"data: [DONE]\n\n", "empty"),
    (event(reasoning="hidden", reason="stop") + b"data: [DONE]\n\n", "empty"),
    (b"data: invalid\n\n", "format"),
])
def test_abnormal_stream_preserves_deltas_and_never_calls_eof_success(wire: bytes, kind: str) -> None:
    deltas: list[str] = []
    with sse_server([wire]) as (endpoint, requests):
        with pytest.raises(ChatError) as failure:
            for item in DeepSeekProvider(endpoint=endpoint).stream([], "unit-key", threading.Event()):
                assert item.kind != "complete"
                deltas.append(item.text)
    assert failure.value.kind == kind and len(requests) == 1
    if "部分" in wire.decode():
        assert "".join(deltas) == "部分"


@pytest.mark.parametrize("status,kind", [(401, "invalid_key"), (403, "invalid_key"), (402, "balance"),
                                        (429, "rate_limit"), (503, "busy"), (500, "busy"), (400, "request")])
def test_http_errors_are_distinct_sanitized_and_never_retried(status: int, kind: str) -> None:
    with sse_server([b"private-key-echo"], status=status) as (endpoint, requests):
        with pytest.raises(ChatError) as failure:
            list(DeepSeekProvider(endpoint=endpoint).stream([], "private-key-echo", threading.Event()))
    assert failure.value.kind == kind and len(requests) == 1
    assert "private-key-echo" not in str(failure.value)


def test_socket_timeout_is_distinct_and_request_is_not_retried() -> None:
    gate = threading.Event()
    with sse_server([], gate=gate) as (endpoint, requests):
        with pytest.raises(ChatError) as failure:
            list(DeepSeekProvider(endpoint=endpoint, socket_timeout=.15).stream([], "unit-key", threading.Event()))
    assert failure.value.kind == "timeout" and len(requests) == 1


def test_redirect_does_not_forward_authorization() -> None:
    with sse_server([]) as (other, other_requests):
        with sse_server([], status=307, redirect=other) as (endpoint, requests):
            with pytest.raises(ChatError):
                list(DeepSeekProvider(endpoint=endpoint).stream([], "unit-key", threading.Event()))
    assert len(requests) == 1 and not other_requests


def test_disconnected_endpoint_is_network_error_without_retry() -> None:
    with sse_server([], disconnect=True) as (endpoint, requests):
        with pytest.raises(ChatError) as failure:
            list(DeepSeekProvider(endpoint=endpoint).stream([], "unit-key", threading.Event()))
    assert failure.value.kind == "network" and len(requests) == 1


@pytest.mark.parametrize("key", ["unit-key\nheader", "unit key", "非ASCII密钥"])
def test_malformed_key_is_actionable_without_sending_or_echoing(key: str) -> None:
    with sse_server([]) as (endpoint, requests):
        with pytest.raises(ChatError) as failure:
            list(DeepSeekProvider(endpoint=endpoint).stream([], key, threading.Event()))
    assert failure.value.kind == "invalid_key" and not requests
    assert key not in str(failure.value)


def test_broken_http_chunk_framing_after_headers_is_stream_interruption() -> None:
    deltas: list[str] = []
    with sse_server([event("已收到的正文")], chunked=True, truncate=True) as (endpoint, requests):
        with pytest.raises(ChatError) as failure:
            for item in DeepSeekProvider(endpoint=endpoint).stream([], "unit-key", threading.Event()):
                deltas.append(item.text)
    assert "".join(deltas) == "已收到的正文"
    assert failure.value.kind == "interrupted" and len(requests) == 1
