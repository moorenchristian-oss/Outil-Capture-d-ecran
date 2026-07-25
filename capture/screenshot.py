from PyQt6.QtGui import QImage

from capture.backend import get_backend


def capture_fullscreen(mute_sound: bool = False) -> QImage:
    return get_backend().grab_fullscreen(mute_sound=mute_sound)
