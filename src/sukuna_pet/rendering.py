"""Frozen V5 layers and neck mesh, rendered into one fixed DPR-aware frame."""

from importlib.resources import files
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF, QTransform

from .playback import PetView
from .settings import DEFAULT_SIZE


SOURCE_BOUNDS = QRectF(90, -110, 1250, 1220)
DISPLAY_HEIGHT = DEFAULT_SIZE
DISPLAY_WIDTH = math.ceil(DISPLAY_HEIGHT * SOURCE_BOUNDS.width() / SOURCE_BOUNDS.height())


def _image(width: int = 1419, height: int = 1108) -> QImage:
    result = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    result.fill(Qt.GlobalColor.transparent)
    return result


def _path(start: tuple[float, float], commands: list[tuple[float, ...]]) -> QPainterPath:
    path = QPainterPath(QPointF(*start))
    for command in commands:
        if len(command) == 2:
            path.lineTo(command[0], command[1])
        else:
            path.cubicTo(*command)
    path.closeSubpath()
    return path


_HEAD = _path((0, 0), [
    (1419, 0), (1419, 390), (938, 390), (939, 425, 933, 476, 899, 513),
    (882, 535), (857, 592, 820, 634, 780, 652), (662, 655),
    (624, 633, 596, 604, 579, 567), (565, 544), (534, 532, 508, 507, 496, 474),
    (486, 450, 487, 424, 491, 412), (465, 390), (0, 390),
])
_FRONT = _path((454, 606), [(600, 671, 828, 663, 998, 598), (975, 757), (882, 824), (532, 823)])
_REAR = _path((454, 610), [(470, 550, 570, 500, 700, 500), (835, 500, 960, 540, 998, 600), (975, 705), (465, 710)])


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
        assets = files("sukuna_pet").joinpath("assets")
        self._base = QImage.fromData(assets.joinpath("sukuna-eye-base-v3.png").read_bytes())
        self._repair = QImage.fromData(assets.joinpath("head-neck-repair.png").read_bytes())
        rear = QImage.fromData(assets.joinpath("rear-collar-complete.png").read_bytes())
        if any(asset.isNull() for asset in (self._base, self._repair, rear)):
            raise RuntimeError("Cannot load the bundled V5 character assets")
        self._rear = _image()
        painter = QPainter(self._rear)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.setClipPath(_REAR)
        painter.drawImage(QRectF(0, 0, 1419, 1108), rear)
        painter.end()
        self._body = self._base.copy()
        painter = QPainter(self._body)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(0, 0, 1419, 660, Qt.GlobalColor.transparent)
        painter.end()
        self._front = _image()
        painter = QPainter(self._front)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipPath(_FRONT)
        painter.drawImage(0, 0, self._base)
        painter.end()

    def _head(self, view: PetView) -> QImage:
        frame = _image()
        painter = QPainter(frame)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.setClipPath(_HEAD)
        painter.drawImage(0, 0, self._base)
        for index, centre in enumerate((view.right_eye, view.left_eye)):
            painter.save()
            painter.setClipPath(_socket(index == 0), Qt.ClipOperation.IntersectClip)
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
        painter.setClipping(False)
        fade = QLinearGradient(0, 634, 0, 658)
        fade.setColorAt(0, QColor(0, 0, 0, 255))
        fade.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.fillRect(frame.rect(), fade)
        painter.end()
        joint = _image()
        painter = QPainter(joint)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.save()
        painter.setClipRect(QRectF(400, 590, 650, 200))
        painter.drawImage(QRectF(168.3, 10.25, 1118.676, 872.9496), self._repair)
        painter.restore()
        painter.drawImage(0, 0, frame)
        painter.end()
        return joint

    def render(self, view: PetView, height: int = DISPLAY_HEIGHT, dpr: float = 1) -> QImage:
        """Final image: fixed logical viewport, rasterized at the screen DPR."""
        scale = height / SOURCE_BOUNDS.height()
        width = math.ceil(SOURCE_BOUNDS.width() * scale)
        result = _image(math.ceil(width * dpr), math.ceil(height * dpr))
        result.setDevicePixelRatio(dpr)
        painter = QPainter(result)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        painter.scale(scale, scale)
        painter.translate(-SOURCE_BOUNDS.x(), -SOURCE_BOUNDS.y())
        # One outer transform for every composed layer, about the full RGBA
        # material's bottom centre (transparent margins included). Viewport and
        # display scaling stay outside it; the collar shares the same bounce.
        painter.translate(709.5, 1108)
        painter.scale(*view.bounce_scale)
        painter.translate(-709.5, -1108)
        painter.drawImage(0, 0, self._rear)
        painter.drawImage(0, 0, self._body)
        radians = math.radians(view.head_angle)
        a, b = view.head_scale * math.cos(radians), view.head_scale * math.sin(radians)
        # Uniform head pose about the local fixed neck centre; no XY offset.
        transform = QTransform(a, b, -b, a, 720 - a * 720 + b * 735, 735 - b * 720 - a * 735)
        _warp(painter, self._head(view), transform)
        painter.drawImage(0, 0, self._front)
        painter.end()
        return result


