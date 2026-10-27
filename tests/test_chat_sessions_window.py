"""Real sidebar and close decisions at the agreed native window boundary."""

from pathlib import Path
from dataclasses import asdict
import json
import os
import threading

import pytest
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from sukuna_pet.chat_controller import ChatController
from sukuna_pet.chat_session import ChatSession
from sukuna_pet.chat_window import ChatWindow
from sukuna_pet.session_store import SessionStore
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from test_chat_controller import configured, wait_for


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def answer_dialog(button_text: str, seen: list[str]) -> None:
    def answer() -> None:
        dialog = QApplication.activeModalWidget()
        if not isinstance(dialog, QMessageBox):
            QTimer.singleShot(10, answer)
            return
        seen.append(dialog.text())
        button = next(b for b in dialog.buttons() if button_text in b.text())
        button.click()
    QTimer.singleShot(10, answer)


def test_sidebar_restores_real_records_and_delete_requires_confirmation(
    app: QApplication, tmp_path: Path,
) -> None:
    store = SessionStore(tmp_path)
    first = ChatSession()
    first.add_message("user", "第一段 <b>标题</b>")
    store.save(first)
    assert store.flush()
    controller = ChatController(configured(), store=store)
    chat = ChatWindow(controller)
    chat.show()
    seen: list[str] = []
    try:
        assert chat.session_list.count() == 1
        assert "第一段 <b>标题</b>" in chat.session_list.item(0).text()
        chat.new_session_button.click()
        second = controller.session.id
        assert second != first.id and chat.session_list.count() == 2
        row = next(i for i in range(2) if chat.session_list.item(i).data(Qt.ItemDataRole.UserRole) == first.id)
        chat.session_list.setCurrentRow(row)
        assert controller.session.id == first.id
        assert "第一段 <b>标题</b>" in chat.transcript.toPlainText()
        answer_dialog("取消", seen)
        chat.delete_session_button.click()
        assert len(controller.sessions) == 2
        answer_dialog("删除", seen)
        chat.delete_session_button.click()
        assert controller.session.id == second and chat.session_list.count() == 1
        assert len(seen) == 2 and "本机" in seen[1]
        assert store.flush()
        assert [s.id for s in SessionStore(tmp_path).load_all()] == [second]
    finally:
        store.flush()
        chat.close()
        chat.deleteLater()
        controller.deleteLater()
        store.close()


def test_pet_exit_waits_for_chat_and_cancel_keeps_pet_and_credentials(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pet = PetWindow(PetApplication(), credentials=configured(), chat_data_dir=tmp_path)
    pet.show()
    pet.open_chat()
    chat = pet.findChild(ChatWindow)
    assert chat is not None
    store = chat.controller.store
    assert store is not None and store.flush()
    seen: list[str] = []
    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(PermissionError()))
            chat.controller.session.add_message("user", "退出也要确认")
            chat.controller.save_all()
            assert not store.flush()
            assert not pet.close()
            answer_dialog("取消关闭", seen)
            wait_for(lambda: bool(seen))
            assert pet.isVisible() and chat.isVisible()
            assert pet.credentials.snapshot() == "unit-controller"
        chat.controller.save_all()
        assert store.flush()
        assert pet.close()
        assert not pet.isVisible()
        restored_pet = PetWindow(PetApplication(), credentials=configured(), chat_data_dir=tmp_path)
        try:
            restored_pet.open_chat()
            restored = restored_pet.findChild(ChatWindow)
            assert restored is not None
            assert restored.controller.session.messages[-1].content == "退出也要确认"
            assert restored.controller.store.flush()
        finally:
            restored_pet.close()
            restored_pet.deleteLater()
    finally:
        pet.close()
        pet.deleteLater()
        store.close()


@pytest.mark.parametrize("choice", ["取消关闭", "确认关闭", "重试保存"])
def test_failed_save_close_offers_three_choices_and_preserves_last_disk_version(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, choice: str,
) -> None:
    store = SessionStore(tmp_path)
    controller = ChatController(configured(), store=store)
    chat = ChatWindow(controller)
    chat.show()
    assert store.flush()
    replace = os.replace
    failure = [True]

    def replace_or_fail(source, destination):
        if failure[0]:
            raise PermissionError()
        replace(source, destination)

    seen: list[str] = []
    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "replace", replace_or_fail)
            controller.session.add_message("user", "仍然可见且不能丢弃")
            controller.save_all()
            assert not store.flush()
            wait_for(lambda: "尚未保存" in chat.status.text())
            assert not chat.close()
            assert chat.isVisible()
            if choice == "重试保存":
                failure[0] = False
            answer_dialog(choice, seen)
            wait_for(lambda: bool(seen))
            assert "可能丢失" in seen[0]
            if choice == "取消关闭":
                assert chat.isVisible()
                assert "仍然可见且不能丢弃" in chat.transcript.toPlainText()
                assert controller.unsaved
            else:
                wait_for(lambda: not chat.isVisible())
            recovered = SessionStore(tmp_path).load_all()[0]
            assert bool(recovered.messages) == (choice == "重试保存")
    finally:
        failure[0] = False
        controller.save_all()
        store.flush()
        chat.close()
        chat.deleteLater()
        controller.deleteLater()
        store.close()


