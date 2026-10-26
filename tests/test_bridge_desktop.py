"""Agreed Qt menu boundary with real pnpm and an isolated desktop profile."""

import json
from pathlib import Path
import time
import subprocess
import threading
import hashlib
import os
from collections.abc import Callable

import pytest
from PySide6.QtCore import QEvent, QPoint, QTimer, QLockFile
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

import sukuna_pet.desktop as desktop
from sukuna_pet.bridge_install import BridgeInstaller
from sukuna_pet.desktop import PetWindow
from test_bridge_install import profile_at
from sukuna_pet.settings import save_bridge


def publish_running(directory: Path, health: int) -> None:
    # Include the negotiated identity/health contract as well as the legacy
    # schema field, so this UI test also runs against the issue-38 baseline.
    identity = dict(schema=1, schema_version=1, owner="@sukuna-pet/dsh-bridge",
                    user_id=hashlib.sha256(os.path.normcase(str(Path.home().resolve())).encode()).hexdigest(),
                    profile_id="test-profile", instance_id="test-instance", pid=1,
                    process_start_id="1000", boot_id="test-boot", boot_started_at=1000,
                    host_version="test-host", plugin_version="test-plugin",
                    capabilities=["observed-state", "snapshot-boundary", "contiguous-events", "independent-health"],
                    health_seq=health, lifecycle="active")
    snapshot = dict(identity, coverage="observed", scope="tracked-agents", revision=0,
                    snapshot_seq=health, agents=[dict(agent_id="root", root_id="root",
                    root_turn=1, turn_id=1, known=True, status="running")])
    (directory / "dsh-1.jsonl").touch(exist_ok=True)
    for suffix, value in (("snapshot", snapshot), ("health", identity)):
        temporary = directory / f"{suffix}.tmp"
        temporary.write_text(json.dumps(value), encoding="utf-8")
        try:
            temporary.replace(directory / f"dsh-1.{suffix}.json")
        except PermissionError:
            # Windows can briefly deny replacement while a reader holds it.
            # The next periodic publication supplies the fresh sample.
            return


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def choose(window: PetWindow, text: str, monkeypatch: pytest.MonkeyPatch) -> None:
    class Menu(QMenu):
        def exec(self, point: QPoint) -> None:
            next(action for action in self.actions() if action.text() == text).trigger()

    monkeypatch.setattr(desktop, "QMenu", Menu)
    point = window.rect().center()
    QApplication.sendEvent(window, QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, point, window.mapToGlobal(point),
    ))


