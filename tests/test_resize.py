"""Resize through the context menu and observe geometry and fresh launches."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox

import sukuna_pet.desktop as desktop
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.settings import load_size, save_mode, save_size


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def choose_size(window: PetWindow, height: int, monkeypatch: pytest.MonkeyPatch) -> None:
    def execute(menu: QMenu, point: QPoint) -> None:
        submenu = next(action.menu() for action in menu.actions() if action.text() == "调整大小")
        assert submenu is not None
        actions = submenu.actions()
        assert [action.text() for action in actions] == ["188px", "271px", "320px"]
        assert [action.text() for action in actions if action.isChecked()] == [f"{window.height()}px"]
        next(action for action in actions if action.text() == f"{height}px").trigger()

    # Shiboken binds QMenu.exec on instances, so replace the adapter's menu
    # constructor rather than monkeypatching the native class attribute.
    class Menu(QMenu):
        def exec(self, point: QPoint) -> None:
            execute(self, point)

    monkeypatch.setattr(desktop, "QMenu", Menu)
    QApplication.sendEvent(window, QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, QPoint(100, 100), window.pos() + QPoint(100, 100),
    ))


@pytest.mark.parametrize("height,width", [(188, 193), (271, 278), (320, 328)])
def test_menu_resize_preserves_playback_hit_region_and_work_area(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, height: int, width: int,
) -> None:
    pet = PetApplication()
    window = PetWindow(pet)
    try:
        app.processEvents()
        area = window.screen().availableGeometry()
        window.move(area.right() - window.width(), area.bottom() - window.height())
        pet.click()
        pet.advance(1000)
        before = pet.view
        choose_size(window, height, monkeypatch)
        assert (window.width(), window.height()) == (width, height)
        assert pet.view == before
        assert pet.mode == "click"
        assert area.contains(window.visible_region.boundingRect().translated(window.pos()))
        assert not window.visible_region.contains(QPoint(0, 0))
        assert window.visible_region.contains(QPoint(width // 2, height // 2))
        # V5 reserves a fixed motion viewport, including transparent padding.
        assert window.rect().contains(window.visible_region.boundingRect())
        assert 0 < window.visible_region.boundingRect().height() < height
        # Reopening the menu reflects the new selection, including shrinking.
        choose_size(window, 188, monkeypatch)
        assert window.height() == 188
        # A normal click still advances after the mask and size change.
        point = window.pos() + QPoint(window.width() // 2, window.height() // 2)
        for kind, buttons in ((QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton),
                              (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton)):
            QApplication.sendEvent(window, QMouseEvent(
                kind, QPointF(point - window.pos()), QPointF(point),
                Qt.MouseButton.LeftButton, buttons, Qt.KeyboardModifier.NoModifier,
            ))
        pet.advance(1000)
        assert pet.view.stage == 2
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_size_and_mode_restore_without_overwriting_each_other(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "config" / "mode.json"
    save_mode(path, "always")  # Old preferences have no size field.
    first = PetWindow(settings_path=path)
    try:
        assert first.height() == 320
        choose_size(first, 188, monkeypatch)
        save_mode(path, "click")
        assert json.loads(path.read_text(encoding="utf-8")) == {"mode": "click", "size": 188}
        second = PetWindow(settings_path=path)
        try:
            assert second.height() == 188
            choose_size(second, 271, monkeypatch)
            assert json.loads(path.read_text(encoding="utf-8")) == {"mode": "click", "size": 271}
        finally:
            second.close()
            second.deleteLater()
    finally:
        first.close()
        first.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("saved", ["not json", "[]", '{"size":true}', '{"size":461.0}',
                                   '{"size":999}', '{"mode":"always"}'])
def test_invalid_or_old_size_uses_default(tmp_path: Path, saved: str) -> None:
    path = tmp_path / "mode.json"
    path.write_text(saved, encoding="utf-8")
    assert load_size(path) == 320


def test_failed_size_save_keeps_previous_geometry(
    app: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "mode.json"
    path.mkdir()
    warnings: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda parent, title, text: warnings.append(title))
    window = PetWindow(settings_path=path)
    try:
        before = window.geometry(), window.visible_region
        choose_size(window, 271, monkeypatch)
        assert (window.geometry(), window.visible_region) == before
        assert warnings == ["无法保存大小"]
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_unsupported_size_is_not_saved(tmp_path: Path) -> None:
    path = tmp_path / "mode.json"
    with pytest.raises(ValueError):
        save_size(path, 999)
    assert not path.exists()


@pytest.mark.parametrize("saved,expected", [(320, 320), (461, 271), (544, 320)])
def test_previous_sizes_restore_at_or_below_new_maximum(
    app: QApplication, tmp_path: Path, saved: int, expected: int,
) -> None:
    path = tmp_path / "mode.json"
    path.write_text(json.dumps({"mode": "always", "size": saved}), encoding="utf-8")
    window = PetWindow(settings_path=path)
    try:
        assert window.height() == expected
        assert window.height() <= 320
        assert json.loads(path.read_text(encoding="utf-8"))["mode"] == "always"
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
