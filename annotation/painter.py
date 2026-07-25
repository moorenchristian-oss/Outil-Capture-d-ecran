import math
from enum import Enum, auto

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

DEFAULT_STROKE_COLOR = QColor(220, 30, 30)
DEFAULT_HIGHLIGHTER_COLOR = QColor(255, 235, 0, 90)

# (épaisseur trait, épaisseur surligneur, rayon gomme) par taille choisie.
SIZE_PRESETS = {
    "fin": (2, 10, 8),
    "moyen": (4, 18, 14),
    "epais": (8, 26, 22),
}

UNDO_STACK_LIMIT = 20


class AnnotationTool(Enum):
    NONE = auto()
    PEN = auto()
    HIGHLIGHTER = auto()
    ERASER = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()
    LINE = auto()
    ARROW = auto()


SHAPE_TOOLS = (AnnotationTool.RECTANGLE, AnnotationTool.ELLIPSE, AnnotationTool.LINE, AnnotationTool.ARROW)


class AnnotationCanvas(QWidget):
    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.tool = AnnotationTool.NONE
        self._drawing = False
        self._last_point = QPoint()
        self._start_point = QPoint()
        self._current_point = QPoint()

        self._stroke_color = QColor(DEFAULT_STROKE_COLOR)
        self._highlighter_color = QColor(DEFAULT_HIGHLIGHTER_COLOR)
        self._size = "moyen"
        self._undo_stack: list[QPixmap] = []

        self.set_image(image)

    def set_image(self, image: QImage):
        self._original = QPixmap.fromImage(image)
        self._pixmap = self._original.copy()
        self._undo_stack.clear()
        self.setFixedSize(self._pixmap.size())
        self.update()

    def set_tool(self, tool: AnnotationTool):
        self.tool = tool

    def set_stroke_color(self, color: QColor):
        self._stroke_color = QColor(color)

    def set_highlighter_color(self, color: QColor):
        self._highlighter_color = QColor(color)

    def set_size(self, preset: str):
        if preset in SIZE_PRESETS:
            self._size = preset

    def _pen_width(self) -> int:
        return SIZE_PRESETS[self._size][0]

    def _highlighter_width(self) -> int:
        return SIZE_PRESETS[self._size][1]

    def _eraser_radius(self) -> int:
        return SIZE_PRESETS[self._size][2]

    def result_image(self) -> QImage:
        return self._pixmap.toImage()

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def undo(self):
        if not self._undo_stack:
            return
        self._pixmap = self._undo_stack.pop()
        self.update()

    def _push_undo_snapshot(self):
        self._undo_stack.append(self._pixmap.copy())
        if len(self._undo_stack) > UNDO_STACK_LIMIT:
            self._undo_stack.pop(0)

    def mousePressEvent(self, event):
        if self.tool == AnnotationTool.NONE:
            return
        self._push_undo_snapshot()
        self._drawing = True
        self._last_point = event.pos()
        self._start_point = event.pos()
        self._current_point = event.pos()
        if self.tool == AnnotationTool.ERASER:
            self._erase_at(event.pos())

    def mouseMoveEvent(self, event):
        if not self._drawing:
            return
        if self.tool in (AnnotationTool.PEN, AnnotationTool.HIGHLIGHTER):
            self._draw_line(self._last_point, event.pos())
            self._last_point = event.pos()
        elif self.tool == AnnotationTool.ERASER:
            self._erase_at(event.pos())
        elif self.tool in SHAPE_TOOLS:
            self._current_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if not self._drawing:
            return
        self._drawing = False
        if self.tool in SHAPE_TOOLS:
            rect = QRect(self._start_point, event.pos()).normalized()
            self._commit_shape(rect, event.pos())
        self.update()

    def _draw_line(self, p1: QPoint, p2: QPoint):
        painter = QPainter(self._pixmap)
        if self.tool == AnnotationTool.HIGHLIGHTER:
            pen = QPen(
                self._highlighter_color,
                self._highlighter_width(),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        else:
            pen = QPen(
                self._stroke_color, self._pen_width(), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap
            )
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        self.update()

    def _erase_at(self, pos: QPoint):
        radius = self._eraser_radius()
        painter = QPainter(self._pixmap)
        source_rect = QRect(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2)
        painter.drawPixmap(source_rect, self._original, source_rect)
        painter.end()
        self.update()

    def _draw_arrowhead(self, painter: QPainter, p1: QPoint, p2: QPoint):
        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        head_len = 10 + self._pen_width() * 2
        head_angle = math.radians(28)
        left = QPoint(
            int(p2.x() - head_len * math.cos(angle - head_angle)),
            int(p2.y() - head_len * math.sin(angle - head_angle)),
        )
        right = QPoint(
            int(p2.x() - head_len * math.cos(angle + head_angle)),
            int(p2.y() - head_len * math.sin(angle + head_angle)),
        )
        painter.setBrush(self._stroke_color)
        painter.drawPolygon(p2, left, right)

    def _commit_shape(self, rect: QRect, end_point: QPoint):
        painter = QPainter(self._pixmap)
        pen = QPen(self._stroke_color, self._pen_width())
        painter.setPen(pen)
        if self.tool == AnnotationTool.ELLIPSE:
            painter.drawEllipse(rect)
        elif self.tool == AnnotationTool.RECTANGLE:
            painter.drawRect(rect)
        elif self.tool == AnnotationTool.LINE:
            painter.drawLine(self._start_point, end_point)
        elif self.tool == AnnotationTool.ARROW:
            painter.drawLine(self._start_point, end_point)
            self._draw_arrowhead(painter, self._start_point, end_point)
        painter.end()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._pixmap)
        if self._drawing and self.tool in SHAPE_TOOLS:
            painter.setPen(QPen(self._stroke_color, 2, Qt.PenStyle.DashLine))
            if self.tool == AnnotationTool.ELLIPSE:
                rect = QRect(self._start_point, self._current_point).normalized()
                painter.drawEllipse(rect)
            elif self.tool == AnnotationTool.RECTANGLE:
                rect = QRect(self._start_point, self._current_point).normalized()
                painter.drawRect(rect)
            elif self.tool in (AnnotationTool.LINE, AnnotationTool.ARROW):
                painter.drawLine(self._start_point, self._current_point)
