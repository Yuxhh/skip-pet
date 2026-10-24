"""Qt is an adapter: input and elapsed time enter through PetApplication."""

import sys
from pathlib import Path
from time import perf_counter

from PySide6.QtCore import QPoint, QRectF, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QActionGroup, QContextMenuEvent, QMouseEvent, QPaintEvent, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QWidget

from .playback import PetApplication
from .rendering import CharacterRenderer, DISPLAY_HEIGHT, DISPLAY_WIDTH, SOURCE_BOUNDS
from .settings import Mode


class PetWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("宿傩桌宠")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(DISPLAY_WIDTH, DISPLAY_HEIGHT)
        settings_path = Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation,
        )) / "mode.json"
        self._pet = PetApplication(settings_path=settings_path)
        self._renderer = CharacterRenderer()
        self._frame = self._renderer.render(self._pet.view)
        self._last_time = perf_counter()
        self._press: QPoint | None = None
        self._origin = QPoint()
        self._dragged = False
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(8)
        self._timer.timeout.connect(self._advance)
        self._timer.start()
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.right() - self.width() - 32, area.bottom() - self.height() - 32)

    def _advance(self) -> None:
        now = perf_counter()
        before = self._pet.view
        self._pet.advance((now - self._last_time) * 1000)
        self._last_time = now
        if self._pet.view != before:
            self._frame = self._renderer.render(self._pet.view)
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QRectF(self.rect()), self._frame, SOURCE_BOUNDS)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._origin = self.pos()
            self._dragged = False
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # Qt sends a double-click event in place of the second press.
        self.mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._press is None:
            return
        distance = event.globalPosition().toPoint() - self._press
        if distance.manhattanLength() >= QApplication.startDragDistance():
            self._dragged = True
        if self._dragged:
            self.move(self._origin + distance)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._press is None:
            return
        self._press = None
        if not self._dragged:
            self._advance()
            self._pet.click()
            self._frame = self._renderer.render(self._pet.view)
            self.update()
        event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        modes = QActionGroup(menu)
        for value, label in (("click", "点击跳动"), ("always", "持续跳动")):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self._pet.mode == value)
            modes.addAction(action)
        click_action, always_action = modes.actions()
        click_action.triggered.connect(lambda: self._select_mode("click"))
        always_action.triggered.connect(lambda: self._select_mode("always"))
        menu.addSeparator()
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        menu.exec(event.globalPos())
        menu.deleteLater()

    def _select_mode(self, mode: Mode) -> None:
        self._advance()
        try:
            self._pet.select_mode(mode)
        except OSError:
            QMessageBox.warning(self, "无法保存模式", "请检查设置目录是否可写，然后重试。")
        self._frame = self._renderer.render(self._pet.view)
        self.update()


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("skip-pet")
    app.setApplicationName("sukuna-pet")
    app.setApplicationDisplayName("宿傩桌宠")
    window = PetWindow()
    window.show()
    return app.exec()
