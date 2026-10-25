"""Dynamic edge contact through the approved Qt input/frame/geometry seam."""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import sukuna_pet.desktop as desktop
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from test_desktop import pet_window, pointer
from test_resize import choose_size
from test_v5_desktop import assert_frame_matches_region


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def drag_to(window: PetWindow, horizontal: str | None, vertical: str | None) -> None:
    area = window.screen().availableGeometry()
    start = window.mapToGlobal(window.visible_region.boundingRect().center())
    end = QPoint(start)
    if horizontal is not None:
        end.setX(area.left() - window.width() if horizontal == "left"
                 else area.right() + window.width())
    if vertical is not None:
        end.setY(area.top() - window.height() if vertical == "top"
                 else area.bottom() + window.height())
    pointer(window, QEvent.Type.MouseButtonPress, start)
    pointer(window, QEvent.Type.MouseMove, end)
    pointer(window, QEvent.Type.MouseButtonRelease, end)


def assert_contact(window: PetWindow, horizontal: str | None, vertical: str | None) -> None:
    area = window.screen().availableGeometry()
    visible = window.visible_region.boundingRect().translated(window.pos())
    assert area.contains(visible)
    if horizontal is not None:
        assert getattr(visible, horizontal)() == getattr(area, horizontal)()
    if vertical is not None:
        assert getattr(visible, vertical)() == getattr(area, vertical)()


EDGES = [(None, "top"), (None, "bottom"), ("left", None), ("right", None),
         ("left", "top"), ("left", "bottom"), ("right", "top"), ("right", "bottom"),
         (None, None)]


@pytest.mark.parametrize("height", [188, 271, 320])
@pytest.mark.parametrize("horizontal,vertical", EDGES)
def test_contact_follows_continuous_frames_bounce_and_all_four_endpoints(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, height: int,
    horizontal: str | None, vertical: str | None,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    pet = PetApplication()
    with pet_window(app, pet) as window:
        window.show()
        app.processEvents()
        choose_size(window, height, monkeypatch)
        area = window.screen().availableGeometry()
        window.move(area.center() - window.rect().center())
        if horizontal or vertical:
            drag_to(window, horizontal, vertical)
        origin = window.pos()
        previous_frame = window.frame
        for stage in (1, 2, 3, 0):
            point = window.mapToGlobal(window.visible_region.boundingRect().center())
            pointer(window, QEvent.Type.MouseButtonPress, point)
            pointer(window, QEvent.Type.MouseButtonRelease, point)
            for elapsed in (22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 780):
                pet.advance(elapsed)
                QTest.qWait(15)
                assert_contact(window, horizontal, vertical)
                if horizontal is None:
                    assert window.x() == origin.x()
                if vertical is None:
                    assert window.y() == origin.y()
            assert window.frame != previous_frame
            previous_frame = window.frame
            assert pet.view.stage == stage and pet.view.holding
            assert_frame_matches_region(window)
        if horizontal or vertical:
            assert not area.contains(window.geometry())


def test_compensation_during_a_held_gesture_preserves_the_drag_anchor(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    pet, control = PetApplication(), PetApplication()
    with pet_window(app, pet) as window:
        window.show()
        app.processEvents()
        drag_to(window, None, "top")
        point = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, point)
        pointer(window, QEvent.Type.MouseButtonRelease, point)
        control.click()
        pet.advance(55)
        control.advance(55)
        QTest.qWait(15)
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        pet.advance(55)
        control.advance(55)
        QTest.qWait(15)
        compensated = window.pos()
        delta = QPoint(QApplication.startDragDistance() + 20, 0)
        pointer(window, QEvent.Type.MouseMove, start + delta)
        assert window.pos() == compensated + delta
        assert_contact(window, None, "top")
        pet.advance(55)
        control.advance(55)
        QTest.qWait(15)
        compensated = window.pos()
        pointer(window, QEvent.Type.MouseButtonRelease, start + delta)
        assert window.pos() == compensated
        assert pet.view == control.view


@pytest.mark.parametrize("axis", ["horizontal", "vertical", "both"])
def test_leaving_one_edge_releases_only_that_axis(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, axis: str,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    pet = PetApplication()
    with pet_window(app, pet) as window:
        window.show()
        app.processEvents()
        drag_to(window, "left", "top")
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        delta = QPoint(90 if axis != "vertical" else 0, 90 if axis != "horizontal" else 0)
        pointer(window, QEvent.Type.MouseButtonPress, start)
        pointer(window, QEvent.Type.MouseButtonRelease, start + delta)
        origin = window.pos()
        point = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, point)
        pointer(window, QEvent.Type.MouseButtonRelease, point)
        for elapsed in (110, 110, 780):
            pet.advance(elapsed)
            QTest.qWait(15)
            assert_contact(window, "left" if axis == "vertical" else None,
                           "top" if axis == "horizontal" else None)
            if axis != "vertical":
                assert window.x() == origin.x()
            if axis != "horizontal":
                assert window.y() == origin.y()


@pytest.mark.parametrize("horizontal,vertical", EDGES[:-1])
def test_edge_resize_rebuilds_current_frame_and_does_not_persist_contact(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    horizontal: str | None, vertical: str | None,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    path = tmp_path / "preferences.json"
    pet = PetApplication()
    window = PetWindow(pet, settings_path=path)
    try:
        window.show()
        app.processEvents()
        drag_to(window, horizontal, vertical)
        pet.click()
        pet.advance(110)
        QTest.qWait(15)
        peak = pet.view
        for height in (188, 271, 320, 271, 188):
            choose_size(window, height, monkeypatch)
            assert window.height() == height
            assert pet.view == peak
            assert_contact(window, horizontal, vertical)
            assert_frame_matches_region(window)
        # A new instance restores only the saved size and the default placement.
        second = PetWindow(settings_path=path)
        try:
            assert second.height() == 188
            area = second.screen().availableGeometry()
            visible = second.visible_region.boundingRect().translated(second.pos())
            assert area.contains(visible)
            assert visible.left() > area.left() and visible.right() < area.right()
            assert visible.top() > area.top() and visible.bottom() < area.bottom()
        finally:
            second.close()
            second.deleteLater()
        assert json.loads(path.read_text()) == {"size": 188}
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("interruption", [QEvent.Type.UngrabMouse, QEvent.Type.Hide])
def test_edge_compensation_does_not_turn_interrupted_gestures_into_clicks(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, interruption: QEvent.Type,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    pet, control = PetApplication(), PetApplication()
    with pet_window(app, pet) as window:
        window.show()
        app.processEvents()
        drag_to(window, "right", "top")
        pet.click()
        control.click()
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        pet.advance(110)
        control.advance(110)
        QTest.qWait(15)
        assert_contact(window, "right", "top")
        QApplication.sendEvent(window, QEvent(interruption))
        pointer(window, QEvent.Type.MouseButtonRelease, start)
        assert pet.view == control.view
