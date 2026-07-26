from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ui.icons import icon


class RecordingIndicator(QWidget):
    stop_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # Couleurs issues de la palette Qt (héritée du thème système clair/sombre)
        # plutôt que des couleurs fixes, pour rester lisible dans les deux cas.
        self.setAutoFillBackground(True)
        self.setStyleSheet(
            "QWidget#recordingIndicator { background-color: palette(window); "
            "border: 1px solid palette(mid); border-radius: 8px; }"
            "QLabel { color: palette(window-text); font-weight: bold; }"
        )
        self.setObjectName("recordingIndicator")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self._dot = QLabel("●")
        self._dot.setStyleSheet("color: #e01b1b; font-size: 16px;")
        self._time_label = QLabel("00:00")

        stop_button = QPushButton(" Arrêter")
        stop_button.setIcon(icon("media-playback-stop-symbolic"))
        stop_button.clicked.connect(self.stop_requested.emit)

        layout.addWidget(self._dot)
        layout.addWidget(self._time_label)
        layout.addWidget(stop_button)

        self._dot_visible = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start(600)

        self.adjustSize()
        self._move_to_corner()

    def _move_to_corner(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 24, screen.top() + 24)

    def _blink(self):
        self._dot_visible = not self._dot_visible
        self._dot.setVisible(self._dot_visible)

    def set_elapsed(self, seconds: int):
        minutes, secs = divmod(seconds, 60)
        self._time_label.setText(f"{minutes:02d}:{secs:02d}")

    def closeEvent(self, event):
        self._blink_timer.stop()
        super().closeEvent(event)
