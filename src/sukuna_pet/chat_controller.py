"""Conversation operations; provider callbacks never touch the pet task state."""

import threading
from uuid import uuid4

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from .chat_provider import ChatError, DeepSeekProvider, ERROR_MESSAGES, ErrorKind, StreamEvent
from .chat_session import AUTHOR_PROMPT, AuthorPrompt, ChatMessage, ChatSession, utc_now
from .credentials import CredentialStore
from .session_store import SessionStore


class ChatController(QObject):
    changed = Signal()
    _arrived = Signal(str, str, object)

    retry_notice = "重试会替换未完成回复，可能再次消耗 API 额度。"

    def __init__(self, credentials: CredentialStore, parent: QObject | None = None, *,
                 provider: DeepSeekProvider | None = None, generation_timeout_ms: int = 180000,
                 store: SessionStore | None = None, author_prompt: AuthorPrompt = AUTHOR_PROMPT) -> None:
        super().__init__(parent)
        self.credentials = credentials
        self.store = store
        self._author_prompt = author_prompt
        self.sessions = store.load_all() if store is not None else []
        self.session = self.sessions[0] if self.sessions else ChatSession(prompt=author_prompt)
        if not self.sessions:
            self.sessions.append(self.session)
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
        self._storage_timer = QTimer(self)
        self._storage_timer.setInterval(50)
        self._storage_timer.timeout.connect(self._storage_changed)
        self._last_storage_notice = ""
        if store is not None:
            self.save_all()
            self._storage_timer.start()
            self.destroyed.connect(lambda: store.close(timeout=0))

    @property
    def unsaved(self) -> bool:
        return self.store is not None and self.store.unsaved

    @property
    def storage_notice(self) -> str:
        if self.store is None:
            return ""
        notices = list(self.store.problems)
        if self.store.unsaved:
            notices.append("尚未保存：写盘失败，请重试保存。" if self.store.failed else "尚未保存：正在写入本机记录…")
        return "\n".join(notices)

    def _storage_changed(self) -> None:
        notice = self.storage_notice
        if notice != self._last_storage_notice:
            self._last_storage_notice = notice
            self.changed.emit()

    def _persist(self) -> None:
        self.session.updated_at = utc_now()
        if self.store is not None:
            self.store.save(self.session)

    def save_all(self) -> None:
        if self.store is not None:
            for session in self.sessions:
                self.store.save(session)
            self.store.retry_failed()
        self.changed.emit()

    def new_session(self) -> str:
        self.stop()
        self.session = ChatSession(prompt=self._author_prompt)
        self.sessions.insert(0, self.session)
        self.notice = ""
        self.error_kind = None
        self._persist()
        self.changed.emit()
        return self.session.id

    def select_session(self, session_id: str) -> bool:
        selected = next((s for s in self.sessions if s.id == session_id), None)
        if selected is None:
            return False
        if selected is self.session:
            return True
        self.stop()
        self.session = selected
        self.notice = ""
        self.error_kind = None
        self._persist()
        self.changed.emit()
        return True

    def delete_session(self, session_id: str) -> bool:
        selected = next((s for s in self.sessions if s.id == session_id), None)
        if selected is None:
            return False
        if selected is self.session:
            self.stop()
        if self.store is not None and not self.store.delete(session_id):
            return False
        self.sessions.remove(selected)
        if selected is self.session:
            if self.sessions:
                self.session = self.sessions[0]
                self._persist()
            else:
                self.new_session()
            self.notice = ""
            self.error_kind = None
        self.changed.emit()
        return True

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
        self.session.messages[-1].request_id = request_id
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
        self._persist()
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
        self._persist()
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
            self._persist()
            self.changed.emit()
            return
        self._timeout.stop()
        self._reply.state = "incomplete" if isinstance(event, ChatError) else "complete"
        self._reply = None
        self._request_id = ""
        self._persist()
        if isinstance(event, ChatError):
            self._error(event.kind)
        else:
            self.notice = ""
            self.changed.emit()
