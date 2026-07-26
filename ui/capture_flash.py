from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QGuiApplication, QPainter
from PyQt6.QtWidgets import QWidget


class CaptureFlash(QWidget):
    """Flash plein écran bref : retour visuel immédiat au moment de la capture, en plus
    du son du déclencheur (utile aussi quand celui-ci est coupé).

    Pas de fondu animé : setWindowOpacity() ne fonctionne pas de façon fiable sous le
    plugin QPA Wayland (déjà vérifié ailleurs dans ce projet) — un flash "dur" (affiché
    puis masqué) reste simple et fiable quel que soit le compositeur.
    """

    def __init__(self, duration_ms: int = 120):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        virtual_geometry = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(virtual_geometry)
        self.show()
        self.raise_()
        QTimer.singleShot(duration_ms, self._finish)

    def _finish(self):
        self.hide()
        self.close()
        self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255))
