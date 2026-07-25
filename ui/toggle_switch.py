from PyQt6.QtCore import QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget

TRACK_ON = QColor(60, 180, 90)
TRACK_OFF = QColor(120, 124, 132)


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._handle_pos = 1.0 if checked else 0.0
        self.setFixedSize(46, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"handlePos", self)
        self._anim.setDuration(150)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, emit: bool = True):
        if checked == self._checked:
            return
        self._checked = checked
        self._anim.stop()
        self._anim.setStartValue(self._handle_pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()
        if emit:
            self.toggled.emit(checked)

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)

    def _get_handle_pos(self) -> float:
        return self._handle_pos

    def _set_handle_pos(self, value: float):
        self._handle_pos = value
        self.update()

    handlePos = pyqtProperty(float, _get_handle_pos, _set_handle_pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(TRACK_ON if self._checked else TRACK_OFF)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        margin = 2
        diameter = rect.height() - margin * 2
        x = margin + self._handle_pos * (rect.width() - diameter - margin * 2)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QRectF(x, margin, diameter, diameter))
