from capture.backend import session_type


class VideoRecorder:
    def __init__(self, x: int, y: int, width: int, height: int, output_path: str):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.output_path = output_path
        self._process = None

    def start(self):
        if session_type() == "wayland":
            self._start_wayland()
        else:
            self._start_x11()

    def _start_x11(self):
        raise NotImplementedError

    def _start_wayland(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
