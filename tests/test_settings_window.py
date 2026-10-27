"""Settings/menu interaction, credential drafts and lifecycle via native Qt."""

import json
from pathlib import Path
import time
import subprocess
import threading

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

import sukuna_pet.connection_test as connection
from sukuna_pet.credentials import CredentialStore
from sukuna_pet.desktop import PetWindow
from sukuna_pet.settings import load_mode, load_size, save_bridge
from sukuna_pet.bridge_install import BridgeInstaller
from sukuna_pet.settings_window import SettingsWindow, product_version
from test_credentials import CredentialVault
from test_connection_test import server
from test_modes_desktop import choose
from test_bridge_install import profile_at
from test_bridge_desktop import wait_until


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def pet(app: QApplication, tmp_path: Path) -> tuple[PetWindow, CredentialVault, Path]:
    path = tmp_path / "mode.json"
    path.write_text(json.dumps({"mode": "click", "size": 320, "future": {"keep": True}}))
    vault = CredentialVault()
    window = PetWindow(settings_path=path, credentials=CredentialStore(vault))
    window.show()
    try:
        yield window, vault, path
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def opened(window: PetWindow, page: str = "桌宠") -> SettingsWindow:
    window.open_settings(page)
    settings = window.findChild(SettingsWindow)
    assert settings is not None and settings.isVisible()
    return settings


