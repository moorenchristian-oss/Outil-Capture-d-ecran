from enum import Enum, auto

from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QWidget

PEN_COLOR = QColor(220, 30, 30)
HIGHLIGHTER_COLOR = QColor(255, 235, 0, 90)


class AnnotationTool(Enum):
    NONE = auto()
    PEN = auto()
    HIGHLIGHTER = auto()
    ERASER = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()


class AnnotationCanvas(QWidget):
    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.tool = AnnotationTool.NONE
        self._drawing = False
        self._last_point = QPoint()
        self._start_point = QPoint()
        self._current_point = QPoint()
        self.set_image(image)

    def set_image(self, image: QImage):
        self._original = QPixmap.fromImage(image)
        self._pixmap = self._original.copy()
        self.setFixedSize(self._pixmap.size())
        self.update()

    def set_tool(self, tool: AnnotationTool):
        self.tool = tool

    def result_image(self) -> QImage:
        return self._pixmap.toImage()

    def mousePressEvent(self, event):
        if self.tool == AnnotationTool.NONE:
            return
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
        elif self.tool in (AnnotationTool.RECTANGLE, AnnotationTool.ELLIPSE):
            self._current_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if not self._drawing:
            return
        self._drawing = False
        if self.tool in (AnnotationTool.RECTANGLE, AnnotationTool.ELLIPSE):
            rect = QRect(self._start_point, event.pos()).normalized()
            self._commit_shape(rect, ellipse=self.tool == AnnotationTool.ELLIPSE)
        self.update()

    def _draw_line(self, p1: QPoint, p2: QPoint):
        painter = QPainter(self._pixmap)
        if self.tool == AnnotationTool.HIGHLIGHTER:
            pen = QPen(HIGHLIGHTER_COLOR, 18, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        else:
            pen = QPen(PEN_COLOR, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        self.update()

    def _erase_at(self, pos: QPoint, radius: int = 14):
        painter = QPainter(self._pixmap)
        source_rect = QRect(pos.x() - radius, pos.y() - radius, radius * 2, radius * 2)
        painter.drawPixmap(source_rect, self._original, source_rect)
        painter.end()
        self.update()

    def _commit_shape(self, rect: QRect, ellipse: bool):
        painter = QPainter(self._pixmap)
        painter.setPen(QPen(PEN_COLOR, 3))
        if ellipse:
            painter.drawEllipse(rect)
        else:
            painter.drawRect(rect)
        painter.end()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._pixmap)
        if self._drawing and self.tool in (AnnotationTool.RECTANGLE, AnnotationTool.ELLIPSE):
            rect = QRect(self._start_point, self._current_point).normalized()
            painter.setPen(QPen(PEN_COLOR, 2, Qt.PenStyle.DashLine))
            if self.tool == AnnotationTool.ELLIPSE:
                painter.drawEllipse(rect)
            else:
                painter.drawRect(rect)
