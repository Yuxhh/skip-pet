"""Mode/size menus and elapsed frames at the agreed public Qt boundary."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

import sukuna_pet.desktop as desktop
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from test_v5_desktop import assert_frame_matches_region


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def choose(
    window: PetWindow, text: str, monkeypatch: pytest.MonkeyPatch,
    expected_mode: str = "点击跳动",
) -> None:
    class Menu(QMenu):
        def exec(self, point: QPoint) -> None:
            actions = self.actions()
            checked_modes = [a.text() for a in actions if a.isChecked()]
            assert checked_modes == [expected_mode]
            submenu = next(a.menu() for a in actions if a.text() == "调整大小")
            assert submenu is not None
            sizes = submenu.actions()
            assert [a.text() for a in sizes] == ["188px", "271px", "320px"]
            assert [a.text() for a in sizes if a.isChecked()] == [f"{window.height()}px"]
            next(a for a in actions + sizes if a.text() == text).trigger()

    monkeypatch.setattr(desktop, "QMenu", Menu)
    point = window.visible_region.boundingRect().center()
    QApplication.sendEvent(window, QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, point, window.mapToGlobal(point),
    ))


def test_real_frame_cap_and_wait_match_native_frame_accounting(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(desktop, "perf_counter", lambda: clock[0])
    pet = PetApplication()
    control = PetApplication()
    window = PetWindow(pet)
    try:
        window.show()
        app.processEvents()
        choose(window, "持续跳动", monkeypatch)
        control.select_mode("always")
        # Every injected clock change is one real frame, even after a stall.
        # QTest only pumps Qt's real timer; no private timer entry is called.
        for milliseconds in (500, 70, 150, 150, 150, 16, 33, 500):
            clock[0] += milliseconds / 1000
            control.advance(min(150, milliseconds))
            QTest.qWait(20)
            assert pet.view.stage == control.view.stage
            assert pet.view.head_phase == pytest.approx(control.view.head_phase, abs=1e-8)
            assert pet.view.bounce_scale == pytest.approx(control.view.bounce_scale, abs=1e-8)
            assert_frame_matches_region(window)
        choose(window, "点击跳动", monkeypatch, "持续跳动")
        stage = pet.view.stage
        for _ in range(10):
            clock[0] += .15
            QTest.qWait(15)
        assert pet.view.stage == stage and pet.view.holding
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("height", [188, 271, 320])
def test_menu_modes_and_sizes_restore_together(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, height: int,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    path = tmp_path / "preferences.json"
    first = PetWindow(settings_path=path)
    try:
        choose(first, f"{height}px", monkeypatch)
        choose(first, "持续跳动", monkeypatch)
        second = PetWindow(settings_path=path)
        try:
            assert second.height() == height
            choose(second, "点击跳动", monkeypatch, "持续跳动")
            choose(second, "188px", monkeypatch)
            third = PetWindow(settings_path=path)
            try:
                assert third.height() == 188
                choose(third, "点击跳动", monkeypatch)
            finally:
                third.close()
                third.deleteLater()
        finally:
            second.close()
            second.deleteLater()
    finally:
        first.close()
        first.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_failed_menu_saves_warn_and_keep_both_previous_choices(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    path = tmp_path / "preferences.json"
    path.mkdir()
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: warnings.append(title))
    window = PetWindow(settings_path=path)
    try:
        before = window.frame
        choose(window, "持续跳动", monkeypatch)
        choose(window, "188px", monkeypatch)
        assert window.height() == 320 and window.frame == before
        choose(window, "点击跳动", monkeypatch)
        assert warnings == ["无法保存模式", "无法保存大小"]
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
