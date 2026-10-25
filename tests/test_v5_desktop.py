"""Approved Qt event/geometry/final-image seam; synthetic DPR is not hardware QA."""

import math
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import sukuna_pet.desktop as desktop
from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.settings import save_size


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_visible_head_motion_updates_the_same_final_frame_and_visible_region(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(desktop, "perf_counter", lambda: clock[0])
    pet = PetApplication()
    window = PetWindow(pet)
    try:
        window.show()
        app.processEvents()
        assert (window.width(), window.height()) == (328, 320)
        initial_frame, initial_mask = window.frame, window.visible_region
        point = initial_mask.boundingRect().center()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point)
        clock[0] = .1
        QTest.qWait(25)
        assert -6.44 < pet.view.head_angle < 0
        assert window.frame != initial_frame
        assert window.visible_region != initial_mask
        assert window.rect().contains(window.visible_region.boundingRect())
        assert not window.visible_region.contains(QPoint(0, 0))
        clock[0] = .3
        QTest.qWait(25)
        clock[0] = .5
        QTest.qWait(25)
        assert pet.view.holding
        held = window.frame
        clock[0] = 10
        QTest.qWait(25)
        assert window.frame == held
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def assert_frame_matches_region(window: PetWindow) -> None:
    frame, region = window.frame, window.visible_region
    dpr = frame.devicePixelRatio()
    rgba = frame.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = bytes(rgba.constBits())
    rows = [pixels[y * rgba.bytesPerLine() + 3:y * rgba.bytesPerLine() + rgba.width() * 4:4]
            for y in range(rgba.height())]
    # Independently inspect every logical cell's overlapping physical pixels.
    # This detects both omitted antialiasing and stale/union silhouettes.
    for y in range(window.height()):
        physical_rows = rows[math.floor(y * dpr):math.ceil((y + 1) * dpr)]
        for x in range(window.width()):
            left, right = math.floor(x * dpr), math.ceil((x + 1) * dpr)
            visible = any(any(row[left:right]) for row in physical_rows)
            assert region.contains(QPoint(x, y)) == visible, (dpr, x, y)
    bounds = region.boundingRect()
    assert bounds.left() > 0 and bounds.top() > 0
    assert bounds.right() < window.width() - 1
    assert bounds.bottom() < window.height() - 1


@pytest.mark.parametrize("height,width", [(188, 193), (271, 278), (320, 328)])
@pytest.mark.parametrize("dpr", [1, 1.25, 1.5, 2])
def test_three_sizes_and_dpr_keep_every_stage_inside_and_alpha_accurate(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    height: int, width: int, dpr: float,
) -> None:
    clock = [0.0]
    monkeypatch.setattr(desktop, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(PetWindow, "devicePixelRatioF", lambda self: dpr)
    path = tmp_path / "preferences.json"
    save_size(path, height)
    pet = PetApplication()
    window = PetWindow(pet, settings_path=path)
    try:
        assert (window.width(), window.height()) == (width, height)
        for stage in range(4):
            assert pet.view.stage == stage
            frame = window.frame
            assert (frame.width(), frame.height()) == (math.ceil(width * dpr), math.ceil(height * dpr))
            assert_frame_matches_region(window)
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.visible_region.boundingRect().center())
            for _ in range(4):
                clock[0] += .1
                QTest.qWait(10)
        assert pet.view.stage == 0 and pet.view.holding
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_dpr_change_rebuilds_both_frame_and_region_without_advancing(
    app: QApplication, monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock, dpr = [0.0], [1.0]
    monkeypatch.setattr(desktop, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(PetWindow, "devicePixelRatioF", lambda self: dpr[0])
    pet = PetApplication()
    window = PetWindow(pet)
    try:
        initial = pet.view
        dpr[0] = 1.5
        QApplication.sendEvent(window, QEvent(QEvent.Type.DevicePixelRatioChange))
        app.processEvents()
        assert window.frame.devicePixelRatio() == 1.5
        assert window.frame.width() == 492
        assert_frame_matches_region(window)
        assert pet.view == initial
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
