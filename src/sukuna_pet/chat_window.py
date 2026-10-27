"""Native single-session Sukuna AI window, following the confirmed layout."""

from html import escape

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import (QCloseEvent, QColor, QInputMethodEvent, QKeyEvent, QPainter,
                           QPaintEvent, QPen, QPolygonF, QResizeEvent)
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QTextBrowser, QVBoxLayout, QWidget)

from .chat_controller import ChatController
from .connection_test import MODEL


class _Shrine(QWidget):
    """Code-native line art and author-confirmed sigil from the HTML prototype."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(142)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2 - 165, 0)
        painter.scale(.825, .68)
        painter.setPen(QPen(QColor("#52303a"), 1.2))
        for x, y, width in ((35, 182, 330), (62, 168, 276), (86, 152, 228), (107, 130, 186)):
            painter.drawLine(x, y, x + width, y)
        for x in (118, 127, 273, 282):
            painter.drawLine(x, 14, x, 130)
        painter.drawPolyline(QPolygonF([QPointF(93, 94), QPointF(200, 34), QPointF(307, 94), QPointF(93, 94)]))
        painter.drawLine(148, 75, 252, 75)
        painter.drawLine(123, 105, 277, 105)
        painter.translate(175, 92)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d45966"))
        for coordinates in (
            ((22, 4), (28, 4), (27, 18), (23, 18)),
            ((8, 8), (16, 12), (19, 23), (11, 18)),
            ((42, 8), (34, 12), (31, 23), (39, 18)),
            ((3, 22), (20, 27), (21, 32), (6, 27)),
            ((47, 22), (30, 27), (29, 32), (44, 27)),
            ((5, 32), (20, 37), (21, 42), (8, 37)),
            ((45, 32), (30, 37), (29, 42), (42, 37)),
            ((22, 25), (28, 25), (27, 48), (25, 53), (23, 48)),
            ((12, 44), (19, 47), (21, 53), (15, 50)),
            ((38, 44), (31, 47), (29, 53), (35, 50)),
        ):
            painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in coordinates]))


class ChatInput(QPlainTextEdit):
    submitted = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._composing = False
        self.setPlaceholderText("我想要问些什么…")
        self.setAccessibleName("输入消息")
        self.setMinimumHeight(52)
        self.setMaximumHeight(160)
        self.textChanged.connect(self._fit)
        self._fit()

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:
        self._composing = bool(event.preeditString())
        super().inputMethodEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not self._composing
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.submitted.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _fit(self) -> None:
        lines = max(self.document().size().height(), float(self.blockCount()))
        self.setFixedHeight(max(52, min(160, int(lines * self.fontMetrics().lineSpacing() + 16))))


class ChatWindow(QWidget):
    settings_requested = Signal()

    def __init__(self, controller: ChatController, owner: QWidget | None = None) -> None:
        super().__init__(owner, Qt.WindowType.Window)
        self.controller = controller
        self.setWindowTitle("Sukuna AI · 宿傩 AI 对话")
        self.setMinimumSize(560, 480)
        self.resize(1040, 760)
        self.setStyleSheet("""
            QWidget { background: #111113; color: #eee9e5;
                font-family: 'Segoe UI', 'Microsoft YaHei'; font-size: 14px; }
            QWidget#sidebar { background: #171416; border-right: 1px solid #302328; }
            QWidget#header { border-bottom: 1px solid #302328; }
            QLabel { background: transparent; border: 0; }
            QLabel#brand { font-size: 22px; font-weight: 600; color: #edcbd0; }
            QLabel#hero { font-size: 25px; font-weight: 600; }
            QLabel#muted { color: #b3a2aa; font-size: 12px; }
            QPushButton { border: 0; padding: 9px 13px; border-radius: 7px; background: #302128; }
            QPushButton:hover { background: #49303a; }
            QPushButton:disabled { color: #88777e; background: #261e22; }
            QPushButton#send { background: #bd3543; color: #fff1f0; min-width: 46px; }
            QPushButton#send:disabled { background: #542831; color: #ae8d95; }
            QWidget#composer { background: #1d191c; border: 1px solid #60404b; border-radius: 13px; }
            QPlainTextEdit { border: 0; background: #1d191c; padding: 3px; selection-background-color: #70404b; }
            QTextBrowser { border: 0; background: transparent; selection-background-color: #70404b; }
            QScrollBar:vertical { width: 9px; background: #191518; }
            QScrollBar::handle:vertical { background: #60404b; min-height: 24px; border-radius: 4px; }
        """)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(210)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(20, 26, 20, 20)
        brand = QLabel("◆  Sukuna AI")
        brand.setObjectName("brand")
        side.addWidget(brand)
        side.addSpacing(28)
        side.addWidget(QLabel("当前对话"))
        self.session_title = QLabel("新对话")
        self.session_title.setWordWrap(True)
        side.addWidget(self.session_title)
        side.addStretch()
        foot = QLabel("宿傩 · 伏魔御厨子\nMALEVOLENT SHRINE")
        foot.setObjectName("muted")
        side.addWidget(foot)
        settings = QPushButton("桌宠设置")
        settings.clicked.connect(self.settings_requested)
        side.addWidget(settings)
        root.addWidget(self.sidebar)
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(74)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 10, 24, 10)
        titles = QVBoxLayout()
        self.title = QLabel("新对话")
        self.model = QLabel(f"DeepSeek  /  {MODEL}")
        self.model.setObjectName("muted")
        titles.addWidget(self.title)
        titles.addWidget(self.model)
        header_layout.addLayout(titles, 1)
        toggle = QPushButton("◫")
        toggle.setAccessibleName("切换侧栏")
        toggle.clicked.connect(lambda: self.sidebar.setVisible(not self.sidebar.isVisible()))
        header_layout.addWidget(toggle)
        key_settings = QPushButton("设置")
        key_settings.clicked.connect(self.settings_requested)
        header_layout.addWidget(key_settings)
        main_layout.addWidget(header)
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(28, 16, 28, 20)
        self.body_layout.setSpacing(12)
        self.body_layout.addStretch(1)
        self.welcome = QWidget()
        welcome_layout = QVBoxLayout(self.welcome)
        welcome_layout.setContentsMargins(0, 0, 0, 12)
        welcome_layout.setSpacing(10)
        welcome_layout.addWidget(_Shrine())
        hero = QLabel("有什么可以帮你的吗？")
        hero.setObjectName("hero")
        hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(hero)
        subtitle = QLabel("唤来一段新的对话")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("muted")
        welcome_layout.addWidget(subtitle)
        self.body_layout.addWidget(self.welcome)
        self.transcript = QTextBrowser()
        self.transcript.setOpenLinks(False)
        self.transcript.setAccessibleName("聊天消息")
        self.body_layout.addWidget(self.transcript, 1)
        composer = QWidget()
        composer.setObjectName("composer")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(15, 12, 15, 10)
        composer_layout.setSpacing(5)
        self.input = ChatInput()
        self.input.submitted.connect(self._send)
        self.input.textChanged.connect(self._buttons)
        composer_layout.addWidget(self.input)
        controls = QHBoxLayout()
        hint = QLabel("Enter 发送 · Shift + Enter 换行")
        hint.setObjectName("muted")
        controls.addWidget(hint, 1)
        self.send_button = QPushButton("发送")
        self.send_button.setObjectName("send")
        self.send_button.clicked.connect(self._send_or_stop)
        controls.addWidget(self.send_button)
        composer_layout.addLayout(controls)
        self.body_layout.addWidget(composer)
        self.status = QLabel()
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.body_layout.addWidget(self.status)
        actions = QHBoxLayout()
        self.retry_button = QPushButton("重试 · 可能再次消耗额度")
        self.retry_button.setToolTip(controller.retry_notice)
        self.retry_button.clicked.connect(controller.retry)
        actions.addWidget(self.retry_button)
        self.configure_button = QPushButton("配置 AI 对话 Key")
        self.configure_button.clicked.connect(self.settings_requested)
        actions.addWidget(self.configure_button)
        actions.addStretch()
        self.body_layout.addLayout(actions)
        note = QLabel("本次运行内保留对话，重启不保留。AI 内容请核实。")
        note.setObjectName("muted")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body_layout.addWidget(note)
        self.body_layout.addStretch(1)
        main_layout.addWidget(body, 1)
        root.addWidget(main, 1)
        if self.width() < 800:
            self.sidebar.hide()
        self._render_timer = QTimer(self)
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(30)
        self._render_timer.timeout.connect(self._render_messages)
        controller.changed.connect(self._refresh)
        self._refresh()

    def open_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

    def _send(self) -> None:
        if self.controller.send(self.input.toPlainText()):
            self.input.clear()

    def _send_or_stop(self) -> None:
        if self.controller.busy:
            self.controller.stop()
        else:
            self._send()

    def _buttons(self) -> None:
        self.send_button.setText("停止" if self.controller.busy else "发送")
        self.send_button.setEnabled(self.controller.busy or bool(self.input.toPlainText().strip()))

    def _refresh(self) -> None:
        has_messages = bool(self.controller.session.messages)
        self.welcome.setVisible(not has_messages)
        self.transcript.setVisible(has_messages)
        self.body_layout.setStretch(0, 0 if has_messages else 1)
        self.body_layout.setStretch(self.body_layout.count() - 1, 0 if has_messages else 1)
        self.status.setText(self.controller.notice)
        self.status.setVisible(bool(self.controller.notice))
        self.retry_button.setVisible(self.controller.can_retry)
        self.configure_button.setVisible(self.controller.needs_settings)
        title = self.controller.session.messages[0].content[:22] if has_messages else "新对话"
        # User content stays plain text in both native labels and message HTML.
        for label in (self.title, self.session_title):
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setText(title.replace("\n", " "))
        self._buttons()
        if self.controller.busy:
            if not self._render_timer.isActive():
                self._render_timer.start()
        else:
            self._render_timer.stop()
            self._render_messages()

    def _render_messages(self) -> None:
        scrollbar = self.transcript.verticalScrollBar()
        old_position = scrollbar.value()
        follow = scrollbar.maximum() - old_position < 24
        parts: list[str] = []
        for message in self.controller.session.messages:
            user = message.role == "user"
            label = "你" if user else "Sukuna AI"
            state = {"complete": "", "generating": " · 正在生成…", "incomplete": " · 未完成"}[message.state]
            color = "#edcbd0" if user else "#d45966"
            content = escape(message.content).replace("\n", "<br>")
            parts.append(f'<p style="color:{color};font-size:12px;margin-top:24px"><b>{label}</b>{state}</p>'
                         f'<p style="color:#eee0e5;white-space:pre-wrap;line-height:155%">{content}</p>')
        self.transcript.setHtml("".join(parts))
        scrollbar.setValue(scrollbar.maximum() if follow else old_position)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.controller.stop()
        self._render_timer.stop()
        super().closeEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        if self.width() < 800:
            self.sidebar.hide()
        super().resizeEvent(event)
