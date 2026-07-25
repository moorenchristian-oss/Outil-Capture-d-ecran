import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ui.window import MainWindow

ICON_PATH = Path(__file__).parent / "data" / "icons" / "outil-capture-decran-256.png"


def main():
    app = QApplication(sys.argv)

    # Sans ceci, QIcon.fromTheme() renvoie des icônes nulles pour tout —
    # ce PyQt6 (apt) ne détecte pas automatiquement le thème d'icônes système.
    QIcon.setThemeSearchPaths(["/usr/share/icons"])
    QIcon.setThemeName("Yaru")
    QIcon.setFallbackThemeName("Adwaita")

    # Sans ceci, GNOME identifie la fenêtre par son WM_CLASS/app_id qui vaut
    # "python3" (l'interpréteur), pas l'application — le dock affiche alors
    # l'icône générique Python au lieu de la nôtre. Doit correspondre au nom du
    # fichier .desktop créé par install.sh (outil-capture-decran.desktop).
    app.setDesktopFileName("outil-capture-decran")

    app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
