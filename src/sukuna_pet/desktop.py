"""Qt is an adapter: input and elapsed time enter through PetApplication."""

import math
import re
import sys
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QPoint, QPointF, QStandardPaths, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QActionGroup, QCloseEvent, QContextMenuEvent, QIcon, QImage, QMouseEvent, QPaintEvent, QPainter, QPixmap, QRegion, QScreen
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget

from .playback import PetApplication, PetView
from .bridge_control import BridgeController
from .bridge_install import BridgeInstaller, InstallPlan, maintenance_directory
from .rendering import CharacterRenderer, SOURCE_BOUNDS
from .settings import DEFAULT_SIZE, DISPLAY_SIZES, MODE_LABELS, Mode, load_size, save_size
from .task_bridge import TaskMonitor
from .task_bridge import TaskSummary
from .task_bubble import TaskBubble
from .credentials import CredentialStore
from .settings_window import SettingsWindow
from .chat_controller import ChatController
from .chat_window import ChatWindow
from .session_store import SessionStore

if TYPE_CHECKING:
    from .music import MusicPlayer


class PetWindow(QWidget):
    preferences_changed = Signal()

    def __init__(
        self, application: PetApplication | None = None, *, settings_path: Path | None = None,
        task_monitor: TaskMonitor | None = None,
        bridge_installer: BridgeInstaller | None = None,
        credentials: CredentialStore | None = None,
        chat_data_dir: Path | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("宿傩桌宠")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        # Tool windows skip the Windows taskbar, but must still end the app on
        # an accepted close. Qt disables QuitOnClose for tools by default.
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if application is None and settings_path is None:
            settings_path = Path(QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppConfigLocation,
            )) / "mode.json"
            if chat_data_dir is None:
                chat_data_dir = Path(QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.AppLocalDataLocation,
                )) / "chat" / "sessions"
        elif chat_data_dir is None and settings_path is not None:
            chat_data_dir = settings_path.parent / "chat" / "sessions"
        self._chat_data_dir = chat_data_dir
        self._closing_with_chat = False
        self._settings_path = settings_path
        self._credentials = credentials
        self._settings_window: SettingsWindow | None = None
        self._chat_window: ChatWindow | None = None
        self._chat_open_timer = QTimer(self)
        self._chat_open_timer.setSingleShot(True)
        self._chat_open_timer.setInterval(50)
        self._chat_open_timer.timeout.connect(self.open_chat)
        height = load_size(settings_path) if settings_path is not None else DEFAULT_SIZE
        self.setFixedSize(math.ceil(height * SOURCE_BOUNDS.width() / SOURCE_BOUNDS.height()), height)
        self._pet = application if application is not None else PetApplication(settings_path=settings_path)
        self._music: MusicPlayer | None = None
        self._task_monitor = task_monitor
        self._bridge: BridgeController | None = None
        if task_monitor is None and settings_path is not None:
            installer = bridge_installer or BridgeInstaller(data_dir=maintenance_directory())
            self._bridge = BridgeController(settings_path, installer, self)
            self._bridge.prepared.connect(self._confirm_bridge)
            self._bridge.notice.connect(self._bridge_notice)
            QTimer.singleShot(0, self._bridge.start)
        self._bubble = TaskBubble(self)
        self._renderer = CharacterRenderer()
        self._frame = QImage()
        self._visible_region = QRegion()
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
        self._create_tray()

    def _create_tray(self) -> None:
        icon = QIcon(QPixmap.fromImage(self._frame))
        self.setWindowIcon(icon)
        # Keep both wrappers alive for native tray menu callbacks.
        self._tray_menu = QMenu(self)
        self._tray_menu.addAction("显示桌宠").triggered.connect(self._show_from_tray)
        # Present the chat after the native popup has returned. Constructing
        # and activating a window inside QMenu.exec() can lose activation.
        self._tray_menu.addAction("AI 对话").triggered.connect(
            self.open_chat, Qt.ConnectionType.QueuedConnection)
        self._tray_menu.addSeparator()
        self._tray_menu.addAction("桌宠设置").triggered.connect(
            self._open_default_settings, Qt.ConnectionType.QueuedConnection)
        self._tray_menu.addAction("退出").triggered.connect(self.close)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("宿傩桌宠")
        self._tray.setContextMenu(self._tray_menu)
        self._tray.activated.connect(self._activate_tray)
        self._tray.show()

    def _show_from_tray(self) -> None:
        self._keep_visible()
        self.show()
        self.raise_()

    def _activate_tray(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    @property
    def credentials(self) -> CredentialStore:
        if self._credentials is None:
            self._credentials = CredentialStore()
        return self._credentials

    @property
    def pet_mode(self) -> Mode:
        return self._pet.mode

    @property
    def bridge_controller(self) -> BridgeController | None:
        return self._bridge

    @property
    def music_playing(self) -> bool:
        return self._music is not None and self._music.active

    def _sync_music(self) -> None:
        if self._pet.music_requested:
            if self._music is None:
                from .music import MusicPlayer
                self._music = MusicPlayer(self)
                self._music.stopped.connect(self._music_stopped)
                self._music.failed.connect(self._music_failed, Qt.ConnectionType.QueuedConnection)
            if not self._music.active:
                self._music.play()
            self._pet.set_music_position(self._music.position_ms)
        elif self._music is not None:
            self._music.stop()

    def _music_stopped(self) -> None:
        self._pet.stop_music()
        self._refresh_frame()
        self.preferences_changed.emit()

    def _music_failed(self) -> None:
        QMessageBox.warning(self, "无法播放音乐", "音乐片段无法播放，请检查系统声音输出后重试。")

    def open_settings(self, page: str = "桌宠") -> None:
        if self._settings_window is None:
            self._settings_window = SettingsWindow(self)
        self._settings_window.open_page(page)

    @Slot()
    def _open_default_settings(self) -> None:
        # Discard QAction's checked argument and activate after popup teardown.
        self.open_settings()

    @Slot()
    def open_chat(self) -> None:
        # A queued QAction can still be delivered by a nested native menu
        # loop. Match dsh-pet's popup guard before constructing or presenting.
        if QApplication.activePopupWidget() is not None:
            if not self._chat_open_timer.isActive():
                self._chat_open_timer.start()
            return
        self._chat_open_timer.stop()
        if self._chat_window is None:
            store = SessionStore(self._chat_data_dir) if self._chat_data_dir is not None else None
            controller = ChatController(self.credentials, self, store=store)
            self._chat_window = ChatWindow(controller, self)
            self._chat_window.settings_requested.connect(lambda: self.open_settings("AI 对话"))
            self._chat_window.closed.connect(self._chat_closed)
            self._chat_window.close_cancelled.connect(self._cancel_chat_exit)
        self._chat_window.open_window()

    def _chat_closed(self) -> None:
        if self._closing_with_chat:
            self._closing_with_chat = False
            QTimer.singleShot(0, self.close)

    def _cancel_chat_exit(self) -> None:
        self._closing_with_chat = False

    @property
    def frame(self) -> QImage:
        """Read-only snapshot of the final physical-pixel image used by Qt."""
        return self._frame.copy()

    @property
    def visible_region(self) -> QRegion:
        """Logical alpha coverage for geometry, without native visual clipping."""
        return QRegion(self._visible_region)

    def _refresh_frame(self) -> None:
        if not self._update_frame():
            return
        self._keep_visible()

    def _update_frame(self) -> bool:
        key = (self._pet.view, self.height(), self.devicePixelRatioF())
        if key == self._render_key:
            return False
        self._frame = self._renderer.render(*key)
        # A native mask changes immediately, before Qt uploads the new layered
        # image, exposing mixed old/new contours during animation. Windows uses
        # the uploaded image's alpha for both display and mouse hit testing.
        # Keep coverage only for layout; upload the full transparent frame.
        self._visible_region = _character_region(self._frame)
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
            screen = _screen_at(self._visible_region.boundingRect().translated(self.pos()).center())
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
        visible = self._visible_region.boundingRect()
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
        summary = (self._task_monitor.summary if self._task_monitor is not None else
                   self._bridge.summary if self._bridge is not None else TaskSummary())
        self._pet.set_task_running(summary.jump)
        self._sync_music()
        # One capped real frame enters the model once. PetApplication splits
        # motion into <=4ms steps, but keeps automatic waits frame-granular.
        self._pet.advance(min(150, (now - self._last_time) * 1000))
        self._last_time = now
        self._keep_visible()
        if self.isVisible():
            area = self.screen().availableGeometry()
            character = self._visible_region.boundingRect().translated(self.pos())
            self._bubble.present(summary.text, character, area)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._chat_window is not None:
            if not self._chat_window.close():
                self._closing_with_chat = True
                event.ignore()
                return
        if self._settings_window is not None:
            self._settings_window.close()
        self._chat_open_timer.stop()
        if self._credentials is not None:
            self._credentials.release()
        self._timer.stop()
        if self._music is not None:
            self._music.stop()
        self._bubble.hide()
        if self._task_monitor is not None:
            self._task_monitor.close()
        if self._bridge is not None:
            self._bridge.close()
        self._tray.hide()
        super().closeEvent(event)

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
        chat_action = menu.addAction("AI 对话")
        chat_action.triggered.connect(self.open_chat, Qt.ConnectionType.QueuedConnection)
        menu.addSeparator()
        modes = QActionGroup(menu)
        for value, label in MODE_LABELS:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self._pet.mode == value)
            modes.addAction(action)
            action.triggered.connect(lambda checked=False, chosen=value: self.select_mode(chosen))
        menu.addSeparator()
        if self._bridge is not None:
            bridge_action = menu.addAction("关闭 DeepSeek 接入" if self._bridge.enabled else "启用 DeepSeek 接入")
            bridge_action.setEnabled(not self._bridge.busy)
            bridge_action.triggered.connect(self._bridge.disable if self._bridge.enabled else self._bridge.prepare)
            menu.addSeparator()
        size_menu = menu.addMenu("调整大小")
        sizes = QActionGroup(size_menu)
        for size in DISPLAY_SIZES:
            action = size_menu.addAction(f"{size}px")
            action.setCheckable(True)
            action.setChecked(self.height() == size)
            sizes.addAction(action)
            action.triggered.connect(lambda checked=False, height=size: self.select_size(height))
        menu.addSeparator()
        # Keep settings directly above Exit, which must remain the last item.
        settings_action = menu.addAction("桌宠设置")
        settings_action.triggered.connect(self._open_default_settings, Qt.ConnectionType.QueuedConnection)
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        menu.exec(event.globalPos())
        menu.deleteLater()

    def _confirm_bridge(self, plan: InstallPlan) -> None:
        answer = QMessageBox.question(self, "启用 DeepSeek 接入", plan.description,
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes and self._bridge is not None:
            self._bridge.confirm(plan)

    def _bridge_notice(self, title: str, text: str) -> None:
        if title == "DeepSeek 接入已更新":
            QMessageBox.information(self, title, text)
        else:
            QMessageBox.warning(self, title, text)

    def select_mode(self, mode: Mode) -> None:
        self._advance()
        try:
            self._pet.select_mode(mode)
        except OSError:
            QMessageBox.warning(self, "无法保存模式", "请检查设置目录是否可写，然后重试。")
            self.preferences_changed.emit()
            return
        if mode == "music":
            self._pet.click()
        if self._pet.music_requested:
            # Initialize the Windows audio device after the menu input event.
            QTimer.singleShot(0, self._sync_music)
        else:
            self._sync_music()
        self._refresh_frame()
        self.preferences_changed.emit()

    def select_size(self, height: int) -> None:
        if height not in DISPLAY_SIZES or height == self.height():
            return
        self._cancel_pointer()
        try:
            if self._settings_path is not None:
                save_size(self._settings_path, height)
        except OSError:
            QMessageBox.warning(self, "无法保存大小", "请检查设置目录是否可写，然后重试。")
            self.preferences_changed.emit()
            return
        # Anchor the feet and horizontal centre while the character grows.
        centre_x = self.x() + self.width() // 2
        bottom = self.y() + self.height()
        self.setFixedSize(math.ceil(height * SOURCE_BOUNDS.width() / SOURCE_BOUNDS.height()), height)
        self._refresh_frame()
        self._move_visible((centre_x - self.width() // 2, bottom - height), self.screen(), follow_edges=True)
        self.update()
        self.preferences_changed.emit()


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
    if len(sys.argv) > 2 and sys.argv[1] == "--verify-settings":
        from .settings_check import main as verify_settings
        return verify_settings(sys.argv[2:])
    if len(sys.argv) > 2 and sys.argv[1] == "--verify-music":
        from .music_check import main as verify_music
        return verify_music(sys.argv[2:])
    if len(sys.argv) > 2 and sys.argv[1] in ("--verify-installation", "--verify-installation-readback"):
        from .installation_check import main as verify_main
        return verify_main(sys.argv[2:], readback=sys.argv[1].endswith("-readback"))
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall-cleanup":
        from .uninstall_cleanup import main as cleanup_main
        return cleanup_main(sys.argv[2:])
    app = QApplication(sys.argv)
    app.setOrganizationName("skip-pet")
    app.setApplicationName("sukuna-pet")
    app.setApplicationDisplayName("宿傩桌宠")
    window = PetWindow()
    window.show()
    return app.exec()