def test_settings_and_shortcuts_share_persisted_mode_and_size(
    pet: tuple[PetWindow, CredentialVault, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, vault, path = pet
    choose(window, "桌宠设置", monkeypatch)
    settings = opened(window)
    assert settings.navigation.count() == 4
    for index, (mode, height) in enumerate((("click", 188), ("always", 271), ("task", 320))):
        settings.mode.setCurrentIndex(index)
        settings.size_choice.setCurrentIndex(index)
        assert window.pet_mode == mode and window.height() == height
        assert load_mode(path) == mode and load_size(path) == height
    choose(window, "点击跳动", monkeypatch, "任务联动")
    choose(window, "188px", monkeypatch)
    assert settings.mode.currentData() == "click" and settings.size_choice.currentData() == 188
    assert json.loads(path.read_text())["future"] == {"keep": True}
    assert not vault.value
    settings.close()
    assert window.isVisible() and not settings.isVisible()
    assert opened(window) is settings
    assert len(window.findChildren(SettingsWindow)) == 1


def test_key_save_cancel_blank_close_and_escape_do_not_leak_drafts(
    pet: tuple[PetWindow, CredentialVault, Path],
) -> None:
    window, vault, path = pet
    settings = opened(window, "AI 对话")
    settings.key_input.setText("unit-discard")
    settings.cancel_key.click()
    assert not settings.key_input.text() and not vault.value
    settings.key_input.setText("unit-saved")
    settings.save_key.click()
    assert not settings.key_input.text() and window.credentials.snapshot() == "unit-saved"
    assert "已安全保存" in settings.key_status.text()
    settings.key_input.setText(" ")
    settings.save_key.click()
    assert window.credentials.snapshot() == "unit-saved"
    settings.key_input.setText("unit-unsaved")
    QTest.keyClick(settings, Qt.Key.Key_Escape)
    assert not settings.isVisible() and not settings.key_input.text() and window.isVisible()
    assert opened(window, "AI 对话") is settings
    settings.key_input.setText("unit-close-draft")
    settings.close()
    assert not settings.key_input.text() and vault.value == "unit-saved"
    assert "unit-" not in path.read_text()


def test_clear_drops_saved_and_unsaved_key_and_reports_delete_failure(
    pet: tuple[PetWindow, CredentialVault, Path],
) -> None:
    window, vault, path = pet
    settings = opened(window, "AI 对话")
    settings.key_input.setText("unit-old")
    settings.save_key.click()
    settings.key_input.setText("unit-new-draft")
    vault.fail_delete = True
    settings.clear_key.click()
    settings.key_input.undo()
    assert not window.credentials.snapshot() and not settings.key_input.text()
    assert "未安全保存" in settings.key_status.text() and "删除失败" in settings.key_notice.text()
    assert "unit-old" not in settings.key_notice.text()
    settings.save_key.click()  # Blank cannot reload a key after deletion failure.
    assert not window.credentials.snapshot()
    vault.fail_delete = False
    settings.clear_key.click()
    assert not vault.value and "已清除" in settings.key_notice.text()
    assert "unit-" not in path.read_text()


def test_memory_fallback_is_visible_and_never_written_to_preferences(
    pet: tuple[PetWindow, CredentialVault, Path],
) -> None:
    window, vault, path = pet
    settings = opened(window, "AI 对话")
    vault.fail_write = True
    settings.key_input.setText("unit-runtime")
    settings.save_key.click()
    assert window.credentials.snapshot() == "unit-runtime" and not vault.value
    assert "未安全保存" in settings.key_status.text() and "重启" in settings.key_notice.text()
    assert "unit-runtime" not in path.read_text()


def wait_result(settings: SettingsWindow) -> None:
    deadline = time.monotonic() + 5
    while "本次连接测试成功" not in settings.test_result.text():
        assert time.monotonic() < deadline
        QTest.qWait(15)
        time.sleep(.01)


def test_explicit_probe_uses_draft_then_current_key_without_saving(
    pet: tuple[PetWindow, CredentialVault, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, vault, path = pet
    settings = opened(window, "AI 对话")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    with server() as (endpoint, requests):
        monkeypatch.setattr(connection, "ENDPOINT", endpoint)
        settings.key_input.setText("unit-current")
        settings.save_key.click()
        assert not requests
        settings.key_input.setText("unit-draft")
        settings.test_key.click()
        wait_result(settings)
        assert requests[-1]["authorization"] == "Bearer unit-draft"
        assert vault.value == "unit-current" and window.credentials.snapshot() == "unit-current"
        settings.cancel_key.click()
        settings.test_key.click()
        wait_result(settings)
        assert requests[-1]["authorization"] == "Bearer unit-current" and len(requests) == 2
        settings.close()
        opened(window, "AI 对话")
        assert not settings.test_result.text()
        assert "unit-" not in path.read_text()


def test_declining_billable_probe_sends_nothing(
    pet: tuple[PetWindow, CredentialVault, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, vault, path = pet
    settings = opened(window, "AI 对话")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    with server() as (endpoint, requests):
        monkeypatch.setattr(connection, "ENDPOINT", endpoint)
        settings.key_input.setText("unit-declined")
        settings.test_key.click()
        QTest.qWait(50)
    assert not requests and not vault.value
    assert "unit-" not in path.read_text()


def test_close_clears_draft_and_late_network_response_does_not_change_reopened_window(
    pet: tuple[PetWindow, CredentialVault, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, vault, path = pet
    settings = opened(window, "AI 对话")
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    release = threading.Event()
    try:
        with server(gate=release) as (endpoint, requests):
            monkeypatch.setattr(connection, "ENDPOINT", endpoint)
            settings.key_input.setText("unit-late")
            settings.test_key.click()
            wait_until(lambda: requests)
            assert not settings.test_key.isEnabled()
            settings.close()
            assert not settings.key_input.text() and window.isVisible()
            assert opened(window, "AI 对话") is settings
            release.set()
            QTest.qWait(100)
            time.sleep(.05)
            QTest.qWait(50)
            assert not settings.test_result.text() and settings.test_key.isEnabled()
            assert len(requests) == 1 and not vault.value
    finally:
        release.set()


def test_failed_preference_save_restores_both_controls(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "directory"
    path.mkdir()
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: QMessageBox.StandardButton.Ok)
    window = PetWindow(settings_path=path, credentials=CredentialStore(CredentialVault()))
    try:
        settings = opened(window)
        settings.mode.setCurrentIndex(1)
        settings.size_choice.setCurrentIndex(0)
        assert settings.mode.currentData() == "click" and settings.size_choice.currentData() == 320
        assert window.pet_mode == "click" and window.height() == 320
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_about_matches_project_version() -> None:
    assert product_version() == "0.3.0"


def test_bridge_preferences_preserve_unknown_fields(tmp_path: Path) -> None:
    path = tmp_path / "mode.json"
    path.write_text(json.dumps({"mode": "task", "size": 271, "future": 7,
                                "dsh_bridge": {"enabled": True, "future_bridge": 8}}))
    save_bridge(path, False, (tmp_path / "desktop",))
    saved = json.loads(path.read_text())
    assert saved["future"] == 7 and saved["dsh_bridge"]["future_bridge"] == 8
    assert saved["mode"] == "task" and saved["size"] == 271
    assert not saved["dsh_bridge"]["enabled"]


def test_settings_bridge_uses_existing_preflight_confirm_busy_and_failure_flow(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = profile_at(tmp_path / "dsh")
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "dsh"))
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    path = tmp_path / "mode.json"
    window = PetWindow(settings_path=path, bridge_installer=installer,
                       credentials=CredentialStore(CredentialVault()))
    prompts: list[str] = []
    notices: list[str] = []

    def confirm(parent: object, title: str, text: str, *args: object) -> QMessageBox.StandardButton:
        prompts.append(text)
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", confirm)
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: notices.append(text))
    # pnpm is the external process boundary, with real preflight/profile handling.
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(
        command, 1, "ERR_SETTINGS_INSTALL", ""))
    try:
        settings = opened(window, "任务联动")
        settings.bridge_toggle.click()
        assert not settings.bridge_toggle.isEnabled() and not settings.bridge_maintain.isEnabled()
        wait_until(lambda: notices)
        settings.refresh()
        assert prompts and str(profile) in prompts[0]
        assert "ERR_SETTINGS_INSTALL" in notices[-1]
        assert settings.bridge_toggle.isEnabled() and not settings.bridge_maintain.isEnabled()
        assert "未启用" in settings.bridge_status.text()
        assert not installer.inspect(profile).registered
        assert not path.exists()
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
