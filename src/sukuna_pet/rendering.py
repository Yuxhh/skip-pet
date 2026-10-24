"""Draw the approved blank-sclera asset and clipped eyes without body motion."""

from importlib.resources import files

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen

from .playback import PetView


SOURCE_BOUNDS = QRectF(201, 47, 1016, 991)
DISPLAY_HEIGHT = 247
DISPLAY_WIDTH = round(DISPLAY_HEIGHT * SOURCE_BOUNDS.width() / SOURCE_BOUNDS.height())


def _socket(screen_left: bool) -> QPainterPath:
    path = QPainterPath()
    if screen_left:
        path.moveTo(600, 469)
        path.cubicTo(623, 471, 646, 472, 654, 476)
        path.cubicTo(663, 480, 666, 484, 664, 486)
        path.cubicTo(648, 489, 630, 490, 621, 486)
        path.cubicTo(611, 480, 605, 475, 600, 469)
    else:
        path.moveTo(776, 467)
        path.cubicTo(793, 460, 819, 455, 838, 451)
        path.cubicTo(833, 465, 829, 471, 817, 474)
        path.cubicTo(801, 479, 788, 480, 774, 478)
        path.lineTo(776, 467)
    path.closeSubpath()
    return path


class CharacterRenderer:
    def __init__(self) -> None:
        asset = files("sukuna_pet").joinpath("assets/sukuna-eye-base-v3.png")
        self._base = QImage.fromData(asset.read_bytes())
        if self._base.isNull():
            raise RuntimeError("Cannot load the bundled character asset")

    def render(self, view: PetView) -> QImage:
        """Return a source-resolution transparent frame for this drawable view."""
        frame = self._base.copy()
        painter = QPainter(frame)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for index, centre in enumerate((view.right_eye, view.left_eye)):
            painter.save()
            painter.setClipPath(_socket(index == 0))
            cx, cy = centre
            painter.setPen(QPen(QColor("#25181a"), 2))
            painter.setBrush(QColor("#652d2d"))
            painter.drawEllipse(QPointF(cx, cy), 15, 17)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#130e11"))
            painter.drawEllipse(QPointF(cx, cy - 1), 7, 11)
            painter.setBrush(QColor("#dfcac7"))
            painter.drawEllipse(QPointF(cx - 4, cy - 5), 2, 3)
            if view.eyelid_closure > 0:
                _eyelid(painter, index == 0, view.eyelid_closure)
            painter.restore()
        painter.end()
        return frame


def _eyelid(painter: QPainter, screen_left: bool, closure: float) -> None:
    if screen_left:
        xl, xr = 590, 680
        yl, yr = 463 + closure * 33, 473 + closure * 33
        skin = "#a19595"
    else:
        xl, xr = 765, 847
        yl, yr = 466 + closure * 25, 447 + closure * 30
        skin = "#ecdcd4"
    lid = QPainterPath(QPointF(xl, 430))
    lid.lineTo(xr, 430)
    lid.lineTo(xr, yr)
    lid.lineTo(xl, yl)
    lid.closeSubpath()
    painter.fillPath(lid, QColor(skin))
    painter.setPen(QPen(QColor("#251d21"), 3))
    painter.drawLine(QPointF(xl, yl), QPointF(xr, yr))
