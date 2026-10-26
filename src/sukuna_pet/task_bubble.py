"""Input-transparent, independently positioned native task bubble."""

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QLabel, QWidget


def bubble_position(character: QRect, area: QRect, width: int, height: int) -> QPoint:
    x = character.center().x() - width // 2
    y = character.top() - height - 10
    if y < area.top():
        y = character.bottom() + 10
    return QPoint(max(area.left(), min(x, area.right() - width + 1)),
                  max(area.top(), min(y, area.bottom() - height + 1)))


class TaskBubble(QLabel):
    def __init__(self, owner: QWidget) -> None:
        super().__init__(owner, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus
                         | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setMargin(12)
        self.setStyleSheet("QLabel { color: #f7ede2; background: #261e21; border: 1px solid #ab7770;"
                           " border-radius: 12px; font-size: 14px; }")

    def present(self, text: str, character: QRect, area: QRect) -> None:
        if not text:
            self.hide()
            return
        self.setFixedWidth(min(300, max(1, area.width())))
        if self.text() != text:
            self.setText(text)
            self.adjustSize()
        self.setFixedHeight(min(area.height(), max(44, self.heightForWidth(self.width()))))
        self.move(bubble_position(character, area, self.width(), self.height()))
        self.show()
