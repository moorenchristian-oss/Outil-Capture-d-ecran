from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QScrollArea,
    QToolBar,
    QToolButton,
    QWidget,
)

from annotation.painter import AnnotationCanvas, AnnotationTool
from capture.backend import session_type
from capture.screenshot import capture_fullscreen, crop_to_logical_rect
from capture.selector import RegionSelectorOverlay
from clipboard.manager import copy_image
from database.history import add_entry
from ocr.ocr_engine import get_default_engine
from ui.icons import icon
from ui.ocr_selection import OCRSelectionDialog, build_text
from ui.toggle_switch import ToggleSwitch

MODES = [
    ("Forme libre", "freeform", "edit-select-all-symbolic", "lasso.png"),
    ("Capture rectangulaire", "rectangle", "object-select-symbolic", "capture-rect-dashed.png"),
    ("Capture Fenêtre", "window", "focus-windows-symbolic", None),
    ("Capture Plein écran", "fullscreen", "view-fullscreen-symbolic", None),
]

TOOLS = [
    ("Stylet", AnnotationTool.PEN, "document-edit-symbolic", None),
    ("Surligneur", AnnotationTool.HIGHLIGHTER, "marker-symbolic", None),
    ("Gomme", AnnotationTool.ERASER, "edit-clear-symbolic", None),
    ("Carré / Rectangle", AnnotationTool.RECTANGLE, "shape-rectangle-symbolic", "draw-rectangle.png"),
    ("Rond / Ellipse", AnnotationTool.ELLIPSE, "shape-circle-symbolic", "draw-circle.png"),
]

