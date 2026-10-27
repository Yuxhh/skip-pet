"""Native Sukuna AI conversations, following the confirmed layout."""

from html import escape
from time import monotonic

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import (QCloseEvent, QColor, QInputMethodEvent, QKeyEvent, QPainter,
                           QPaintEvent, QPen, QPolygonF, QResizeEvent)
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
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
    closed = Signal()
    close_cancelled = Signal()

    def __init__(self, controller: ChatController, owner: QWidget | None = None) -> None:
        super().__init__(owner, Qt.WindowType.Window)
        self.controller = controller
        self._closing_requested = False
        self._allow_close = False
        self._close_deadline = 0.0
        self._close_timer = QTimer(self)
        self._close_timer.setInterval(50)
        self._close_timer.timeout.connect(self._check_close)
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
        self.new_session_button = QPushButton("＋ 新建对话")
        self.new_session_button.clicked.connect(self._new_session)
        side.addWidget(self.new_session_button)
        self.session_list = QListWidget()
        self.session_list.setAccessibleName("聊天会话")
        self.session_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.session_list.currentRowChanged.connect(self._select_session)
        side.addWidget(self.session_list, 1)
        self.delete_session_button = QPushButton("删除当前对话")
        self.delete_session_button.clicked.connect(self._delete_session)
        side.addWidget(self.delete_session_button)
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
        self.save_retry_button = QPushButton("重试保存记录")
        self.save_retry_button.clicked.connect(controller.save_all)
        actions.addWidget(self.save_retry_button)
        actions.addStretch()
        self.body_layout.addLayout(actions)
        note = QLabel("对话完整保存在本机。AI 内容请核实。")
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
        if self._closing_requested:
            return
        if self.controller.send(self.input.toPlainText()):
            self.input.clear()

    def _new_session(self) -> None:
        if self._closing_requested:
            return
        self.controller.new_session()
        self.input.clear()

    def _select_session(self, row: int) -> None:
        if self._closing_requested:
            return
        item = self.session_list.item(row)
        if item is not None and self.controller.select_session(str(item.data(Qt.ItemDataRole.UserRole))):
            self.input.clear()

    def _delete_session(self) -> None:
        if self._closing_requested:
            return
        session_id = self.controller.session.id
        dialog = QMessageBox(QMessageBox.Icon.Warning, "删除对话", "删除当前对话的全部本机记录？此操作无法撤销。", parent=self)
        delete = dialog.addButton("删除", QMessageBox.ButtonRole.DestructiveRole)
        cancel = dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        dialog.setDefaultButton(cancel)
        dialog.exec()
        if dialog.clickedButton() is delete:
            self.controller.delete_session(session_id)
            self.input.clear()
        dialog.deleteLater()

    def _refresh_sessions(self) -> None:
        rows = [(s.id, (s.messages[0].content[:22].replace("\n", " ") if s.messages else "新对话"))
                for s in self.controller.sessions]
        current = [(self.session_list.item(i).data(Qt.ItemDataRole.UserRole), self.session_list.item(i).text())
                   for i in range(self.session_list.count())]
        self.session_list.blockSignals(True)
        if current != rows:
            self.session_list.clear()
            for session_id, title in rows:
                item = QListWidgetItem(title)
                item.setData(Qt.ItemDataRole.UserRole, session_id)
                item.setToolTip(title)
                self.session_list.addItem(item)
        for row, (session_id, _) in enumerate(rows):
            if session_id == self.controller.session.id:
                self.session_list.setCurrentRow(row)
                break
        self.session_list.blockSignals(False)

    def _send_or_stop(self) -> None:
        if self.controller.busy:
            self.controller.stop()
        else:
            self._send()

    def _buttons(self) -> None:
        self.send_button.setText("停止" if self.controller.busy else "发送")
        self.send_button.setEnabled(not self._closing_requested and
                                    (self.controller.busy or bool(self.input.toPlainText().strip())))
        for widget in (self.input, self.sidebar, self.retry_button, self.save_retry_button):
            widget.setEnabled(not self._closing_requested)

    def _refresh(self) -> None:
        self._refresh_sessions()
        has_messages = bool(self.controller.session.messages)
        self.welcome.setVisible(not has_messages)
        self.transcript.setVisible(has_messages)
        self.body_layout.setStretch(0, 0 if has_messages else 1)
        self.body_layout.setStretch(self.body_layout.count() - 1, 0 if has_messages else 1)
        notice = "\n".join(text for text in (self.controller.notice, self.controller.storage_notice) if text)
        self.status.setText(notice)
        self.status.setVisible(bool(notice))
        self.retry_button.setVisible(self.controller.can_retry)
        self.configure_button.setVisible(self.controller.needs_settings)
        self.save_retry_button.setVisible(self.controller.store is not None and self.controller.store.failed)
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
        if self._closing_requested:
            event.ignore()
            return
        self.controller.stop()
        if self.controller.unsaved and not self._allow_close:
            event.ignore()
            self._closing_requested = True
            self._close_deadline = monotonic() + 3.0
            self._close_timer.start()
            self._buttons()
            return
        self._allow_close = False
        self._render_timer.stop()
        super().closeEvent(event)
        if event.isAccepted():
            self.closed.emit()

    def _check_close(self) -> None:
        store = self.controller.store
        if not self.controller.unsaved:
            self._finish_close()
            return
        if store is not None and not store.failed and monotonic() < self._close_deadline:
            return
        self._close_timer.stop()
        dialog = QMessageBox(QMessageBox.Icon.Warning, "记录尚未保存",
                             "部分聊天记录尚未保存，关闭后可能丢失未写入内容。请选择重试保存、取消关闭或确认关闭。", parent=self)
        retry = dialog.addButton("重试保存", QMessageBox.ButtonRole.AcceptRole)
        cancel = dialog.addButton("取消关闭", QMessageBox.ButtonRole.RejectRole)
        discard = dialog.addButton("确认关闭", QMessageBox.ButtonRole.DestructiveRole)
        dialog.setDefaultButton(cancel)
        dialog.exec()
        clicked = dialog.clickedButton()
        dialog.deleteLater()
        if clicked is discard:
            self._finish_close()
        elif clicked is retry:
            self.controller.save_all()
            self._close_deadline = monotonic() + 3.0
            self._close_timer.start()
        else:
            self._closing_requested = False
            self._refresh()
            self.close_cancelled.emit()

    def _finish_close(self) -> None:
        self._close_timer.stop()
        self._closing_requested = False
        self._allow_close = True
        self._buttons()
        self.close()

    def resizeEvent(self, event: QResizeEvent) -> None:
        if self.width() < 800:
            self.sidebar.hide()
        super().resizeEvent(event)
