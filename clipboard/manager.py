from PyQt6.QtWidgets import QApplication


def copy_text(text: str):
    QApplication.clipboard().setText(text)


def copy_image(image):
    QApplication.clipboard().setImage(image)
