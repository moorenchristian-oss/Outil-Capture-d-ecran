from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QWidget,
)

from annotation.painter import AnnotationTool
from ui.icons import icon

STROKE_COLORS = [
    ("Rouge", QColor(220, 30, 30)),
    ("Noir", QColor(20, 20, 20)),
    ("Blanc", QColor(255, 255, 255)),
    ("Jaune", QColor(250, 200, 0)),
    ("Vert", QColor(30, 160, 60)),
    ("Bleu", QColor(30, 110, 220)),
    ("Orange", QColor(240, 130, 20)),
    ("Rose", QColor(220, 60, 160)),
]

HIGHLIGHTER_COLORS = [
    ("Jaune", QColor(255, 235, 0, 90)),
    ("Rose", QColor(255, 90, 170, 90)),
    ("Vert", QColor(60, 220, 90, 90)),
    ("Bleu", QColor(60, 160, 255, 90)),
]

SIZE_PRESETS = [("fin", "Fin", 6), ("moyen", "Moyen", 10), ("epais", "Épais", 15)]


class _ColorSwatch(QPushButton):
    def __init__(self, name: str, color: QColor, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(name)

        # Aperçu toujours opaque (couleur mélangée sur fond blanc) : un bouton avec un
        # vrai alpha se mélange avec le fond gris du thème système et devient illisible.
        alpha = color.alpha() / 255
        preview_r = round(color.red() * alpha + 255 * (1 - alpha))
        preview_g = round(color.green() * alpha + 255 * (1 - alpha))
        preview_b = round(color.blue() * alpha + 255 * (1 - alpha))
        preview = QColor(preview_r, preview_g, preview_b)
        css_color = f"rgb({preview.red()},{preview.green()},{preview.blue()})"
        border_color = "#888" if preview.lightness() > 200 else "#333"
        self.setStyleSheet(
            f"QPushButton {{ background-color: {css_color}; border-radius: 10px; "
            f"border: 1px solid {border_color}; }}"
            f"QPushButton:hover {{ border: 2px solid #2b7fff; }}"
        )


class _SizeDot(QPushButton):
    def __init__(self, name: str, diameter: int, parent=None):
        super().__init__(parent)
        self.diameter = diameter
        self.setFixedSize(28, 28)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(name)
        self.setStyleSheet(
            "QPushButton { border: none; background: transparent; }"
            "QPushButton:checked { background-color: rgba(43,127,255,60); border-radius: 6px; }"
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.black)
        painter.setPen(Qt.PenStyle.NoPen)
        r = self.diameter
        painter.drawEllipse(self.rect().center(), r // 2, r // 2)


class DrawingOptionsBar(QWidget):
    stroke_color_changed = pyqtSignal(QColor)
    highlighter_color_changed = pyqtSignal(QColor)
    size_changed = pyqtSignal(str)
    undo_requested = pyqtSignal()
    crop_confirmed = pyqtSignal()
    crop_cancelled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._crop_bar = QWidget()
        crop_layout = QHBoxLayout(self._crop_bar)
        crop_layout.setContentsMargins(0, 0, 0, 0)
        crop_layout.setSpacing(6)
        crop_hint = QLabel("Faites glisser pour définir la zone à conserver")
        confirm_crop_button = QPushButton("Valider le rognage")
        confirm_crop_button.clicked.connect(self.crop_confirmed.emit)
        cancel_crop_button = QPushButton("Annuler")
        cancel_crop_button.clicked.connect(self.crop_cancelled.emit)
        crop_layout.addWidget(crop_hint)
        crop_layout.addStretch()
        crop_layout.addWidget(confirm_crop_button)
        crop_layout.addWidget(cancel_crop_button)
        self._crop_bar.setVisible(False)
        layout.addWidget(self._crop_bar)

        self._color_label = QLabel("Couleur")
        layout.addWidget(self._color_label)

        self._color_swatches: list[_ColorSwatch] = []
        self._color_row = QWidget()
        color_row_layout = QHBoxLayout(self._color_row)
        color_row_layout.setContentsMargins(0, 0, 0, 0)
        color_row_layout.setSpacing(4)
        layout.addWidget(self._color_row)

        self._custom_color_button = QPushButton("…")
        self._custom_color_button.setFixedSize(20, 20)
        self._custom_color_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._custom_color_button.setToolTip("Autre couleur…")
        self._custom_color_button.clicked.connect(self._pick_custom_color)
        layout.addWidget(self._custom_color_button)

        layout.addSpacing(12)
        self._size_label = QLabel("Épaisseur")
        layout.addWidget(self._size_label)

        self._size_buttons: dict[str, _SizeDot] = {}
        for preset, name, diameter in SIZE_PRESETS:
            dot = _SizeDot(name, diameter)
            dot.clicked.connect(lambda checked, p=preset: self._on_size_clicked(p))
            self._size_buttons[preset] = dot
            layout.addWidget(dot)
        self._size_buttons["moyen"].setChecked(True)

        layout.addStretch()

        self._undo_button = QToolButton()
        self._undo_button.setIcon(icon("edit-undo-symbolic"))
        self._undo_button.setText("Annuler")
        self._undo_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._undo_button.clicked.connect(self.undo_requested.emit)
        layout.addWidget(self._undo_button)

        self._normal_widgets = [
            self._color_label,
            self._color_row,
            self._custom_color_button,
            self._size_label,
            *self._size_buttons.values(),
            self._undo_button,
        ]

        self._current_tool = AnnotationTool.NONE
        self.set_active_tool(AnnotationTool.PEN)

    def enter_crop_mode(self):
        for widget in self._normal_widgets:
            widget.setVisible(False)
        self._crop_bar.setVisible(True)

    def exit_crop_mode(self):
        self._crop_bar.setVisible(False)
        for widget in self._normal_widgets:
            widget.setVisible(True)
        self.set_active_tool(self._current_tool)

    def _rebuild_color_row(self, colors: list[tuple[str, QColor]]):
        color_row_layout = self._color_row.layout()
        while color_row_layout.count():
            item = color_row_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._color_swatches.clear()

        for name, color in colors:
            swatch = _ColorSwatch(name, color)
            swatch.clicked.connect(lambda checked, c=color: self._on_color_clicked(c))
            color_row_layout.addWidget(swatch)
            self._color_swatches.append(swatch)

    def _on_color_clicked(self, color: QColor):
        if self._current_tool == AnnotationTool.HIGHLIGHTER:
            self.highlighter_color_changed.emit(color)
        else:
            self.stroke_color_changed.emit(color)

    def _pick_custom_color(self):
        chosen = QColorDialog.getColor(QColor(220, 30, 30), self, "Choisir une couleur")
        if chosen.isValid():
            self._on_color_clicked(chosen)

    def _on_size_clicked(self, preset: str):
        for name, button in self._size_buttons.items():
            button.setChecked(name == preset)
        self.size_changed.emit(preset)

    def set_active_tool(self, tool: AnnotationTool):
        self._current_tool = tool
        if tool in (AnnotationTool.ERASER, AnnotationTool.BLUR):
            self._color_label.setVisible(False)
            self._color_row.setVisible(False)
            self._custom_color_button.setVisible(False)
        elif tool == AnnotationTool.HIGHLIGHTER:
            self._color_label.setVisible(True)
            self._color_row.setVisible(True)
            self._custom_color_button.setVisible(True)
            self._rebuild_color_row(HIGHLIGHTER_COLORS)
        else:
            self._color_label.setVisible(True)
            self._color_row.setVisible(True)
            self._custom_color_button.setVisible(True)
            self._rebuild_color_row(STROKE_COLORS)
