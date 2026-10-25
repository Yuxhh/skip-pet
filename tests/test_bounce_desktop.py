"""Observe the combined character only through public Qt input and final image."""

import json
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
from test_v5_desktop import assert_frame_matches_region
from test_desktop import pointer


REFERENCES = Path(__file__).parent / "fixtures/bounce-native"


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("sample", json.loads((REFERENCES / "manifest.json").read_text())["samples"],
                         ids=lambda sample: sample["file"])
def test_combined_bounce_matches_frozen_native_at_all_sizes_and_scaled_dpr(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sample: dict,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    monkeypatch.setattr(PetWindow, "devicePixelRatioF", lambda self: sample["dpr"])
    path = tmp_path / "preferences.json"
    save_size(path, sample["height"])
    pet = PetApplication()
    window = PetWindow(pet, settings_path=path)
    try:
        window.show()
        app.processEvents()
        origin = window.pos()
        time = 0
        for at in sample["clicks_ms"]:
            pet.advance(at - time)
            app.processEvents()
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.visible_region.boundingRect().center())
            time = at
        pet.advance(sample["at_ms"] - time)
        QTest.qWait(15)
        frame = window.frame.convertToFormat(QImage.Format.Format_RGBA8888)
        expected = QImage(str(REFERENCES / sample["file"])).convertToFormat(QImage.Format.Format_RGBA8888)
        assert frame.size() == expected.size()
        # Full-image oracle catches collar separation and wrong crop/alpha anchors.
        assert max(abs(a - b) for a, b in zip(bytes(frame.constBits()), bytes(expected.constBits()))) <= 1
        assert_frame_matches_region(window)
        assert window.pos() == origin
        held = window.frame
        if "recovered" in sample["file"]:
            pet.advance(60_000)
            QTest.qWait(15)
            assert window.frame == held
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("gesture", ["threshold", "return", "ungrab", "hide"])
def test_changing_silhouette_preserves_drag_and_cancels_interrupted_clicks(
    app: QApplication, monkeypatch: pytest.MonkeyPatch, gesture: str,
) -> None:
    monkeypatch.setattr(desktop, "perf_counter", lambda: 0.0)
    pet, control = PetApplication(), PetApplication()
    window = PetWindow(pet)
    try:
        window.show()
        app.processEvents()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.visible_region.boundingRect().center())
        control.click()
        pet.advance(55)
        control.advance(55)
        QTest.qWait(15)
        origin = window.pos()
        start = window.mapToGlobal(window.visible_region.boundingRect().center())
        pointer(window, QEvent.Type.MouseButtonPress, start)
        delta = QPoint(QApplication.startDragDistance(), 0)
        if gesture in ("threshold", "return"):
            pointer(window, QEvent.Type.MouseMove, start + delta - QPoint(1, 0))
            assert window.pos() == origin
            pointer(window, QEvent.Type.MouseMove, start + delta)
            assert window.pos() == origin + delta
        previous_mask = window.visible_region
        pet.advance(55)
        control.advance(55)
        QTest.qWait(15)
        assert window.visible_region != previous_mask
        assert_frame_matches_region(window)
        if gesture == "ungrab":
            QApplication.sendEvent(window, QEvent(QEvent.Type.UngrabMouse))
        elif gesture == "hide":
            window.hide()
        destination = start + delta if gesture == "threshold" else start
        if gesture == "return":
            pointer(window, QEvent.Type.MouseMove, start)
            assert window.pos() == origin
        pointer(window, QEvent.Type.MouseButtonRelease, destination)
        assert pet.view == control.view
        pet.advance(110)
        control.advance(110)
        QTest.qWait(15)
        assert pet.view == control.view
        assert pet.view.bounce_scale == (1, 1)
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
