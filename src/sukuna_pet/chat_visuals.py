"""Native vector artwork transcribed from the author-confirmed #45 prototype."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPaintEvent, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


SCROLLBAR_STYLE = """
    QScrollBar:vertical { width: 8px; background: #191518; margin: 0; }
    QScrollBar::handle:vertical { background: #60404b; min-height: 24px; border-radius: 4px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""


def paint_sigil(painter: QPainter, area: QRectF) -> None:
    painter.save()
    painter.translate(area.x(), area.y())
    painter.scale(area.width() / 50, area.height() / 60)
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
    painter.restore()


class Sigil(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(34, 38)
        self.setAccessibleName("宿傩标记")

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#341d23"))
        painter.drawRoundedRect(QRectF(self.rect()), 9, 9)
        paint_sigil(painter, QRectF(4.5, 4.5, 25, 29))


class Shrine(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(166)
        self.setAccessibleName("伏魔御厨子线稿")

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.save()
        width = min(330, self.width())
        painter.translate((self.width() - width) / 2, 0)
        painter.scale(width / 400, .82)
        painter.setPen(QPen(QColor("#44282f"), 1))
        for x, y, length in ((35, 182, 330), (62, 168, 276), (86, 152, 228), (107, 130, 186)):
            painter.drawLine(x, y, x + length, y)
        for x in (118, 127, 273, 282):
            painter.drawLine(x, 14, x, 130)
        painter.drawPolyline(QPolygonF([QPointF(93, 94), QPointF(200, 34), QPointF(307, 94), QPointF(93, 94)]))
        roof = QPainterPath(QPointF(101, 94))
        roof.quadTo(171, 73, 200, 34)
        roof.quadTo(228, 73, 300, 94)
        painter.drawPath(roof)
        painter.drawLine(148, 75, 252, 75)
        painter.drawLine(123, 105, 277, 105)
        for x in (70, 330):
            painter.drawLine(x, 54, x, 153)
            painter.drawPolyline(QPolygonF([QPointF(x - 11, 123), QPointF(x, 114),
                                           QPointF(x + 11, 123), QPointF(x - 11, 123)]))
        painter.restore()
        box = QRectF(self.width() / 2 - 31, 86, 62, 62)
        painter.setPen(QPen(QColor("#4b2d35"), 1))
        painter.setBrush(QColor("#151215"))
        painter.drawRoundedRect(box, 15, 15)
        paint_sigil(painter, QRectF(box.x() + 11, box.y() + 8, 40, 46))
