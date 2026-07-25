import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QRect
from PyQt6.QtGui import QImage


@dataclass
class WordBox:
    text: str
    rect: QRect
    line_key: tuple
    word_num: int


class OCREngine:
    def recognize(self, image: QImage) -> str:
        raise NotImplementedError

    def recognize_words(self, image: QImage) -> list:
        raise NotImplementedError


class TesseractEngine(OCREngine):
    def __init__(self, lang: str = "fra+eng", psm: int = 6):
        self.lang = lang
        self.psm = psm

    def recognize(self, image: QImage) -> str:
        return self._run(image, "").strip()

    def recognize_words(self, image: QImage) -> list:
        output = self._run(image, "tsv")
        words = []
        lines = output.splitlines()
        if not lines:
            return words
        header = lines[0].split("\t")
        for row in lines[1:]:
            cols = row.split("\t")
            if len(cols) != len(header):
                continue
            data = dict(zip(header, cols))
            if data.get("level") != "5":
                continue
            text = data.get("text", "").strip()
            if not text:
                continue
            try:
                rect = QRect(
                    int(data["left"]),
                    int(data["top"]),
                    int(data["width"]),
                    int(data["height"]),
                )
                line_key = (
                    int(data["block_num"]),
                    int(data["par_num"]),
                    int(data["line_num"]),
                )
                word_num = int(data["word_num"])
            except (KeyError, ValueError):
                continue
            words.append(WordBox(text=text, rect=rect, line_key=line_key, word_num=word_num))
        return words

    def _run(self, image: QImage, output_format: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            png_path = Path(tmpdir) / "capture.png"
            image.save(str(png_path), "PNG")
            command = [
                "tesseract",
                str(png_path),
                "stdout",
                "-l",
                self.lang,
                "--psm",
                str(self.psm),
            ]
            if output_format:
                command.append(output_format)
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout


class PaddleOCREngine(OCREngine):
    def recognize(self, image: QImage) -> str:
        raise NotImplementedError("PaddleOCR non installé — moteur optionnel, voir Paramètres.")


def get_default_engine() -> OCREngine:
    return TesseractEngine()
