"""Serial background snapshots and atomic local conversation records.

Mechanism reference: dsh-pet pet/chat/session_store.py at 34d810b1.
Only immutable bytes cross to the writer. Failed snapshots remain retryable;
deletion permanently rejects later saves for that ID within this store.
"""

from collections import OrderedDict
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading
import time
from uuid import uuid4

from .chat_session import AuthorPrompt, ChatMessage, ChatSession


def _valid_id(value: str) -> bool:
    return re.fullmatch(r"[0-9a-f]{32}", value) is not None


class _UnknownVersion(ValueError):
    pass


def _text(value: dict[str, object], key: str) -> str:
    text = value[key]
    if not isinstance(text, str):
        raise ValueError("Invalid text field")
    return text


def _timestamp(value: dict[str, object], key: str) -> str:
    text = _text(value, key)
    if datetime.fromisoformat(text).tzinfo is None:
        raise ValueError("Missing timezone")
    return text


def _decode(payload: bytes, session_id: str) -> ChatSession:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("Invalid record")
    if "schema_version" not in value:
        raise ValueError("Missing version")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise _UnknownVersion()
    if not _valid_id(session_id) or value["id"] != session_id:
        raise ValueError("Invalid session ID")
    prompt = value["prompt"]
    if not isinstance(prompt, dict) or not isinstance(value["messages"], list):
        raise ValueError("Invalid session")
    messages: list[ChatMessage] = []
    ids: set[str] = set()
    for item in value["messages"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid message")
        role, state = item["role"], item["state"]
        message_id = _text(item, "id")
        if (role not in ("user", "assistant") or state not in ("complete", "generating", "incomplete")
                or not _valid_id(message_id) or message_id in ids):
            raise ValueError("Invalid message fields")
        ids.add(message_id)
        messages.append(ChatMessage(
            role=role, content=_text(item, "content"),
            state="incomplete" if state == "generating" else state,
            request_id=_text(item, "request_id"), id=message_id,
            created_at=_timestamp(item, "created_at"),
        ))
    return ChatSession(
        prompt=AuthorPrompt(*(_text(prompt, key) for key in ("version", "body", "supplement"))),
        id=session_id, messages=messages, created_at=_timestamp(value, "created_at"),
        updated_at=_timestamp(value, "updated_at"),
    )


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.stem + ".", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class SessionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.problems: list[str] = []
        self._condition = threading.Condition()
        self._pending: OrderedDict[str, tuple[int, bytes | None]] = OrderedDict()
        self._dirty: dict[str, tuple[int, bytes | None]] = {}
        self._deleted: set[str] = set()
        self._protected: set[str] = set()
        self._errors: set[str] = set()
        self._revision = 0
        self._inflight = False
        self._closing = False
        self._thread: threading.Thread | None = None

    def load_all(self) -> list[ChatSession]:
        sessions: list[ChatSession] = []
        with self._condition:
            dirty = dict(self._dirty)
            deleted = set(self._deleted)
        try:
            paths = list(self.root.iterdir())
        except FileNotFoundError:
            paths = []
        except OSError:
            self.problems.append("无法读取本机聊天记录目录；原记录未修改。")
            paths = []
        for path in paths:
            if path.suffix != ".json" or path.stem in dirty or path.stem in deleted:
                continue
            try:
                sessions.append(_decode(path.read_bytes(), path.stem))
            except _UnknownVersion:
                self._protected.add(path.stem)
                self.problems.append(f"记录 {path.stem} 的版本不受支持，已保留原文件。")
            except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
                self._protected.add(path.stem)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                backup = path.with_name(f"{path.name}.corrupt-{stamp}-{uuid4().hex[:8]}")
                try:
                    with path.open("rb") as source, backup.open("xb") as target:
                        shutil.copyfileobj(source, target)
                        target.flush()
                        os.fsync(target.fileno())
                    self.problems.append(f"记录 {path.stem} 已损坏，已创建时间戳备份；原文件保留。")
                except OSError:
                    self.problems.append(f"记录 {path.stem} 已损坏且备份失败；原文件保留。")
            except OSError:
                self._protected.add(path.stem)
                self.problems.append(f"无法读取记录 {path.stem}；原文件保留。")
        for session_id, (_, payload) in dirty.items():
            if payload is not None:
                sessions.append(_decode(payload, session_id))
        return sorted(sessions, key=lambda session: session.updated_at, reverse=True)

    @property
    def unsaved(self) -> bool:
        with self._condition:
            return bool(self._dirty)

    @property
    def pending(self) -> bool:
        with self._condition:
            return bool(self._pending) or self._inflight

    @property
    def failed(self) -> bool:
        with self._condition:
            return bool(self._errors)

    def is_saved(self, session_id: str) -> bool:
        with self._condition:
            return session_id not in self._dirty

    def save(self, session: ChatSession) -> bool:
        if not _valid_id(session.id):
            return False
        payload = json.dumps({"schema_version": 1, **asdict(session)}, ensure_ascii=False).encode("utf-8")
        with self._condition:
            if session.id in self._deleted or session.id in self._protected:
                return False
            return self._submit(session.id, payload)

    def delete(self, session_id: str) -> bool:
        if not _valid_id(session_id):
            return False
        with self._condition:
            if session_id in self._protected or self._closing:
                return False
            self._deleted.add(session_id)
            return self._submit(session_id, None)

    def _submit(self, session_id: str, payload: bytes | None) -> bool:
        # Caller holds the condition; accepted operations share one writer.
        if self._closing:
            return False
        self._revision += 1
        self._dirty[session_id] = self._pending[session_id] = (self._revision, payload)
        self._errors.discard(session_id)
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, daemon=True, name="sukuna-records")
            self._thread.start()
        self._condition.notify_all()
        return True

    def retry_failed(self) -> None:
        with self._condition:
            if self._closing:
                return
            for session_id in tuple(self._errors):
                self._submit(session_id, self._dirty[session_id][1])

    def flush(self, timeout: float = 3.0) -> bool:
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._pending or self._inflight:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return not self._dirty

    def close(self, timeout: float = 3.0) -> bool:
        with self._condition:
            self._closing = True
            self._condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout)
        return not self.pending and not self.unsaved

    def _run(self) -> None:
        while True:
            with self._condition:
                while not self._pending and not self._closing:
                    self._condition.wait()
                if not self._pending:
                    return
                session_id, snapshot = self._pending.popitem(last=False)
                self._inflight = True
            ok = True
            try:
                path = self.root / (session_id + ".json")
                if snapshot[1] is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_write(path, snapshot[1])
            except OSError:
                ok = False
            with self._condition:
                if self._dirty.get(session_id) == snapshot:
                    if ok:
                        del self._dirty[session_id]
                    else:
                        self._errors.add(session_id)
                self._inflight = False
                self._condition.notify_all()
