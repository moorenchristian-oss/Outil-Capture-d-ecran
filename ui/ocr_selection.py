from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QGuiApplication, QImage, QKeySequence, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from clipboard.manager import copy_text


def build_text(words, selected_indices) -> str:
    selected = sorted(selected_indices, key=lambda i: (words[i].line_key, words[i].word_num))
    lines = []
    current_key = None
    current_words = []
    for i in selected:
        word = words[i]
        if word.line_key != current_key:
            if current_words:
                lines.append(" ".join(current_words))
            current_words = []
            current_key = word.line_key
        current_words.append(word.text)
    if current_words:
        lines.append(" ".join(current_words))
    return "\n".join(lines)


class ImageSelectWidget(QWidget):
    def __init__(self, image: QImage, words: list, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap.fromImage(image)
        self.words = words
        self.selected = set()
        self._dragging = False
        self._drag_start = QPoint()
        self._drag_rect = QRect()
        self.setFixedSize(self.pixmap.size())
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.IBeamCursor)

    def mousePressEvent(self, event):
        self.setFocus()
        self._dragging = True
        self._drag_start = event.pos()
        self._drag_rect = QRect(self._drag_start, self._drag_start)
        if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.selected = set()
        self.update()

    def mouseMoveEvent(self, event):
        if not self._dragging:
            return
        self._drag_rect = QRect(self._drag_start, event.pos()).normalized()
        for i, word in enumerate(self.words):
            if self._drag_rect.intersects(word.rect):
                self.selected.add(i)
        self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self.update()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection()
        elif event.matches(QKeySequence.StandardKey.SelectAll):
            self._select_all()

    def copy_selection(self) -> str:
        text = build_text(self.words, self.selected)
        if text:
            copy_text(text)
        return text

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        copy_action = menu.addAction("Copier")
        copy_action.setEnabled(bool(self.selected))
        copy_action.triggered.connect(self.copy_selection)
        select_all_action = menu.addAction("Tout sélectionner")
        select_all_action.triggered.connect(self._select_all)
        menu.exec(event.globalPos())

    def _select_all(self):
        self.selected = set(range(len(self.words)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 120, 255, 90))
        for i in self.selected:
            painter.drawRect(self.words[i].rect)

        if self._dragging:
            painter.setPen(QPen(QColor(0, 120, 255), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(0, 120, 255, 30))
            painter.drawRect(self._drag_rect)


class OCRSelectionDialog(QDialog):
    def __init__(self, image: QImage, words: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sélectionner le texte sur la photo")
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setSizeGripEnabled(True)

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Glissez la souris sur le texte à sélectionner, puis Ctrl+C pour copier "
            "(Ctrl+clic pour étendre la sélection, Ctrl+A pour tout sélectionner)."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.image_widget = ImageSelectWidget(image, words)
        scroll = QScrollArea()
        scroll.setWidget(self.image_widget)
        scroll.setWidgetResizable(False)
        layout.addWidget(scroll)

        buttons = QHBoxLayout()
        copy_button = QPushButton("Copier la sélection")
        copy_button.clicked.connect(self.image_widget.copy_selection)
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(copy_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        max_width = int(screen.width() * 0.9)
        max_height = int(screen.height() * 0.9)
        self.resize(
            min(self.image_widget.width() + 40, max_width),
            min(self.image_widget.height() + 140, max_height),
        )
        self.image_widget.setFocus()
