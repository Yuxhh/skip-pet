"""Conversation operations; provider callbacks never touch the pet task state."""

import threading
from uuid import uuid4

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from .chat_provider import ChatError, DeepSeekProvider, ERROR_MESSAGES, ErrorKind, StreamEvent
from .chat_session import ChatMessage, ChatSession
from .credentials import CredentialStore


class ChatController(QObject):
    changed = Signal()
    _arrived = Signal(str, str, object)

    retry_notice = "重试会替换未完成回复，可能再次消耗 API 额度。"

    def __init__(self, credentials: CredentialStore, parent: QObject | None = None, *,
                 provider: DeepSeekProvider | None = None, generation_timeout_ms: int = 180000) -> None:
        super().__init__(parent)
        self.credentials = credentials
        self.session = ChatSession()
        self._provider = provider or DeepSeekProvider()
        self._workers: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._request_id = ""
        self._reply: ChatMessage | None = None
        self.notice = ""
        self.error_kind: ErrorKind | None = None
        self._arrived.connect(self._accept, Qt.ConnectionType.QueuedConnection)
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.setInterval(generation_timeout_ms)
        self._timeout.timeout.connect(self._timed_out)

    @property
    def busy(self) -> bool:
        return bool(self._request_id)

    @property
    def running_workers(self) -> int:
        return sum(thread.is_alive() for thread, _ in self._workers.values())

    @property
    def needs_settings(self) -> bool:
        return self.error_kind in ("missing_key", "invalid_key")

    @property
    def can_retry(self) -> bool:
        messages = self.session.messages
        return (not self.busy and len(messages) >= 2 and messages[-1].role == "assistant"
                and messages[-1].state == "incomplete" and messages[-2].role == "user")

    def _credential_for_request(self) -> str:
        key = self.credentials.snapshot()
        if not key:
            self._error("missing_key")
            return ""
        self._workers = {rid: entry for rid, entry in self._workers.items() if entry[0].is_alive()}
        if len(self._workers) >= 4:
            self._error("cleanup")
            return ""
        return key

    def send(self, text: str) -> bool:
        if self.busy or not text.strip():
            return False
        key = self._credential_for_request()
        if not key:
            return False
        text = text.strip()
        messages = self.session.request_messages(text)
        self.session.add_message("user", text)
        self._start(messages, key)
        return True

    def retry(self) -> bool:
        if not self.can_retry:
            return False
        key = self._credential_for_request()
        if not key:
            return False
        messages = self.session.request_messages(self.session.messages[-2].content,
                                                 history_end=len(self.session.messages) - 2)
        self.session.messages.pop()
        self._start(messages, key)
        return True

    def _start(self, messages: list[dict[str, str]], key: str) -> None:
        request_id = uuid4().hex
        self._request_id = request_id
        self._reply = self.session.add_message("assistant", "", state="generating", request_id=request_id)
        self.notice = "正在生成…"
        self.error_kind = None
        cancel = threading.Event()
        # The worker owns transport cleanup. Qt never waits on a socket or
        # destroys a running QThread; each worker is a Python daemon thread.
        self.destroyed.connect(cancel.set)
        worker = threading.Thread(target=self._run, args=(self.session.id, request_id, messages, key, cancel),
                                  name="sukuna-chat", daemon=True)
        self._workers[request_id] = worker, cancel
        self._timeout.start()
        worker.start()
        self.changed.emit()

    def stop(self) -> None:
        if not self.busy:
            return
        self._workers[self._request_id][1].set()
        self._timeout.stop()
        self._request_id = ""  # Invalidate before any queued delta/completion.
        if self._reply is not None:
            self._reply.state = "incomplete"
        self._reply = None
        self.error_kind = None
        self.notice = "已停止，回复未完成；停止不保证服务端立即停止计算或计费。"
        self.changed.emit()

    def _timed_out(self) -> None:
        self.stop()
        self._error("timeout")

    def _error(self, kind: ErrorKind) -> None:
        self.error_kind = kind
        self.notice = ERROR_MESSAGES[kind]
        self.changed.emit()

    def _run(self, session_id: str, request_id: str, messages: list[dict[str, str]],
             key: str, cancel: threading.Event) -> None:
        try:
            for event in self._provider.stream(messages, key, cancel):
                if cancel.is_set():
                    return
                self._arrived.emit(session_id, request_id, event)
        except ChatError as error:
            self._deliver_error(session_id, request_id, error)
        except Exception:
            self._deliver_error(session_id, request_id, ChatError("interrupted"))
        finally:
            key = ""
            messages.clear()

    def _deliver_error(self, session_id: str, request_id: str, error: ChatError) -> None:
        try:
            self._arrived.emit(session_id, request_id, error)
        except RuntimeError:
            pass  # Qt owner was already destroyed; daemon cleanup still runs.

    def _accept(self, session_id: str, request_id: str, event: StreamEvent | ChatError) -> None:
        if session_id != self.session.id or request_id != self._request_id or self._reply is None:
            return
        if isinstance(event, StreamEvent) and event.kind == "delta":
            self._reply.content += event.text
            self.changed.emit()
            return
        self._timeout.stop()
        self._reply.state = "incomplete" if isinstance(event, ChatError) else "complete"
        self._reply = None
        self._request_id = ""
        if isinstance(event, ChatError):
            self._error(event.kind)
        else:
            self.notice = ""
            self.changed.emit()
