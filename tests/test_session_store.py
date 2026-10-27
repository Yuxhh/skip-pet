"""Versioned conversation storage through its agreed public boundary."""

from pathlib import Path
import json
import os
import threading
from dataclasses import asdict

import pytest

from sukuna_pet.chat_session import AuthorPrompt, ChatSession
from sukuna_pet.session_store import SessionStore


def test_full_history_and_author_snapshot_survive_restart(tmp_path: Path) -> None:
    session = ChatSession(prompt=AuthorPrompt("old-v1", "旧正文", "旧补充"))
    for index in range(45):
        session.add_message("user", f"问题 {index}" + "长" * 1000, request_id=f"request-{index}")
    session.add_message("assistant", "部分正文", state="incomplete", request_id="last-request")
    store = SessionStore(tmp_path)
    try:
        assert store.save(session)
        assert store.flush()
        restored = SessionStore(tmp_path).load_all()
        assert len(restored) == 1
        assert restored[0] == session
        assert restored[0].request_messages("追问")[0]["content"] == "旧正文\n\n旧补充"
        assert len(restored[0].messages) == 46
    finally:
        store.close()


def test_failed_atomic_replace_keeps_last_version_and_can_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = ChatSession()
    session.add_message("user", "已保存")
    store = SessionStore(tmp_path)
    try:
        store.save(session)
        assert store.flush()
        session.add_message("assistant", "仍在内存", state="incomplete")
        with monkeypatch.context() as patch:
            patch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(PermissionError()))
            store.save(session)
            assert not store.flush()
            assert store.failed and store.unsaved and not store.is_saved(session.id)
            assert len(SessionStore(tmp_path).load_all()[0].messages) == 1
            assert store.load_all()[0].messages[-1].content == "仍在内存"
        store.retry_failed()
        assert store.flush() and not store.unsaved
        assert SessionStore(tmp_path).load_all()[0].messages[-1].content == "仍在内存"
        assert not list(tmp_path.glob("*.tmp"))
    finally:
        store.close()


def test_delete_follows_inflight_write_and_rejects_late_snapshots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    entered, release = threading.Event(), threading.Event()
    replace = os.replace

    def delayed_replace(source, destination):
        entered.set()
        assert release.wait(3)
        replace(source, destination)

    session, other = ChatSession(), ChatSession()
    store = SessionStore(tmp_path)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "replace", delayed_replace)
            store.save(session)
            assert entered.wait(2)
            session.add_message("user", "不能复活")
            store.save(session)
            assert store.delete(session.id)
            assert not store.save(session)
            store.save(other)
            assert not store.flush(.01) and store.pending
            assert [s.id for s in store.load_all()] == [other.id]
            release.set()
            assert store.flush()
        assert [s.id for s in SessionStore(tmp_path).load_all()] == [other.id]
        assert not store.save(session)
    finally:
        release.set()
        store.close()


def test_backup_failure_leaves_original_and_other_sessions_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = b"not json"
    bad = tmp_path / ("f" * 32 + ".json")
    bad.write_bytes(original)
    good = ChatSession()
    store = SessionStore(tmp_path)
    store.save(good)
    assert store.flush()
    store.close()
    path_open = Path.open

    def no_backup(path, *args, **kwargs):
        if ".corrupt-" in path.name:
            raise PermissionError()
        return path_open(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", no_backup)
        restored = SessionStore(tmp_path)
        assert [s.id for s in restored.load_all()] == [good.id]
        assert "备份失败" in restored.problems[0]
    assert bad.read_bytes() == original


def test_record_directory_unreadable_is_reported(tmp_path: Path) -> None:
    root = tmp_path / "not-a-directory"
    root.write_text("保留")
    store = SessionStore(root)
    assert store.load_all() == []
    assert "无法读取" in store.problems[0]
    store.save(ChatSession())
    assert not store.flush() and store.failed
    store.close()


@pytest.mark.parametrize("kind", ["json", "schema", "fields", "duplicate-message", "wrong-id"])
def test_bad_record_is_reported_and_preserved_without_overwriting(
    tmp_path: Path, kind: str,
) -> None:
    session = ChatSession()
    session.add_message("user", "唯一消息")
    record = {"schema_version": 1, **asdict(session)}
    if kind == "schema":
        record["schema_version"] = 999
    elif kind == "fields":
        record["prompt"] = {"version": "v1"}
    elif kind == "duplicate-message":
        record["messages"] *= 2
    elif kind == "wrong-id":
        record["id"] = "../elsewhere"
    original = b"{broken" if kind == "json" else json.dumps(record).encode()
    path = tmp_path / f"{session.id}.json"
    path.write_bytes(original)
    store = SessionStore(tmp_path)
    assert store.load_all() == []
    assert store.problems
    assert path.read_bytes() == original
    assert not store.save(session)
    backups = list(tmp_path.glob("*.corrupt-*"))
    if kind == "schema":
        assert "版本" in store.problems[0] and not backups
    else:
        assert len(backups) == 1 and backups[0].read_bytes() == original


def test_abnormal_exit_recovers_generating_body_as_incomplete(tmp_path: Path) -> None:
    session = ChatSession()
    session.add_message("user", "原问题", request_id="request-1")
    reply = session.add_message("assistant", "已经收到", state="generating", request_id="request-1")
    store = SessionStore(tmp_path)
    try:
        store.save(session)
        assert store.flush()
        restored = SessionStore(tmp_path).load_all()[0]
        assert restored.messages[-1].id == reply.id
        assert restored.messages[-1].state == "incomplete"
        assert restored.messages[-1].content == "已经收到"
        assert json.loads((tmp_path / f"{session.id}.json").read_text("utf-8"))["schema_version"] == 1
    finally:
        store.close()