def test_slow_disk_keeps_gui_responsive_and_pet_exit_waits_for_snapshot(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pet = PetWindow(PetApplication(), credentials=configured(), chat_data_dir=tmp_path)
    pet.show()
    pet.open_chat()
    chat = pet.findChild(ChatWindow)
    assert chat is not None
    store = chat.controller.store
    assert store is not None and store.flush()
    entered, release = threading.Event(), threading.Event()
    replace = os.replace

    def slow_replace(source, destination):
        entered.set()
        assert release.wait(4)
        replace(source, destination)

    ticks: list[int] = []
    heartbeat = QTimer()
    heartbeat.setInterval(10)
    heartbeat.timeout.connect(lambda: ticks.append(1))
    heartbeat.start()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "replace", slow_replace)
            chat.controller.session.add_message("user", "延迟写入正文")
            chat.controller.save_all()
            assert entered.wait(2)
            assert not pet.close() and pet.isVisible()
            QTest.qWait(100)
            assert len(ticks) >= 3 and chat.isVisible() and store.unsaved
            release.set()
            wait_for(lambda: not pet.isVisible())
        assert SessionStore(tmp_path).load_all()[0].messages[-1].content == "延迟写入正文"
    finally:
        release.set()
        heartbeat.stop()
        store.flush()
        pet.close()
        pet.deleteLater()
        store.close()


@pytest.mark.parametrize("kind", ["unknown", "corrupt", "backup-failed"])
def test_invalid_record_is_reported_in_window_and_not_replaced(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str,
) -> None:
    session = ChatSession()
    path = tmp_path / f"{session.id}.json"
    original = json.dumps({"schema_version": 999, **asdict(session)}).encode() if kind == "unknown" else b"{bad"
    path.write_bytes(original)
    path_open = Path.open

    def fail_backup(file, *args, **kwargs):
        if ".corrupt-" in file.name:
            raise PermissionError()
        return path_open(file, *args, **kwargs)

    if kind == "backup-failed":
        monkeypatch.setattr(Path, "open", fail_backup)
    store = SessionStore(tmp_path)
    controller = ChatController(configured(), store=store)
    chat = ChatWindow(controller)
    chat.show()
    try:
        expected = {"unknown": "版本不受支持", "corrupt": "已损坏", "backup-failed": "备份失败"}[kind]
        assert expected in chat.status.text()
        assert controller.session.id != session.id
        assert chat.session_list.count() == 1
        assert store.flush()
        assert path.read_bytes() == original
    finally:
        chat.close()
        chat.deleteLater()
        controller.deleteLater()
        store.close()


def test_delete_disk_failure_is_visible_and_retry_does_not_restore_sidebar_row(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SessionStore(tmp_path)
    controller = ChatController(configured(), store=store)
    doomed = controller.session.id
    survivor = controller.new_session()
    controller.select_session(doomed)
    chat = ChatWindow(controller)
    chat.show()
    assert store.flush()
    unlink = Path.unlink
    seen: list[str] = []

    def fail_delete(path, *args, **kwargs):
        if path.name == f"{doomed}.json":
            raise PermissionError()
        return unlink(path, *args, **kwargs)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(Path, "unlink", fail_delete)
            answer_dialog("删除", seen)
            chat.delete_session_button.click()
            wait_for(lambda: store.failed)
            wait_for(lambda: chat.save_retry_button.isVisible())
            assert "尚未保存" in chat.status.text()
            assert controller.session.id == survivor and chat.session_list.count() == 1
            assert (tmp_path / f"{doomed}.json").exists()
        chat.save_retry_button.click()
        wait_for(lambda: not store.unsaved)
        assert [s.id for s in SessionStore(tmp_path).load_all()] == [survivor]
    finally:
        store.retry_failed()
        store.flush()
        chat.close()
        chat.deleteLater()
        controller.deleteLater()
        store.close()


def test_unreadable_record_directory_is_visible_and_original_is_preserved(
    app: QApplication, tmp_path: Path,
) -> None:
    root = tmp_path / "blocked-directory"
    root.write_text("原内容不可覆盖", encoding="utf-8")
    store = SessionStore(root)
    controller = ChatController(configured(), store=store)
    chat = ChatWindow(controller)
    chat.show()
    try:
        wait_for(lambda: store.failed)
        wait_for(lambda: chat.save_retry_button.isVisible())
        assert "无法读取本机聊天记录目录" in chat.status.text()
        assert "尚未保存" in chat.status.text()
        assert root.read_text("utf-8") == "原内容不可覆盖"
    finally:
        chat.hide()
        chat.deleteLater()
        controller.deleteLater()
        store.close()
