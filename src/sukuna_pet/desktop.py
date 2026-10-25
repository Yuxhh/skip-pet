"""Qt is an adapter: input and elapsed time enter through PetApplication."""

import math
import re
import sys
from pathlib import Path
from time import perf_counter

from PySide6.QtCore import QEvent, QPoint, QPointF, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QActionGroup, QContextMenuEvent, QImage, QMouseEvent, QPaintEvent, QPainter, QRegion, QScreen
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QWidget

from .playback import PetApplication, PetView
from .rendering import CharacterRenderer, SOURCE_BOUNDS
from .settings import DEFAULT_SIZE, DISPLAY_SIZES, Mode, load_size, save_size


class PetWindow(QWidget):
    def __init__(
        self, application: PetApplication | None = None, *, settings_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("宿傩桌宠")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if application is None and settings_path is None:
            settings_path = Path(QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppConfigLocation,
            )) / "mode.json"
        self._settings_path = settings_path
        height = load_size(settings_path) if settings_path is not None else DEFAULT_SIZE
        self.setFixedSize(math.ceil(height * SOURCE_BOUNDS.width() / SOURCE_BOUNDS.height()), height)
        self._pet = application if application is not None else PetApplication(settings_path=settings_path)
        self._renderer = CharacterRenderer()
        self._frame = QImage()
        self._render_key: tuple[PetView, int, float] | None = None
        self._edges = Qt.Edge(0)
        self._pointer_compensation: QPoint | None = None
        self._refresh_frame()
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

    @property
    def frame(self) -> QImage:
        """Read-only snapshot of the final physical-pixel image used by Qt."""
        return self._frame.copy()

    def _refresh_frame(self) -> None:
        if not self._update_frame():
            return
        self._keep_visible()

    def _update_frame(self) -> bool:
        key = (self._pet.view, self.height(), self.devicePixelRatioF())
        if key == self._render_key:
            return False
        self._frame = self._renderer.render(*key)
        self.setMask(_character_region(self._frame))
        self._render_key = key
        self.update()
        return True

    def _watch_screen(self, screen: QScreen) -> None:
        screen.availableGeometryChanged.connect(self._schedule_visibility)
        screen.geometryChanged.connect(self._schedule_visibility)
        self._schedule_visibility()

    def _schedule_visibility(self) -> None:
        # Let Qt finish its native DPI/screen change before rechecking geometry.
        QTimer.singleShot(0, self, self._keep_visible)

    def _keep_visible(self) -> None:
        screen: QScreen | None = self.screen()
        if screen not in QApplication.screens():
            screen = _screen_at(self.mask().boundingRect().translated(self.pos()).center())
        if screen is not None:
            self._move_visible((self.x(), self.y()), screen, follow_edges=True)

    def _move_visible(
        self, destination: tuple[int, int], screen: QScreen, *, follow_edges: bool = False,
    ) -> None:
        # Both rectangles are in Qt logical pixels, including on negative-origin
        # screens. Transparent margins may extend outside the work area.
        previous_position = self.pos()
        if self.screen() != screen:
            self.setScreen(screen)
        # Screen selection must precede rasterization and logical constraints.
        # Native DPI notifications also recheck after Qt completes the change.
        self._update_frame()
        area = screen.availableGeometry()
        visible = self.mask().boundingRect()
        if follow_edges:
            x, y = destination
            if self._edges & Qt.Edge.LeftEdge:
                x = area.left() - visible.left()
            elif self._edges & Qt.Edge.RightEdge:
                x = area.right() - visible.right()
            if self._edges & Qt.Edge.TopEdge:
                y = area.top() - visible.top()
            elif self._edges & Qt.Edge.BottomEdge:
                y = area.bottom() - visible.bottom()
            destination = x, y
        x = max(area.left() - visible.left(), min(destination[0], area.right() - visible.right()))
        y = max(area.top() - visible.top(), min(destination[1], area.bottom() - visible.bottom()))
        self.move(x, y)
        if follow_edges and self._pointer_compensation is not None:
            # Carry contour/layout corrections, but not pointer clamping, into
            # the fixed application drag origin for the next move or release.
            self._pointer_compensation += self.pos() - previous_position
        self._edges = Qt.Edge(0)
        if x + visible.left() == area.left():
            self._edges |= Qt.Edge.LeftEdge
        elif x + visible.right() == area.right():
            self._edges |= Qt.Edge.RightEdge
        if y + visible.top() == area.top():
            self._edges |= Qt.Edge.TopEdge
        elif y + visible.bottom() == area.bottom():
            self._edges |= Qt.Edge.BottomEdge

    def _move_drag(self, destination: tuple[int, int], cursor: QPoint) -> None:
        if self._pointer_compensation is not None:
            destination = (destination[0] + self._pointer_compensation.x(),
                           destination[1] + self._pointer_compensation.y())
        screen = _screen_at(cursor)
        if screen is not None:
            self._move_visible(destination, screen)

    def _advance(self) -> None:
        now = perf_counter()
        # One capped real frame enters the model once. PetApplication splits
        # motion into <=4ms steps, but keeps automatic waits frame-granular.
        self._pet.advance(min(150, (now - self._last_time) * 1000))
        self._last_time = now
        self._keep_visible()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.drawImage(QPointF(0, 0), self._frame)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.globalPosition().toPoint()
            self._pointer_compensation = QPoint()
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
        self._pointer_compensation = None
        self._refresh_frame()
        event.accept()

    def _cancel_pointer(self) -> None:
        self._pet.cancel_pointer()
        self._pointer_compensation = None

    def event(self, event: QEvent) -> bool:
        if event.type() in (QEvent.Type.UngrabMouse, QEvent.Type.Hide):
            # QWidget can receive events before our application is constructed.
            if hasattr(self, "_pet"):
                self._cancel_pointer()
        if event.type() in (QEvent.Type.DevicePixelRatioChange, QEvent.Type.ScreenChangeInternal):
            if hasattr(self, "_renderer"):
                self._schedule_visibility()
        return super().event(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self._cancel_pointer()
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
        size_menu = menu.addMenu("调整大小")
        sizes = QActionGroup(size_menu)
        for size in DISPLAY_SIZES:
            action = size_menu.addAction(f"{size}px")
            action.setCheckable(True)
            action.setChecked(self.height() == size)
            sizes.addAction(action)
            action.triggered.connect(lambda checked=False, height=size: self._select_size(height))
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
        self._refresh_frame()

    def _select_size(self, height: int) -> None:
        if height not in DISPLAY_SIZES or height == self.height():
            return
        self._cancel_pointer()
        try:
            if self._settings_path is not None:
                save_size(self._settings_path, height)
        except OSError:
            QMessageBox.warning(self, "无法保存大小", "请检查设置目录是否可写，然后重试。")
            return
        # Anchor the feet and horizontal centre while the character grows.
        centre_x = self.x() + self.width() // 2
        bottom = self.y() + self.height()
        self.setFixedSize(math.ceil(height * SOURCE_BOUNDS.width() / SOURCE_BOUNDS.height()), height)
        self._refresh_frame()
        self._move_visible((centre_x - self.width() // 2, bottom - height), self.screen(), follow_edges=True)
        self.update()


def _screen_at(point: QPoint) -> QScreen | None:
    screen = QApplication.screenAt(point)
    if screen is not None:
        return screen
    # Qt logical desktops can have gaps. Compare individual screens, never
    # their outer rectangle, including when recovering from screen removal.
    def distance(candidate: QScreen) -> int:
        rect = candidate.geometry()
        dx = max(rect.left() - point.x(), 0, point.x() - rect.right())
        dy = max(rect.top() - point.y(), 0, point.y() - rect.bottom())
        return dx * dx + dy * dy

    return min(QApplication.screens(), key=distance, default=None)


def _character_region(frame: QImage) -> QRegion:
    """Outward logical coverage of every nonzero alpha pixel in the final frame."""
    dpr = frame.devicePixelRatio()
    image = frame.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = bytes(image.constBits())
    region = QRegion()
    for y in range(image.height()):
        offset = y * image.bytesPerLine()
        alpha = pixels[offset + 3:offset + image.width() * 4:4]
        for run in re.finditer(b"[^\x00]+", alpha):
            left, top = math.floor(run.start() / dpr), math.floor(y / dpr)
            right, bottom = math.ceil(run.end() / dpr), math.ceil((y + 1) / dpr)
            region |= QRegion(left, top, right - left, bottom - top)
    return region


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("skip-pet")
    app.setApplicationName("sukuna-pet")
    app.setApplicationDisplayName("宿傩桌宠")
    window = PetWindow()
    window.show()
    return app.exec()
