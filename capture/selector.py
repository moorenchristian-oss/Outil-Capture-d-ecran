from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QGuiApplication, QPainter, QColor, QPen, QPixmap
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
    """Sélecteur de zone à la souris, affiché par-dessus une capture d'écran déjà prise.

    Sous Wayland natif (GNOME/Mutter), un rectangle semi-transparent peint sur une fenêtre
    marquée translucide (WA_TranslucentBackground) ne s'affiche pas correctement : le canal
    alpha n'est pas respecté et le résultat apparaît entièrement opaque/noir à l'écran. Pour
    contourner ce problème, l'assombrissement est pré-calculé une seule fois directement sur
    l'image (composition CPU classique, fiable quel que soit le compositeur), et la fenêtre
    reste entièrement opaque du début à la fin — aucune dépendance à la transparence de
    fenêtre. La zone en cours de sélection est révélée "en clair" à partir de l'image
    d'origine, ce qui donne le même effet visuel qu'un vrai overlay translucide."""

    region_selected = pyqtSignal(QRect)
    cancelled = pyqtSignal()

    def __init__(self, background: QPixmap):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._background = background
        self._dimmed = self._make_dimmed(background)
        self._origin = QPoint()
        self._current_rect = QRect()
        self._selecting = False
        self._finished = False

        virtual_geometry = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual_geometry)

    @staticmethod
    def _make_dimmed(pixmap: QPixmap) -> QPixmap:
        dimmed = QPixmap(pixmap.size())
        painter = QPainter(dimmed)
        painter.drawPixmap(0, 0, pixmap)
        painter.fillRect(dimmed.rect(), QColor(0, 0, 0, 120))
        painter.end()
        return dimmed

    def _to_background_rect(self, widget_rect: QRect) -> QRect:
        scale_x = self._background.width() / self.width()
        scale_y = self._background.height() / self.height()
        return QRect(
            int(widget_rect.x() * scale_x),
            int(widget_rect.y() * scale_y),
            int(widget_rect.width() * scale_x),
            int(widget_rect.height() * scale_y),
        )

    def result_pixmap(self, widget_rect: QRect) -> QPixmap:
        """Découpe directement l'image déjà capturée — aucun second appel au portail."""
        return self._background.copy(self._to_background_rect(widget_rect))

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
        painter = QPainter(self)
        if self._finished:
            painter.drawPixmap(self.rect(), self._background, self._background.rect())
            return
        painter.drawPixmap(self.rect(), self._dimmed, self._dimmed.rect())
        if not self._current_rect.isNull():
            painter.drawPixmap(self._current_rect, self._background, self._to_background_rect(self._current_rect))
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawRect(self._current_rect)
