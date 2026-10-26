"""Native Qt integration without changing the user's profile or conversations."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication
from sukuna_pet.task_bridge import TaskSummary
from sukuna_pet.task_bubble import bubble_position


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_native_bubble_and_task_mode_preserve_click_area(app: QApplication, tmp_path: Path) -> None:
    class Monitor:
        summary = TaskSummary(running=1, jump=True)
        closed = False

        def close(self) -> None:
            self.closed = True

    monitor = Monitor()
    pet = PetApplication(settings_path=tmp_path / "mode.json")
    pet.select_mode("task")
    window = PetWindow(pet, task_monitor=monitor)  # type: ignore[arg-type]
    try:
        window.show()
        QTest.qWait(100)
        assert pet.view.stage == 1
        bubble = window._bubble
        assert bubble.isVisible() and "还在办" in bubble.text()
        assert bubble.windowFlags() & Qt.WindowType.WindowTransparentForInput
        assert window.screen().availableGeometry().contains(bubble.geometry())
        # Move to the top; the bubble must move below without resizing the pet.
        height = window.height()
        window.move(100, 0)
        QTest.qWait(30)
        assert window.height() == height
        assert window.screen().availableGeometry().contains(bubble.geometry())
        monitor.summary = TaskSummary(waiting=1)
        QTest.qWait(30)
        assert "回答" in bubble.text()
        monitor.summary = TaskSummary()
        QTest.qWait(30)
        assert not bubble.isVisible()
    finally:
        window.close()
        assert monitor.closed
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.parametrize("character", [QRect(-1910, -150, 250, 300), QRect(-200, 500, 250, 300)])
def test_bubble_clamps_on_negative_origin_screen(character: QRect) -> None:
    area = QRect(-1920, -200, 1920, 1080)
    position = bubble_position(character, area, 300, 80)
    assert area.contains(QRect(position.x(), position.y(), 300, 80))
