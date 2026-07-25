from PyQt6.QtCore import QRect, QSize
from PyQt6.QtGui import QImage

from capture.backend import get_backend


def capture_fullscreen(mute_sound: bool = False) -> QImage:
    return get_backend().grab_fullscreen(mute_sound=mute_sound)


def crop_to_logical_rect(image: QImage, overlay_size: QSize, rect: QRect) -> QImage:
    scale_x = image.width() / overlay_size.width()
    scale_y = image.height() / overlay_size.height()
    x = int(rect.x() * scale_x)
    y = int(rect.y() * scale_y)
    w = int(rect.width() * scale_x)
    h = int(rect.height() * scale_y)
    return image.copy(x, y, w, h)
