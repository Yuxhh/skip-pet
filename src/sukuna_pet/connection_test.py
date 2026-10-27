"""One explicit, non-streaming DeepSeek probe; never stores keys or responses."""

from collections.abc import Callable
from dataclasses import dataclass
import json
from http.client import HTTPException
import ssl
import threading
from time import monotonic
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, Signal, QTimer


ENDPOINT = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"


@dataclass(frozen=True)
class ConnectionResult:
    ok: bool
    message: str


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: object, code: int,
                         msg: str, headers: object, newurl: str) -> None:
        # Never forward the Authorization header to a different endpoint.
        return None


def test_connection(key: str) -> ConnectionResult:
    if not key:
        return ConnectionResult(False, "请先输入或保存 DeepSeek API Key。")
    payload = {"model": MODEL, "thinking": {"type": "disabled"}, "stream": False,
               "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 8}
    try:
        request = urllib.request.Request(
            ENDPOINT, data=json.dumps(payload).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        opener = urllib.request.build_opener(
            _NoRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        )
        deadline = monotonic() + 20
        with opener.open(request, timeout=10) as response:
            body = bytearray()
            while True:
                if monotonic() > deadline:
                    return ConnectionResult(False, "连接测试超时，请手动重试。")
                chunk = response.read1(4096)
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > 65536:
                    return ConnectionResult(False, "连接测试响应过大，请稍后重试。")
        data = json.loads(body)
        choice = data["choices"][0]
        content = choice["message"]["content"]
        if not isinstance(content, str) or not content.strip() or choice.get("finish_reason") not in ("stop", "length"):
            return ConnectionResult(False, "接口未返回有效短回复，请手动重试。")
        return ConnectionResult(True, "本次连接测试成功；不代表持续在线，未保存 Key 或聊天记录。")
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
        message = {400: "请求参数被拒绝，请核对接口契约。", 401: "Key 无效，请更新 Key。",
                   403: "Key 无访问权限，请更新 Key。", 402: "余额不足，请检查 DeepSeek 余额。",
                   429: "请求限流，请稍后手动重试。", 500: "服务异常，请稍后手动重试。",
                   503: "服务繁忙，请稍后手动重试。"}.get(status, "接口请求失败，请稍后手动重试。")
        return ConnectionResult(False, message)
    except (OSError, urllib.error.URLError, HTTPException):
        return ConnectionResult(False, "网络、证书或超时错误，请检查连接后手动重试。")
    except (ValueError, KeyError, IndexError, TypeError):
        return ConnectionResult(False, "接口响应格式异常，请稍后手动重试。")


class ConnectionTester(QObject):
    """Request identity rejects late callbacks; daemon workers outlive closed UI."""

    completed = Signal(object)
    changed = Signal()
    _arrived = Signal(int, object)

    def __init__(self, parent: QObject, probe: Callable[[str], ConnectionResult] = test_connection) -> None:
        super().__init__(parent)
        self._probe = probe
        self._generation = 0
        self.busy = False
        self._arrived.connect(self._accept)
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.setInterval(30000)
        self._timeout.timeout.connect(self._timed_out)

    def start(self, key: str) -> None:
        if self.busy:
            return
        self._generation += 1
        self.busy = True
        self._timeout.start()
        self.changed.emit()
        threading.Thread(target=self._run, args=(self._generation, key),
                         name="sukuna-connection-test", daemon=True).start()

    def invalidate(self) -> None:
        self._timeout.stop()
        self._generation += 1
        self.busy = False
        self.changed.emit()

    def _timed_out(self) -> None:
        self.invalidate()
        self.completed.emit(ConnectionResult(False, "连接测试超时，请手动重试。"))

    def _run(self, generation: int, key: str) -> None:
        try:
            result = self._probe(key)
        except Exception:
            result = ConnectionResult(False, "连接测试失败，请手动重试。")
        finally:
            key = ""
        try:
            self._arrived.emit(generation, result)
        except RuntimeError:
            pass  # Application/Qt owner has already been destroyed.

    def _accept(self, generation: int, result: ConnectionResult) -> None:
        if generation != self._generation:
            return
        self._timeout.stop()
        self.busy = False
        self.changed.emit()
        self.completed.emit(result)