def wait_until(predicate: Callable[[], object], timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "background operation timed out"
        QTest.qWait(20)
        time.sleep(.01)  # Let Python workers run even where Qt's wait holds the GIL.


def test_declined_menu_install_preserves_profile_and_settings(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = profile_at(tmp_path / "dsh")
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "dsh"))
    before = (profile / "package.json").read_bytes()
    prompts: list[str] = []

    def decline(parent: object, title: str, text: str, *args: object) -> QMessageBox.StandardButton:
        prompts.append(text)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", decline)
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    window = PetWindow(settings_path=tmp_path / "mode.json", bridge_installer=installer)
    try:
        choose(window, "启用 DeepSeek 接入", monkeypatch)
        wait_until(lambda: prompts)
        assert str(profile) in prompts[0]
        assert (profile / "package.json").read_bytes() == before
        assert not (tmp_path / "mode.json").exists()
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_background_install_keeps_frames_responsive_and_failed_install_can_retry(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = profile_at(tmp_path / "dsh")
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "dsh"))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    notices: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: notices.append(text))
    monkeypatch.setattr(QMessageBox, "information", lambda parent, title, text: notices.append(text))
    started, release = threading.Event(), threading.Event()

    def slow_failure(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        started.set()
        release.wait(10)
        return subprocess.CompletedProcess(command, 1, "ERR_TEST_INSTALL", "")

    real_run = subprocess.run
    monkeypatch.setattr(subprocess, "run", slow_failure)
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    settings = tmp_path / "mode.json"
    window = PetWindow(settings_path=settings, bridge_installer=installer)
    try:
        window.show()
        choose(window, "启用 DeepSeek 接入", monkeypatch)
        wait_until(started.is_set)
        choose(window, "持续跳动", monkeypatch)
        before = window.frame
        QTest.qWait(120)
        assert window.frame != before
        assert not json.loads(settings.read_text()).get("dsh_bridge", {}).get("enabled", False)
        release.set()
        wait_until(lambda: notices)
        assert "ERR_TEST_INSTALL" in notices[-1]
        assert not installer.inspect(profile).registered
        monkeypatch.setattr(subprocess, "run", real_run)
        choose(window, "启用 DeepSeek 接入", monkeypatch)
        wait_until(lambda: json.loads(settings.read_text()).get("dsh_bridge", {}).get("enabled"))
        assert json.loads(settings.read_text())["mode"] == "always"
    finally:
        release.set()
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_saved_integration_refreshes_old_link_on_start_and_exit_keeps_plugin(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import shutil

    profile = profile_at(tmp_path / "dsh")
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    assert installer.install(installer.preflight((profile,))).ok
    moved = tmp_path / "updated package" / "dsh-bridge"
    shutil.copytree(installer.plugin, moved)
    upgraded = BridgeInstaller(data_dir=tmp_path / "data", plugin=moved)
    settings = tmp_path / "mode.json"
    save_bridge(settings, True, (profile,))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)
    window = PetWindow(settings_path=settings, bridge_installer=upgraded)
    try:
        window.show()
        wait_until(lambda: upgraded.inspect(profile).target == moved.resolve())
        QTest.qWait(80)
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert upgraded.inspect(profile).registered
    assert json.loads(settings.read_text())["dsh_bridge"]["enabled"]


def test_menu_install_monitors_in_click_mode_and_disable_removes_plugin(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = profile_at(tmp_path / "dsh")
    bridge = tmp_path / "events"
    bridge.mkdir()
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "dsh"))
    monkeypatch.setenv("SUKUNA_PET_BRIDGE_DIR", str(bridge))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    notices: list[str] = []
    monkeypatch.setattr(QMessageBox, "information", lambda parent, title, text: notices.append(text))
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: notices.append(text))
    settings = tmp_path / "mode.json"
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    window = PetWindow(settings_path=settings, bridge_installer=installer)
    publisher = QTimer()
    health = iter(range(1, 1000))
    publisher.timeout.connect(lambda: publish_running(bridge, next(health)))
    try:
        window.show()
        choose(window, "启用 DeepSeek 接入", monkeypatch)
        wait_until(lambda: settings.exists() and json.loads(settings.read_text()).get("dsh_bridge", {}).get("enabled"))
        assert installer.inspect(profile).registered
        publisher.start(100)
        wait_until(lambda: window._bubble.isVisible())
        assert "还在办" in window._bubble.text()
        choose(window, "持续跳动", monkeypatch)
        assert json.loads(settings.read_text())["dsh_bridge"]["enabled"] is True
        choose(window, "点击跳动", monkeypatch)
        assert window._bubble.isVisible()
        choose(window, "关闭 DeepSeek 接入", monkeypatch)
        wait_until(lambda: not installer.inspect(profile).registered)
        assert json.loads(settings.read_text())["dsh_bridge"]["enabled"] is False
        assert not window._bubble.isVisible()
    finally:
        publisher.stop()
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_startup_retries_maintenance_lock_then_registers_shared_use_and_monitors(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = profile_at(tmp_path / "dsh")
    events = tmp_path / "events"
    events.mkdir()
    monkeypatch.setenv("SUKUNA_PET_BRIDGE_DIR", str(events))
    installer = BridgeInstaller(data_dir=tmp_path / "data")
    assert installer.install(installer.preflight((profile,))).ok
    settings = tmp_path / "mode.json"
    save_bridge(settings, True, (profile,))
    other = QLockFile(str(installer.data_dir / "maintenance.lock"))
    assert other.tryLock(0)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    window = PetWindow(settings_path=settings, bridge_installer=installer)
    publisher = QTimer()
    health = iter(range(1, 1000))
    publisher.timeout.connect(lambda: publish_running(events, next(health)))
    try:
        window.show()
        publisher.start(100)
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            QTest.qWait(20)
            time.sleep(.01)
        other.unlock()
        wait_until(lambda: window._bubble.isVisible())
        result = installer.remove((profile,))
        assert result.ok and "其他实例" in result.message
        assert installer.inspect(profile).registered
    finally:
        other.unlock()
        publisher.stop()
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
