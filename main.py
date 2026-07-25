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

    app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