ICON_PATH = Path(__file__).parent.parent / "data" / "icons" / "outil-capture-decran-256.png"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Outil Capture d'écran")
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self.resize(760, 540)

        self._mode = "rectangle"
        self._overlay = None
        self._pending_action = "capture"
        self._mute_sound = True
        self.canvas = None

        self._build_menu_bar()
        self._build_toolbar()
        self._build_canvas()

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&Fichier")
        file_menu.addAction("Nouveau", self.on_nouveau)
        file_menu.addAction("Enregistrer sous…", self.on_enregistrer)
        file_menu.addSeparator()
        file_menu.addAction("Quitter", self.close)

        edit_menu = menu_bar.addMenu("&Édition")
        edit_menu.addAction("Copier", self.on_copier)

        tools_menu = menu_bar.addMenu("&Outils")
        tools_menu.addAction("Copier le texte (OCR)", self.on_ocr)

        help_menu = menu_bar.addMenu("&?")
        help_menu.addAction("À propos", self.on_about)

    def _build_toolbar(self):
        toolbar = QToolBar("Principale")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.setIconSize(QSize(22, 22))
        self.addToolBar(toolbar)

        self.action_nouveau = QAction(icon("camera-photo-symbolic"), "Nouveau", self)
        self.action_nouveau.triggered.connect(self.on_nouveau)
        toolbar.addAction(self.action_nouveau)

        toolbar.addWidget(self._build_mode_button())
        toolbar.addSeparator()

        self.action_save = QAction(icon("document-save-symbolic"), "Enregistrer", self)
        self.action_save.triggered.connect(self.on_enregistrer)
        self.action_save.setEnabled(False)
        toolbar.addAction(self.action_save)

        self.action_copy = QAction(icon("edit-copy-symbolic"), "Copier", self)
        self.action_copy.triggered.connect(self.on_copier)
        self.action_copy.setEnabled(False)
        toolbar.addAction(self.action_copy)
        toolbar.addSeparator()

        toolbar.addWidget(self._build_tool_button())
        toolbar.addSeparator()

        self.action_ocr = QAction(icon("insert-text-symbolic"), "OCR Texte", self)
        self.action_ocr.triggered.connect(self.on_ocr)
        toolbar.addAction(self.action_ocr)
        toolbar.addSeparator()
        toolbar.addWidget(self._build_mute_switch())

    def _build_mute_switch(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        self.mute_icon_label = QLabel()
        self.mute_icon_label.setPixmap(self._mute_icon().pixmap(18, 18))
        label = QLabel("Couper le son")
        self.mute_switch = ToggleSwitch(checked=self._mute_sound)
        self.mute_switch.toggled.connect(self._on_mute_toggled)

        layout.addWidget(self.mute_icon_label)
        layout.addWidget(label)
        layout.addWidget(self.mute_switch)
        return container

    def _mute_icon(self):
        return icon("audio-volume-muted-symbolic" if self._mute_sound else "audio-volume-high-symbolic")

    def _on_mute_toggled(self, checked: bool):
        self._mute_sound = checked
        self.mute_icon_label.setPixmap(self._mute_icon().pixmap(18, 18))

    def _build_mode_button(self) -> QToolButton:
        button = QToolButton()
        button.setText("Mode")
        button.setIcon(icon("selection-mode-symbolic"))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QMenu(button)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for label, value, theme_name, custom_file in MODES:
            action = QAction(icon(theme_name, custom_file), label, menu, checkable=True)
            action.setChecked(value == self._mode)
            action.triggered.connect(lambda checked, v=value: setattr(self, "_mode", v))
            group.addAction(action)
            menu.addAction(action)

        button.setMenu(menu)
        return button

    def _build_tool_button(self) -> QToolButton:
        button = QToolButton()
        button.setText("Dessin")
        button.setIcon(icon("applications-graphics-symbolic"))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QMenu(button)
        group = QActionGroup(menu)
        group.setExclusive(True)
        for label, tool, theme_name, custom_file in TOOLS:
            action = QAction(icon(theme_name, custom_file), label, menu, checkable=True)
            action.triggered.connect(lambda checked, t=tool: self._set_annotation_tool(t))
            group.addAction(action)
            menu.addAction(action)

        button.setMenu(menu)
        return button

    def _set_annotation_tool(self, tool: AnnotationTool):
        if self.canvas is not None:
            self.canvas.set_tool(tool)
        else:
            QMessageBox.information(
                self, "Aucune capture", "Prenez d'abord une capture avec Nouveau."
            )

    def _build_canvas(self):
        self.placeholder_label = QLabel(
            "Sélectionnez un mode ou cliquez sur le bouton Nouveau pour commencer."
        )
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setWordWrap(True)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.placeholder_label)
        self.setCentralWidget(self.scroll)

    def on_nouveau(self):
        self.hide()
        QTimer.singleShot(150, self._start_capture)

    def _start_capture(self):
        if self._mode == "fullscreen":
            self._grab_and_finish(None)
            return

        self._overlay = RegionSelectorOverlay()
        self._overlay.region_selected.connect(
            lambda rect: QTimer.singleShot(120, lambda: self._grab_and_finish(rect))
        )
        self._overlay.cancelled.connect(self._cancel_capture)
        self._overlay.showFullScreen()

    def _bring_to_front(self):
        self.show()
        self.setWindowState(
            (self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive
        )
        self.raise_()
        self.activateWindow()

    def _cancel_capture(self):
        self._pending_action = "capture"
        self._bring_to_front()

    def _grab_and_finish(self, rect):
        overlay_size = self._overlay.size() if self._overlay is not None else None
        try:
            image = capture_fullscreen(mute_sound=self._mute_sound)
        except Exception as exc:
            self._bring_to_front()
            QMessageBox.warning(self, "Erreur de capture", str(exc))
            return

        if rect is not None:
            image = crop_to_logical_rect(image, overlay_size, rect)

        action, self._pending_action = self._pending_action, "capture"
        if action == "ocr":
            self._run_ocr(image)
        else:
            self._finish_capture(image)

    def _finish_capture(self, image):
        self._bring_to_front()
        self.canvas = AnnotationCanvas(image)
        self.scroll.setWidget(self.canvas)
        self.action_save.setEnabled(True)
        self.action_copy.setEnabled(True)
        self.action_ocr.setEnabled(True)

    def on_enregistrer(self):
        if self.canvas is None:
            return
        default_dir = Path.home() / "Images"
        default_dir.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer la capture",
            str(default_dir / "capture.png"),
            "Images PNG (*.png)",
        )
        if path:
            self.canvas.result_image().save(path, "PNG")
            add_entry("image", path)

    def on_copier(self):
        if self.canvas is not None:
            copy_image(self.canvas.result_image())

    def on_ocr(self):
        if self.canvas is not None:
            self._run_ocr(self.canvas.result_image())
            return
        self._pending_action = "ocr"
        self.on_nouveau()

    def _run_ocr(self, image):
        self._bring_to_front()
        self.setEnabled(False)
        try:
            engine = get_default_engine()
            words = engine.recognize_words(image)
        except Exception as exc:
            self.setEnabled(True)
            QMessageBox.warning(self, "Erreur OCR", str(exc))
            return
        self.setEnabled(True)

        if not words:
            QMessageBox.information(
                self, "OCR", "Aucun texte détecté dans la zone sélectionnée."
            )
            return

        add_entry("ocr", "", build_text(words, range(len(words))))
        OCRSelectionDialog(image, words, self).exec()

    def on_about(self):
        QMessageBox.information(
            self, "À propos", "Ubuntu Screen Capture Tool\nSession : " + session_type()
        )

