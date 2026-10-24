"""Qt is an adapter: input and elapsed time enter through PetApplication."""

import sys
from pathlib import Path
from time import perf_counter

from PySide6.QtCore import QEvent, QPoint, QRectF, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QActionGroup, QContextMenuEvent, QImage, QMouseEvent, QPaintEvent, QPainter, QRegion, QScreen
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QWidget

from .playback import PetApplication
from .rendering import CharacterRenderer, DISPLAY_HEIGHT, DISPLAY_WIDTH, SOURCE_BOUNDS
from .settings import Mode


class PetWindow(QWidget):
    def __init__(self, application: PetApplication | None = None) -> None:
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
        self._pet = application if application is not None else PetApplication(settings_path=settings_path)
        self._renderer = CharacterRenderer()
        self._frame = self._renderer.render(self._pet.view)
        # A real native window region, not just transparent painting. Keep every
        # nonzero-alpha pixel, including antialiased edges. The silhouette is
        # invariant: eye animation stays within the opaque face.
        self.setMask(_character_region(self._frame))
        self._last_time = perf_counter()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(8)
        self._timer.timeout.connect(self._advance)
        self._timer.start()
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self._move_visible((area.right() - self.width() - 32,
                                area.bottom() - self.height() - 32), screen)
        for screen in QApplication.screens():
            self._watch_screen(screen)
        app = QApplication.instance()
        assert isinstance(app, QApplication)
        app.screenAdded.connect(self._watch_screen)
        app.screenRemoved.connect(self._schedule_visibility)

    def _watch_screen(self, screen: QScreen) -> None:
        screen.availableGeometryChanged.connect(self._schedule_visibility)
        screen.geometryChanged.connect(self._schedule_visibility)
        self._schedule_visibility()

    def _schedule_visibility(self) -> None:
        # Let Qt finish its native DPI/screen change before rechecking geometry.
        QTimer.singleShot(0, self, self._keep_visible)

    def _keep_visible(self) -> None:
        self._move_visible((self.x(), self.y()), self.screen())

    def _move_visible(self, destination: tuple[int, int], screen: QScreen) -> None:
        # Both rectangles are in Qt logical pixels, including on negative-origin
        # screens. Transparent margins may extend outside the work area.
        area = screen.availableGeometry()
        visible = self.mask().boundingRect()
        x = max(area.left() - visible.left(), min(destination[0], area.right() - visible.right()))
        y = max(area.top() - visible.top(), min(destination[1], area.bottom() - visible.bottom()))
        if self.screen() != screen:
            self.setScreen(screen)
        self.move(x, y)

    def _move_drag(self, destination: tuple[int, int], cursor: QPoint) -> None:
        screen = QApplication.screenAt(cursor)
        if screen is None:
            # Qt's Windows virtual desktop can have gaps between logical screen
            # rectangles. Never treat their union as one usable work area.
            def distance(candidate: QScreen) -> int:
                rect = candidate.geometry()
                dx = max(rect.left() - cursor.x(), 0, cursor.x() - rect.right())
                dy = max(rect.top() - cursor.y(), 0, cursor.y() - rect.bottom())
                return dx * dx + dy * dy

            screen = min(QApplication.screens(), key=distance, default=None)
        if screen is not None:
            self._move_visible(destination, screen)

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
            point = event.globalPosition().toPoint()
            self._pet.pointer_press(
                (point.x(), point.y()), (self.x(), self.y()),
                drag_distance=QApplication.startDragDistance(),
            )
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # Qt sends a double-click event in place of the second press.
        self.mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        point = event.globalPosition().toPoint()
        destination = self._pet.pointer_move((point.x(), point.y()))
        if destination is not None:
            self._move_drag(destination, point)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._advance()
        point = event.globalPosition().toPoint()
        destination = self._pet.pointer_release((point.x(), point.y()))
        if destination is not None:
            self._move_drag(destination, point)
        self._frame = self._renderer.render(self._pet.view)
        self.update()
        event.accept()

    def event(self, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.UngrabMouse, QEvent.Type.Hide):
            # QWidget can receive events before our application is constructed.
            if hasattr(self, "_pet"):
                self._pet.cancel_pointer()
        if event.type() in (QEvent.Type.DevicePixelRatioChange, QEvent.Type.ScreenChangeInternal):
            if hasattr(self, "_renderer"):
                self._schedule_visibility()
        return super().event(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self._pet.cancel_pointer()
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


def _character_region(frame: QImage) -> QRegion:
    """Match the painted crop in logical pixels; Qt scales the region for DPI."""
    image = QImage(DISPLAY_WIDTH, DISPLAY_HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(QRectF(image.rect()), frame, SOURCE_BOUNDS)
    painter.end()
    region = QRegion()
    for y in range(image.height()):
        start: int | None = None
        for x in range(image.width() + 1):
            visible = x < image.width() and image.pixelColor(x, y).alpha() > 0
            if visible and start is None:
                start = x
            elif not visible and start is not None:
                region |= QRegion(start, y, x - start, 1)
                start = None
    return region


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("skip-pet")
    app.setApplicationName("sukuna-pet")
    app.setApplicationDisplayName("宿傩桌宠")
    window = PetWindow()
    window.show()
    return app.exec()
