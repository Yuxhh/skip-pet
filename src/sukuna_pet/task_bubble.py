"""Input-transparent, independently positioned native task bubble."""

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
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
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setMargin(12)
        self.setStyleSheet("QLabel { color: #f7ede2; background: transparent; border: none;"
                           " font-size: 14px; }")

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ab7770"), 1))
        painter.setBrush(QColor("#261e21"))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 16, 16)
        painter.end()
        super().paintEvent(event)

    def present(self, text: str, character: QRect, area: QRect) -> None:
        if not text:
            self.hide()
            return
        if self.text() != text:
            self.setText(text)
        self.ensurePolished()
        text_width = self.fontMetrics().size(Qt.TextFlag.TextExpandTabs, text).width()
        padding = 2 * (self.margin() + self.frameWidth())
        self.setFixedWidth(min(300, max(1, area.width()), max(44, text_width + padding)))
        self.setMinimumHeight(0)
        self.setFixedHeight(min(area.height(), max(44, self.heightForWidth(self.width()))))
        self.move(bubble_position(character, area, self.width(), self.height()))
        self.show()
