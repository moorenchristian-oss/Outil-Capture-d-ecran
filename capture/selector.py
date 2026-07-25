from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget


class FocusAnchor(QWidget):
    """Fenêtre invisible (sans décoration, fond translucide, rien n'est peint) affichée
    juste le temps d'un appel au portail Wayland. Sous Wayland, setWindowOpacity() sur la
    fenêtre principale ne fonctionne pas (non supporté par le plugin QPA) et masquer
    complètement l'application (hide()) fait que plus aucune fenêtre n'a le focus — le
    portail refuse alors d'afficher sa boîte de dialogue de permission ("Only the focused
    app is allowed to show a system access dialog"). Cette fenêtre reste mappée/focalisable
    sans jamais rien afficher à l'écran, donc sans apparaître dans la capture."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        virtual_geometry = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual_geometry)

    def finish(self):
        self.hide()
        self.close()


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
        self._finished = False

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
        # Reste mappée/focalisée (juste invisible) au lieu de hide()+close() ici :
        # le portail Wayland refuse d'afficher sa boîte de dialogue de permission si
        # plus aucune fenêtre de l'application n'a le focus au moment de la capture.
        # L'appelant doit appeler finish() une fois la capture terminée.
        self._finished = True
        self.update()
        if valid:
            self.region_selected.emit(selected_rect)
        else:
            self.finish()
            self.cancelled.emit()

    def finish(self):
        self.hide()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.finish()
            self.cancelled.emit()

    def paintEvent(self, event):
        if self._finished:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        if not self._current_rect.isNull():
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawRect(self._current_rect)
