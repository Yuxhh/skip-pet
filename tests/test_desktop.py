"""Agreed Qt window input/geometry seam; not physical multi-monitor evidence."""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@contextmanager
def pet_window(app: QApplication, pet: PetApplication) -> Iterator[PetWindow]:
    window = PetWindow(pet)
    try:
        yield window
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def pointer(window: PetWindow, kind: QEvent.Type, point: QPoint) -> None:
    button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
    buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
    QApplication.sendEvent(window, QMouseEvent(
        kind, QPointF(point - window.pos()), QPointF(point), button, buttons,
        Qt.KeyboardModifier.NoModifier,
    ))


def test_drag_and_release_keep_character_above_taskbar_without_advancing(app: QApplication) -> None:
    pet = PetApplication()
    with pet_window(app, pet) as window:
        area = window.screen().availableGeometry()
        window.move(area.topLeft() + QPoint(100, 100))
        pointer(window, QEvent.Type.MouseButtonPress, window.pos() + QPoint(120, 120))
        destination = QPoint(area.center().x(), area.bottom() + 200)
        pointer(window, QEvent.Type.MouseMove, destination)
        assert area.contains(window.visible_region.boundingRect().translated(window.pos()))
        pointer(window, QEvent.Type.MouseButtonRelease, destination)
        assert area.contains(window.visible_region.boundingRect().translated(window.pos()))
        pet.advance(1000)
        assert pet.view.stage == 0
        assert pet.view.holding


def test_work_area_change_recovers_a_character_left_outside(app: QApplication) -> None:
    with pet_window(app, PetApplication()) as window:
        app.processEvents()
        area = window.screen().availableGeometry()
        window.move(area.right(), area.bottom())
        # Same public system notification as taskbar/work-area reconfiguration.
        window.screen().availableGeometryChanged.emit(area)
        app.processEvents()
        assert area.contains(window.visible_region.boundingRect().translated(window.pos()))


@pytest.mark.parametrize("kind", [QEvent.Type.DevicePixelRatioChange, QEvent.Type.ScreenChangeInternal])
def test_native_screen_notification_rechecks_visible_geometry(
    app: QApplication, kind: QEvent.Type,
) -> None:
    with pet_window(app, PetApplication()) as window:
        app.processEvents()
        area = window.screen().availableGeometry()
        window.move(area.right(), area.bottom())
        QApplication.sendEvent(window, QEvent(kind))
        app.processEvents()
        assert area.contains(window.visible_region.boundingRect().translated(window.pos()))


class Screen(QObject):
    """OS-boundary geometry fixture, not an emulated or physical monitor."""

    availableGeometryChanged = Signal(QRect)
    geometryChanged = Signal(QRect)

    def __init__(self, geometry: QRect, work: QRect) -> None:
        super().__init__()
        self.rect = geometry
        self.work = work

    def geometry(self) -> QRect:
        return self.rect

    def availableGeometry(self) -> QRect:
        return self.work


@pytest.fixture
def layout(app: QApplication, monkeypatch: pytest.MonkeyPatch) -> list[Screen]:
    # Logical rectangles as exposed by Qt on Windows: screen origins remain in
    # native coordinates, sizes scale. Fixtures represent 100/150/200% layouts.
    screens = [
        Screen(QRect(0, 0, 1920, 1080), QRect(0, 0, 1920, 1032)),
        Screen(QRect(-2560, -240, 1707, 960), QRect(-2528, -240, 1675, 960)),
        Screen(QRect(1920, -1440, 1280, 720), QRect(1920, -1400, 1280, 680)),
    ]
    current = [screens[0]]
    monkeypatch.setattr(QApplication, "screens", lambda: screens)
    monkeypatch.setattr(QApplication, "primaryScreen", lambda: screens[0])
    monkeypatch.setattr(QApplication, "screenAt", lambda p: next(
        (s for s in screens if s.geometry().contains(p)), None))
    monkeypatch.setattr(PetWindow, "screen", lambda self: current[0])
    monkeypatch.setattr(PetWindow, "setScreen", lambda self, s: current.__setitem__(0, s))
    return screens


@pytest.mark.parametrize("cursor, horizontal, vertical, target", [
    (QPoint(-2560, -230), "left", "top", 1),
    (QPoint(-900, 700), "right", "bottom", 1),
    # A point in a logical gap uses the nearest individual screen.
    (QPoint(-500, 100), "right", None, 1),
    (QPoint(1930, -1400), "left", "top", 2),
    (QPoint(1910, 1070), "right", "bottom", 0),
])
def test_drag_across_logical_layout_keeps_visible_on_target_and_can_click_again(
    app: QApplication, layout: list[Screen], cursor: QPoint,
    horizontal: str, vertical: str | None, target: int,
) -> None:
    pet = PetApplication()
    with pet_window(app, pet) as window:
        app.processEvents()
        pointer(window, QEvent.Type.MouseButtonPress, window.pos() + QPoint(120, 120))
        pointer(window, QEvent.Type.MouseMove, cursor)
        dragged = window.pos()
        pointer(window, QEvent.Type.MouseButtonRelease, cursor)
        assert window.pos() == dragged
        area = layout[target].availableGeometry()
        visible = window.visible_region.boundingRect().translated(window.pos())
        assert area.contains(visible)
        assert (visible.left() == area.left() if horizontal == "left"
                else visible.right() == area.right())
        if vertical is not None:
            assert (visible.top() == area.top() if vertical == "top"
                    else visible.bottom() == area.bottom())
        else:
            assert window.y() == -20  # Unconstrained vertical drag in the gap.
        pet.advance(1000)
        assert pet.view.stage == 0
        click = window.pos() + QPoint(120, 120)
        pointer(window, QEvent.Type.MouseButtonPress, click)
        pointer(window, QEvent.Type.MouseButtonRelease, click)
        pet.advance(1000)
        assert pet.view.stage == 1
        assert pet.view.holding


@pytest.mark.parametrize("cursor, horizontal, vertical", [
    (QPoint(0, 0), "left", "top"),
    (QPoint(1919, 1079), "right", "bottom"),
])
def test_transparent_padding_can_extend_outside_work_area(
    app: QApplication, layout: list[Screen], cursor: QPoint, horizontal: str, vertical: str,
) -> None:
    with pet_window(app, PetApplication()) as window:
        # Use the actual character's transparent padding, not a visual clip.
        pointer(window, QEvent.Type.MouseButtonPress, window.pos() + QPoint(120, 120))
        # Release without an intervening move still needs to apply constraints.
        pointer(window, QEvent.Type.MouseButtonRelease, cursor)
        visible = window.visible_region.boundingRect().translated(window.pos())
        area = layout[0].availableGeometry()
        assert getattr(visible, horizontal)() == getattr(area, horizontal)()
        assert getattr(visible, vertical)() == getattr(area, vertical)()
        assert area.contains(visible)
        assert not layout[0].availableGeometry().contains(window.geometry())
