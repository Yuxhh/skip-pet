"""Screen-query fixtures and synthetic DPR; never physical hardware acceptance."""

import pytest
from PySide6.QtCore import QEvent, QPoint, QRect
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

import sukuna_pet.desktop as desktop
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from test_desktop import Screen, pet_window, pointer
from test_v5_desktop import assert_frame_matches_region
from test_resize import choose_size


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def screens(app: QApplication, monkeypatch: pytest.MonkeyPatch) -> list[Screen]:
    layout = [
        Screen(QRect(0, 0, 1920, 1080), QRect(0, 0, 1920, 1032)),
        Screen(QRect(-2560, -240, 1707, 960), QRect(-2528, -200, 1675, 920)),
        Screen(QRect(1920, -1440, 1280, 720), QRect(1920, -1400, 1280, 680)),
    ]
    current = [layout[0]]
    ratios = dict(zip(layout, (1.0, 1.5, 2.0)))
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    monkeypatch.setattr(QApplication, "screens", lambda: layout)
    monkeypatch.setattr(QApplication, "primaryScreen", lambda: layout[0])
    monkeypatch.setattr(QApplication, "screenAt", lambda p: next(
        (screen for screen in layout if screen.geometry().contains(p)), None))
    monkeypatch.setattr(PetWindow, "screen", lambda self: current[0])
    monkeypatch.setattr(PetWindow, "setScreen", lambda self, s: current.__setitem__(0, s))
    monkeypatch.setattr(PetWindow, "devicePixelRatioF", lambda self: ratios[current[0]])
    return layout


def bounds(window: PetWindow) -> QRect:
    return window.visible_region.boundingRect().translated(window.pos())


def test_cross_screen_drag_rebuilds_dpr_before_constraining_and_keeps_gesture(
    app: QApplication, screens: list[Screen],
) -> None:
    pet, control = PetApplication(), PetApplication()
    with pet_window(app, pet) as window:
        app.processEvents()
        pet.click()
        control.click()
        pet.advance(55)
        control.advance(55)
        app.processEvents()
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        # Each move must already expose the new physical frame and logical mask,
        # before a deferred native screen notification or another timer tick.
        for target, point, dpr in ((1, QPoint(-860, -200), 1.5),
                                   (2, QPoint(3190, -730), 2.0),
                                   (0, QPoint(1910, 1070), 1.0)):
            pointer(window, QEvent.Type.MouseMove, point)
            assert window.frame.devicePixelRatio() == dpr
            assert window.screen() is screens[target]
            assert screens[target].work.contains(bounds(window))
            assert bounds(window).right() == screens[target].work.right()
            assert_frame_matches_region(window)
            pet.advance(55)
            control.advance(55)
            app.processEvents()
        position = window.pos()
        pointer(window, QEvent.Type.MouseButtonRelease, point)
        assert window.pos() == position
        assert pet.view == control.view


def test_removed_screen_recovers_on_nearest_remaining_work_area(
    app: QApplication, screens: list[Screen],
) -> None:
    with pet_window(app, PetApplication()) as window:
        app.processEvents()
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        point = QPoint(-900, 500)
        pointer(window, QEvent.Type.MouseButtonRelease, point)
        assert window.screen() is screens[1]
        removed = screens.pop(1)
        # Any public screen-removal notification triggers a fresh screen query.
        # The native argument is a notification only; fixtures supply the layout.
        app.screenRemoved.emit(QGuiApplication.primaryScreen())
        app.processEvents()
        assert window.screen() is screens[0]
        assert screens[0].work.contains(bounds(window))
        assert window.frame.devicePixelRatio() == 1.0
        assert_frame_matches_region(window)
        assert removed not in screens


