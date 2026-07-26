import argparse
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from ui.window import MainWindow

ICON_PATH = Path(__file__).parent / "data" / "icons" / "outil-capture-decran-256.png"


def parse_args():
    parser = argparse.ArgumentParser(description="Outil Capture d'écran")
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Lance directement une capture au démarrage (pour un raccourci clavier système).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
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
    if args.capture:
        QTimer.singleShot(0, window.on_nouveau)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
