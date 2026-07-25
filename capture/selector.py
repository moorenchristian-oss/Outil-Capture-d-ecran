from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget


class RegionSelectorOverlay(QWidget):
    region_selected = pyqtSignal(QRect)
    cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._origin = QPoint()
        self._current_rect = QRect()
        self._selecting = False

        virtual_geometry = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual_geometry)

    def mousePressEvent(self, event):
        self._origin = event.pos()
        self._current_rect = QRect(self._origin, self._origin)
        self._selecting = True
        self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._current_rect = QRect(self._origin, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        self._selecting = False
        valid = self._current_rect.width() > 2 and self._current_rect.height() > 2
        selected_rect = self._current_rect
        self.hide()
        self.close()
        if valid:
            self.region_selected.emit(selected_rect)
        else:
            self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        if not self._current_rect.isNull():
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawRect(self._current_rect)
