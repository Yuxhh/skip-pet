"""The single native settings window, using the pet's existing operations."""

from importlib import metadata
from pathlib import Path
import tomllib
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QMessageBox, QPushButton, QScrollArea,
                               QStackedWidget, QVBoxLayout, QWidget)

from .connection_test import ConnectionResult, ConnectionTester
from .chat_visuals import SCROLLBAR_STYLE, Sigil
from .settings import DISPLAY_SIZES, Mode

if TYPE_CHECKING:
    from .desktop import PetWindow


def product_version() -> str:
    package = Path(__file__).parent
    # The frozen app embeds the same project metadata used by its installer.
    for path in (package / "pyproject.toml", package.parents[1] / "pyproject.toml"):
        if path.is_file():
            with path.open("rb") as stream:
                return str(tomllib.load(stream)["project"]["version"])
    try:
        return metadata.version("sukuna-pet")
    except metadata.PackageNotFoundError:
        return "版本信息不可用"


class SettingsWindow(QDialog):
    def __init__(self, owner: "PetWindow") -> None:
        super().__init__(owner)
        self._owner = owner
        self._credentials = owner.credentials
        self._tester = ConnectionTester(self)
        self._tester.completed.connect(self._tested)
        self._tester.changed.connect(self._test_state)
        self.setWindowTitle("桌宠设置 · Sukuna AI")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setMinimumSize(560, 440)
        self.resize(680, 480)
        self.move(self.screen().availableGeometry().center() - self.rect().center())
        self.setStyleSheet("""
            QDialog, QWidget { background: #191518; color: #eee9e5;
                font-family: 'Microsoft YaHei', 'Segoe UI'; font-size: 13px; }
            QLabel#brand { font-size: 19px; font-weight: 600; }
            QLabel#heading { font-size: 17px; font-weight: 600; }
            QLabel { background: transparent; }
            QListWidget { background: #171416; border: 0; border-right: 1px solid #302328; }
            QListWidget::item { padding: 12px 10px; margin: 2px 6px; border-radius: 6px; }
            QListWidget::item:selected { background: #342026; color: #ef9ba5; }
            QLineEdit, QComboBox { background: #241c22; border: 1px solid #60434e;
                padding: 9px; border-radius: 7px; selection-background-color: #bd3543; }
            QPushButton { background: #342026; border: 1px solid #69404a;
                padding: 8px 14px; border-radius: 7px; }
            QPushButton:hover { background: #532b35; }
            QPushButton:disabled { color: #9d8c94; background: #241c22; }
            QPushButton:focus, QLineEdit:focus, QComboBox:focus { border: 1px solid #e37d87; }
            QScrollArea { border: 0; }
        """ + SCROLLBAR_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 18, 24, 16)
        header_layout.setSpacing(12)
        header_layout.addWidget(Sigil())
        brand = QLabel("Sukuna AI  /  桌宠设置")
        brand.setObjectName("brand")
        header_layout.addWidget(brand, 1)
        layout.addWidget(header)
        body = QHBoxLayout()
        body.setSpacing(0)
        self.navigation = QListWidget()
        self.navigation.setAccessibleName("设置分组")
        self.navigation.addItems(["桌宠", "任务联动", "AI 对话", "关于"])
        self.navigation.setFixedWidth(140)
        body.addWidget(self.navigation)
        self.pages = QStackedWidget()
        body.addWidget(self.pages, 1)
        layout.addLayout(body, 1)
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self._build_pet()
        self._build_bridge()
        self._build_ai()
        self._build_about()
        self.navigation.setCurrentRow(0)
        owner.preferences_changed.connect(self.refresh)
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self.refresh)
        self.refresh()

    def _page(self, title: str) -> QVBoxLayout:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("heading")
        layout.addWidget(heading)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        self.pages.addWidget(scroll)
        return layout

    def _build_pet(self) -> None:
        layout = self._page("桌宠")
        mode_label = QLabel("跳动模式")
        layout.addWidget(mode_label)
        self.mode = QComboBox()
        mode_label.setBuddy(self.mode)
        for value, label in (("click", "点击跳动"), ("always", "持续跳动"), ("task", "任务联动")):
            self.mode.addItem(label, value)
        self.mode.currentIndexChanged.connect(self._mode_selected)
        layout.addWidget(self.mode)
        size_label = QLabel("角色大小")
        layout.addWidget(size_label)
        self.size_choice = QComboBox()
        size_label.setBuddy(self.size_choice)
        for label, height in zip(("小", "中", "大"), DISPLAY_SIZES):
            self.size_choice.addItem(f"{label} · {height}px", height)
        self.size_choice.currentIndexChanged.connect(lambda: self._owner.select_size(self.size_choice.currentData()))
        layout.addWidget(self.size_choice)
        note = QLabel("修改立即生效并保存，与右键快捷菜单同步。")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

    def _mode_selected(self) -> None:
        mode: Mode = self.mode.currentData()
        self._owner.select_mode(mode)

    def _build_bridge(self) -> None:
        layout = self._page("任务联动")
        self.bridge_status = QLabel()
        self.bridge_status.setWordWrap(True)
        layout.addWidget(self.bridge_status)
        self.bridge_toggle = QPushButton()
        self.bridge_toggle.clicked.connect(self._toggle_bridge)
        layout.addWidget(self.bridge_toggle)
        self.bridge_maintain = QPushButton("检查并修复已有接入")
        self.bridge_maintain.clicked.connect(self._maintain_bridge)
        layout.addWidget(self.bridge_maintain)
        note = QLabel("沿用已配置的 DeepSeek Harness 接入。启用前会预检并确认安装范围。")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

    def _toggle_bridge(self) -> None:
        bridge = self._owner.bridge_controller
        if bridge is not None:
            if bridge.enabled:
                bridge.disable()
            else:
                bridge.prepare()
        self.refresh()

    def _maintain_bridge(self) -> None:
        bridge = self._owner.bridge_controller
        if bridge is not None:
            bridge.start()
        self.refresh()

    def _build_ai(self) -> None:
        layout = self._page("AI 对话")
        self.key_status = QLabel()
        self.key_status.setWordWrap(True)
        layout.addWidget(self.key_status)
        label = QLabel("DeepSeek API Key")
        layout.addWidget(label)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("输入新 Key；空白保留现有值")
        self.key_input.setMaxLength(1280)
        self.key_input.setInputMethodHints(Qt.InputMethodHint.ImhSensitiveData
                                          | Qt.InputMethodHint.ImhNoPredictiveText)
        label.setBuddy(self.key_input)
        layout.addWidget(self.key_input)
        row = QHBoxLayout()
        self.save_key = QPushButton("保存")
        self.save_key.clicked.connect(self._save_key)
        row.addWidget(self.save_key)
        self.cancel_key = QPushButton("取消修改")
        self.cancel_key.clicked.connect(self._discard_draft)
        row.addWidget(self.cancel_key)
        self.clear_key = QPushButton("清除密钥")
        self.clear_key.clicked.connect(self._clear_key)
        row.addWidget(self.clear_key)
        layout.addLayout(row)
        self.key_notice = QLabel()
        self.key_notice.setWordWrap(True)
        layout.addWidget(self.key_notice)
        note = QLabel("deepseek-flash · 关闭思考\n测试会发送一次短请求，可能消耗 API 用量。"
                      "使用输入框中的待测 Key；空白时使用当前 Key。")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.test_key = QPushButton("测试连接（可能消耗额度）")
        self.test_key.clicked.connect(self._test_key)
        layout.addWidget(self.test_key)
        self.test_result = QLabel()
        self.test_result.setWordWrap(True)
        layout.addWidget(self.test_result)
        layout.addStretch()

    def _build_about(self) -> None:
        layout = self._page("关于")
        text = QLabel(f"宿傩桌宠 · Sukuna AI\n版本 {product_version()}\n\n"
                      "Python — Python Software Foundation\n"
                      "PySide6 / Qt / shiboken6 — The Qt Company Ltd. 及贡献者，LGPL 3.0\n"
                      "dsh-pet 参考实现 — Copyright (c) 2026 Merzlin，MIT\n\n"
                      "许可证全文随安装包附于 THIRD-PARTY-LICENSES。")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text)
        layout.addStretch()

    def refresh(self) -> None:
        for combo, value in ((self.mode, self._owner.pet_mode), (self.size_choice, self._owner.height())):
            blocked = combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(value))
            combo.blockSignals(blocked)
        bridge = self._owner.bridge_controller
        self.bridge_toggle.setEnabled(bridge is not None and not bridge.busy)
        self.bridge_maintain.setEnabled(bridge is not None and bridge.enabled and not bridge.busy)
        self.bridge_toggle.setText("关闭 DeepSeek 接入" if bridge and bridge.enabled else "启用 DeepSeek 接入")
        state = ("维护中，请稍候" if bridge.busy else "已启用" if bridge.enabled else "未启用") if bridge else "未配置"
        summary = bridge.summary.text if bridge and bridge.enabled else ""
        self.bridge_status.setText(f"DeepSeek Harness 接入：{state}" + (f"\n{summary}" if summary else ""))
        self.key_status.setText("Key 已安全保存" if self._credentials.safely_saved else "Key 未安全保存")
        self.key_notice.setText(self._credentials.notice)

    def _save_key(self) -> None:
        self._tester.invalidate()
        self.test_result.clear()
        self._credentials.save(self.key_input.text())
        self.key_input.setText("")
        self.refresh()

    def _discard_draft(self) -> None:
        self.key_input.setText("")
        self._tester.invalidate()
        self.test_result.clear()

    def _clear_key(self) -> None:
        self._discard_draft()
        self._credentials.clear()
        self.refresh()

    def _test_key(self) -> None:
        if self._tester.busy:
            return
        key = self.key_input.text().strip() or self._credentials.snapshot()
        if not key:
            self.test_result.setText("请先输入或保存 DeepSeek API Key。")
            return
        answer = QMessageBox.question(self, "测试连接", "发送一次短请求可能消耗 API 用量，是否继续？",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.test_result.setText("正在测试本次连接…")
            self._tester.start(key)

    def _test_state(self) -> None:
        self.test_key.setEnabled(not self._tester.busy)

    def _tested(self, result: ConnectionResult) -> None:
        self.test_result.setText(result.message)

    def open_page(self, name: str = "桌宠") -> None:
        self.navigation.setCurrentRow(["桌宠", "任务联动", "AI 对话", "关于"].index(name))
        self.test_result.clear()
        self.refresh()
        self._timer.start()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def done(self, result: int) -> None:
        # Escape calls reject/done rather than closeEvent.
        self._discard_draft()
        self._timer.stop()
        super().done(result)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._discard_draft()
        self._timer.stop()
        super().closeEvent(event)