def _neck_point(x: float, y: float, transform: QTransform) -> QPointF:
    moved = transform.map(QPointF(x, y))
    u = max(0, min(1, (y - 700) / 80))
    weight = 1 - u * u * (3 - 2 * u)
    return QPointF(x + (moved.x() - x) * weight, y + (moved.y() - y) * weight)


def _warp(painter: QPainter, image: QImage, transform: QTransform) -> None:
    # Frozen 8px neck rows, 40px columns and diagonal triangulation. Expand
    # destination clips by 0.35 source pixels to cover antialiased seams.
    rows = [*range(700, 780, 8), 780, 1108]
    cols = list(range(400, 1041, 40))
    for y, bottom in zip(rows, rows[1:]):
        for x, right in zip(cols, cols[1:]):
            for source in (((x, y), (right, y), (right, bottom)),
                           ((x, y), (right, bottom), (x, bottom))):
                destination = [_neck_point(*point, transform) for point in source]
                (sx, sy), (s1, s2), (s3, s4) = source
                origin, first, second = destination
                dx, dy = origin.x(), origin.y()
                x1, y1, x2, y2 = s1 - sx, s2 - sy, s3 - sx, s4 - sy
                det = x1 * y2 - x2 * y1
                a = ((first.x() - dx) * y2 - (second.x() - dx) * y1) / det
                b = ((first.y() - dy) * y2 - (second.y() - dy) * y1) / det
                c = ((second.x() - dx) * x1 - (first.x() - dx) * x2) / det
                d = ((second.y() - dy) * x1 - (first.y() - dy) * x2) / det
                mx = sum(point.x() for point in destination) / 3
                my = sum(point.y() for point in destination) / 3
                grown = []
                for point in destination:
                    xx, yy = point.x(), point.y()
                    radius = math.hypot(xx - mx, yy - my) or 1
                    grown.append(QPointF(xx + (xx - mx) / radius * .35, yy + (yy - my) / radius * .35))
                clip = QPainterPath()
                clip.addPolygon(QPolygonF(grown))
                clip.closeSubpath()
                painter.save()
                painter.setClipPath(clip, Qt.ClipOperation.IntersectClip)
                painter.setTransform(QTransform(a, b, c, d, dx - a * sx - c * sy, dy - b * sx - d * sy), True)
                sampling = QRectF(x - 1, y - 1, right - x + 2, bottom - y + 2)
                painter.drawImage(sampling, image, sampling)
                painter.restore()
    painter.save()
    painter.setTransform(transform, True)
    painter.drawImage(QRectF(0, 0, 1419, 701), image, QRectF(0, 0, 1419, 701))
    painter.restore()


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
