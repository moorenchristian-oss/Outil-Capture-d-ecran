from pathlib import Path

from PyQt6.QtGui import QIcon

CUSTOM_ICONS_DIR = Path(__file__).parent.parent / "data" / "icons" / "toolbar"


def icon(theme_name: str, custom_file: str | None = None) -> QIcon:
    if custom_file:
        fallback = QIcon(str(CUSTOM_ICONS_DIR / custom_file))
        return QIcon.fromTheme(theme_name, fallback)
    return QIcon.fromTheme(theme_name)
