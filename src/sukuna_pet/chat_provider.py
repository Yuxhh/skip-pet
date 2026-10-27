"""Single-request SSE transport. Errors are fixed messages, never provider echoes."""

from collections.abc import Iterator
from dataclasses import dataclass
from http.client import HTTPException
import json
import re
import ssl
import threading
from time import monotonic
from typing import Literal
import urllib.error
import urllib.request

from .connection_test import ENDPOINT, MODEL


ErrorKind = Literal["missing_key", "invalid_key", "balance", "rate_limit", "busy", "network",
                    "timeout", "empty", "interrupted", "format", "length", "request", "cleanup"]
ERROR_MESSAGES: dict[ErrorKind, str] = {
    "missing_key": "请先在 AI 对话设置中配置 DeepSeek API Key，再手动发送。",
    "invalid_key": "Key 无效或无访问权限，请更新 AI 对话设置中的 Key，再手动发送。",
    "balance": "DeepSeek 余额不足，请补充余额后手动重试。",
    "rate_limit": "请求限流，请稍后手动重试。",
    "busy": "DeepSeek 服务繁忙，请稍后手动重试。",
    "network": "网络连接失败，请检查网络后手动重试。",
    "timeout": "回复超时，已收到的正文保留为未完成；请手动重试。",
    "empty": "接口没有返回正文，请手动重试。",
    "interrupted": "回复流中断，已收到的正文保留为未完成；请手动重试。",
    "format": "接口响应格式异常，请手动重试。",
    "length": "回复达到长度上限，已标记未完成；可以追问或手动重试。",
    "request": "接口拒绝请求，请核对接口参数或上下文长度后手动重试。",
    "cleanup": "旧请求仍在清理，请稍后手动发送。",
}


class ChatError(Exception):
    def __init__(self, kind: ErrorKind) -> None:
        self.kind = kind
        super().__init__(ERROR_MESSAGES[kind])


@dataclass(frozen=True)
class StreamEvent:
    kind: Literal["delta", "complete"]
    text: str = ""


class _SSE:
    def __init__(self) -> None:
        self.buffer = b""
        self.done = False
        self.finish_reason: str | None = None

    def feed(self, chunk: bytes) -> Iterator[str]:
        self.buffer += chunk
        if len(self.buffer) > 1024 * 1024:
            raise ChatError("format")
        while not self.done:
            separator = re.search(rb"\r?\n\r?\n", self.buffer)
            if separator is None:
                break
            event, self.buffer = self.buffer[:separator.start()], self.buffer[separator.end():]
            data = b"\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith(b"data:"))
            if not data.strip():
                continue
            if data.strip() == b"[DONE]":
                self.done = True
                break
            payload = json.loads(data.decode("utf-8"))
            if not isinstance(payload, dict) or payload.get("error"):
                raise ChatError("interrupted")
            choices = payload.get("choices", [])
            if not choices:  # Optional usage-only events.
                continue
            choice = choices[0]
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if content is not None and not isinstance(content, str):
                raise ChatError("format")
            reason = choice.get("finish_reason")
            if reason is not None:
                if not isinstance(reason, str):
                    raise ChatError("format")
                self.finish_reason = reason
            if content:
                yield content


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: object, code: int,
                         msg: str, headers: object, newurl: str) -> None:
        return None


class DeepSeekProvider:
    def __init__(self, *, endpoint: str = ENDPOINT, socket_timeout: float = 10,
                 request_budget: float = 180) -> None:
        self.endpoint = endpoint
        self.socket_timeout = socket_timeout
        self.request_budget = request_budget

    def stream(self, messages: list[dict[str, str]], key: str,
               cancel: threading.Event) -> Iterator[StreamEvent]:
        if not key:
            raise ChatError("missing_key")
        if any(not 33 <= ord(character) <= 126 for character in key):
            raise ChatError("invalid_key")
        if cancel.is_set():
            return
        response_started = False
        try:
            payload = {"model": MODEL, "thinking": {"type": "disabled"}, "stream": True,
                       "messages": messages}
            request = urllib.request.Request(
                self.endpoint, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), method="POST",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "Accept": "text/event-stream"},
            )
            opener = urllib.request.build_opener(
                _NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            )
            deadline = monotonic() + self.request_budget
            parser = _SSE()
            content_size = 0
            has_text = False
            with opener.open(request, timeout=self.socket_timeout) as response:
                response_started = True
                while not cancel.is_set():
                    if monotonic() > deadline:
                        raise ChatError("timeout")
                    chunk = response.read1(4096)
                    if cancel.is_set():
                        return
                    if not chunk:
                        raise ChatError("interrupted")
                    for text in parser.feed(chunk):
                        content_size += len(text)
                        has_text = has_text or bool(text.strip())
                        if content_size > 1024 * 1024:
                            raise ChatError("length")
                        yield StreamEvent("delta", text)
                    if parser.done:
                        if parser.finish_reason == "length":
                            raise ChatError("length")
                        if parser.finish_reason != "stop":
                            raise ChatError("interrupted")
                        if not has_text:
                            raise ChatError("empty")
                        yield StreamEvent("complete")
                        return
        except urllib.error.HTTPError as error:
            status = error.code
            error.close()
            kinds: dict[int, ErrorKind] = {401: "invalid_key", 403: "invalid_key", 402: "balance",
                                          429: "rate_limit", 500: "busy", 502: "busy", 503: "busy", 504: "busy"}
            raise ChatError(kinds.get(status, "request")) from None
        except TimeoutError:
            raise ChatError("timeout") from None
        except urllib.error.URLError as error:
            raise ChatError("timeout" if isinstance(error.reason, TimeoutError) else "network") from None
        except (OSError, HTTPException):
            raise ChatError("interrupted" if response_started else "network") from None
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ChatError("format") from None
        finally:
            key = ""