@pytest.mark.parametrize("notification", ["work", "geometry"])
def test_layout_change_during_held_drag_preserves_release_and_current_edges(
    app: QApplication, screens: list[Screen], notification: str,
) -> None:
    pet = PetApplication()
    with pet_window(app, pet) as window:
        app.processEvents()
        point = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, point)
        end = QPoint(-860, 700)
        pointer(window, QEvent.Type.MouseMove, end)
        screen = screens[1]
        screen.work = QRect(-2400, -100, 1400, 700)
        if notification == "geometry":
            screen.rect = QRect(-2440, -140, 1440, 740)
            screen.geometryChanged.emit(screen.rect)
        else:
            screen.availableGeometryChanged.emit(screen.work)
        app.processEvents()
        assert screen.work.contains(bounds(window))
        assert bounds(window).bottomRight() == screen.work.bottomRight()
        position = window.pos()
        before = pet.view
        pointer(window, QEvent.Type.MouseButtonRelease, end)
        assert window.pos() == position
        assert pet.view == before


@pytest.mark.parametrize("height", [188, 271, 320])
@pytest.mark.parametrize("target,point,dpr", [
    (1, QPoint(-500, 100), 1.5),  # Logical gap, nearest negative screen.
    (2, QPoint(2500, -900), 2.0),
])
def test_playing_cross_screen_release_resize_and_leaving_edges(
    app: QApplication, screens: list[Screen], monkeypatch: pytest.MonkeyPatch,
    height: int, target: int, point: QPoint, dpr: float,
) -> None:
    pet = PetApplication()
    pet.select_mode("always")
    with pet_window(app, pet) as window:
        app.processEvents()
        choose_size(window, height, monkeypatch)
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        pointer(window, QEvent.Type.MouseMove, point)
        before = pet.view
        pointer(window, QEvent.Type.MouseButtonRelease, point)
        assert pet.view == before
        assert window.screen() is screens[target]
        assert window.frame.devicePixelRatio() == dpr
        area = screens[target].work
        # Release on the target's bottom/right edges while animation continues.
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        pointer(window, QEvent.Type.MouseButtonRelease, area.bottomRight())
        for elapsed in (110, 110, 780, 110):
            pet.advance(elapsed)
            QTest.qWait(12)
            assert bounds(window).bottomRight() == area.bottomRight()
            assert area.contains(bounds(window))
        for size in (188, 271, 320):
            choose_size(window, size, monkeypatch)
            assert bounds(window).bottomRight() == area.bottomRight()
            assert_frame_matches_region(window)
        # A free placement releases both old edges and keeps a stable anchor.
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        pointer(window, QEvent.Type.MouseButtonRelease, area.center())
        position = window.pos()
        pet.advance(110)
        QTest.qWait(12)
        assert window.pos() == position
        assert area.contains(bounds(window))


@pytest.mark.parametrize("kind", [QEvent.Type.DevicePixelRatioChange,
                                  QEvent.Type.ScreenChangeInternal])
def test_dpr_notification_during_held_edge_gesture_refreshes_without_click(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, screens: list[Screen],
    kind: QEvent.Type,
) -> None:
    pet = PetApplication()
    with pet_window(app, pet) as window:
        app.processEvents()
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        end = screens[0].work.bottomRight()
        pointer(window, QEvent.Type.MouseMove, end)
        monkeypatch.setattr(PetWindow, "devicePixelRatioF", lambda self: 1.25)
        QApplication.sendEvent(window, QEvent(kind))
        app.processEvents()
        assert window.frame.devicePixelRatio() == 1.25
        assert bounds(window).bottomRight() == screens[0].work.bottomRight()
        assert_frame_matches_region(window)
        position = window.pos()
        before = pet.view
        pointer(window, QEvent.Type.MouseButtonRelease, end)
        assert window.pos() == position
        assert pet.view == before


def test_screen_connection_notification_rechecks_visibility(
    app: QApplication, screens: list[Screen],
) -> None:
    with pet_window(app, PetApplication()) as window:
        app.processEvents()
        window.move(4000, 4000)
        native_screen = QGuiApplication.primaryScreen()
        app.screenAdded.emit(native_screen)
        app.processEvents()
        assert screens[0].work.contains(bounds(window))
        # A newly connected native screen is also watched for later work changes.
        window.move(4000, 4000)
        native_screen.availableGeometryChanged.emit(native_screen.availableGeometry())
        app.processEvents()
        assert screens[0].work.contains(bounds(window))
