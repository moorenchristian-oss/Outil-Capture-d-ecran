"""Enregistrement vidéo de l'écran (zone ou plein écran), export MP4.

Sous Wayland, la capture passe par le portail `org.freedesktop.portal.ScreenCast` :
Mutter crée un flux PipeWire correspondant à l'écran choisi par l'utilisateur dans la
boîte de dialogue système. On lit ce flux avec `pipewiresrc` (GStreamer), on le recadre
si une zone a été sélectionnée, puis on envoie les images brutes (rawvideo) sur l'entrée
standard d'un processus `ffmpeg` qui encode en H.264/MP4. Ce pipeline n'utilise que des
paquets déjà présents sur une installation Ubuntu standard (aucun encodeur GStreamer
supplémentaire requis).

Sous X11, `ffmpeg -f x11grab` capture directement le rectangle demandé, plus simple
car aucun portail n'est nécessaire.
"""

import shutil
import signal
import subprocess
import time
from pathlib import Path

from capture.backend import session_type

FRAMERATE = 30

# Mémorise le choix d'écran du portail ScreenCast (restore_token) pour que GNOME
# n'affiche plus la boîte de dialogue de partage à chaque enregistrement.
RESTORE_TOKEN_PATH = Path.home() / ".local" / "share" / "screen_capture_tool" / "screencast_restore_token"


def _load_restore_token() -> str:
    try:
        return RESTORE_TOKEN_PATH.read_text().strip()
    except OSError:
        return ""


def _save_restore_token(token: str):
    if not token:
        return
    RESTORE_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESTORE_TOKEN_PATH.write_text(token)


class ScreenCastError(RuntimeError):
    pass


class ScreenCastSession:
    """Session ScreenCast Wayland active : garde la connexion D-Bus ouverte tant que
    l'enregistrement dure (fermer la connexion met fin au flux PipeWire côté Mutter)."""

    def __init__(self, bus, session_handle, node_id, width, height):
        self._bus = bus
        self._session_handle = session_handle
        self.node_id = node_id
        self.width = width
        self.height = height

    def close(self):
        try:
            session_obj = self._bus.get_object(
                "org.freedesktop.portal.Desktop", self._session_handle
            )
            session_obj.Close(dbus_interface="org.freedesktop.portal.Session")
        except Exception:
            pass


def open_screencast_session() -> ScreenCastSession:
    """Ouvre une session ScreenCast via le portail Wayland. Déclenche la boîte de
    dialogue système GNOME de sélection d'écran/fenêtre + autorisation."""
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    portal = bus.get_object(
        "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
    )
    screencast_iface = dbus.Interface(portal, "org.freedesktop.portal.ScreenCast")
    unique_name = bus.get_unique_name().replace(":", "").replace(".", "_")

    def call_and_wait(make_request_path, invoke):
        result = {}
        loop = GLib.MainLoop()

        def on_response(response_code, results):
            result["code"] = int(response_code)
            result["results"] = {str(k): v for k, v in results.items()}
            loop.quit()

        request_path = make_request_path()
        bus.add_signal_receiver(
            on_response,
            signal_name="Response",
            dbus_interface="org.freedesktop.portal.Request",
            path=request_path,
        )
        invoke()
        GLib.timeout_add_seconds(120, loop.quit)
        loop.run()
        if result.get("code") != 0:
            raise ScreenCastError(
                "Partage d'écran annulé ou refusé dans la boîte de dialogue système."
            )
        return result["results"]

    token = f"t{int(time.time() * 1000)}"

    create_results = call_and_wait(
        lambda: f"/org/freedesktop/portal/desktop/request/{unique_name}/{token}c",
        lambda: screencast_iface.CreateSession(
            {"handle_token": token + "c", "session_handle_token": token + "s"}
        ),
    )
    session_handle = create_results["session_handle"]

    select_options = {
        "handle_token": token + "sel",
        "types": dbus.UInt32(1),  # 1 = MONITOR
        "multiple": False,
        "cursor_mode": dbus.UInt32(2),  # 2 = EMBEDDED (curseur visible dans le flux)
        "persist_mode": dbus.UInt32(2),  # 2 = mémoriser jusqu'à révocation explicite
    }
    saved_token = _load_restore_token()
    if saved_token:
        select_options["restore_token"] = saved_token

    call_and_wait(
        lambda: f"/org/freedesktop/portal/desktop/request/{unique_name}/{token}sel",
        lambda: screencast_iface.SelectSources(session_handle, select_options),
    )

    start_results = call_and_wait(
        lambda: f"/org/freedesktop/portal/desktop/request/{unique_name}/{token}start",
        lambda: screencast_iface.Start(
            session_handle, "", {"handle_token": token + "start"}
        ),
    )

    new_token = start_results.get("restore_token")
    if new_token:
        _save_restore_token(str(new_token))

    streams = start_results.get("streams")
    if not streams:
        raise ScreenCastError("Aucun flux d'écran retourné par le portail.")
    node_id, stream_props = streams[0]
    size = stream_props.get("size")
    width, height = (int(size[0]), int(size[1])) if size else (0, 0)
    return ScreenCastSession(bus, session_handle, int(node_id), width, height)


class VideoRecorder:
    """Pilote l'enregistrement : démarre/arrête les processus gst-launch + ffmpeg
    (Wayland) ou ffmpeg seul (X11), et écrit le fichier MP4 final."""

    def __init__(self):
        self._gst_proc = None
        self._ffmpeg_proc = None
        self._session = None
        self._started_at = 0.0

    def start(self, output_path: str, region_rect=None, region_overlay_size=None):
        """region_rect/region_overlay_size : rectangle et taille (en pixels logiques Qt)
        renvoyés par le sélecteur de zone, ou None pour un enregistrement plein écran."""
        if session_type() == "wayland":
            self._start_wayland(output_path, region_rect, region_overlay_size)
        else:
            self._start_x11(output_path, region_rect, region_overlay_size)
        self._started_at = time.monotonic()

    def elapsed_seconds(self) -> int:
        if not self._started_at:
            return 0
        return int(time.monotonic() - self._started_at)

    @staticmethod
    def _scale_rect(region_rect, region_overlay_size, target_width, target_height):
        scale_x = target_width / region_overlay_size.width()
        scale_y = target_height / region_overlay_size.height()
        x = int(region_rect.x() * scale_x)
        y = int(region_rect.y() * scale_y)
        w = int(region_rect.width() * scale_x)
        h = int(region_rect.height() * scale_y)
        return x, y, w, h

    def _start_wayland(self, output_path: str, region_rect, region_overlay_size):
        if shutil.which("gst-launch-1.0") is None:
            raise ScreenCastError(
                "gst-launch-1.0 introuvable (paquet gstreamer1.0-tools manquant)."
            )

        session = open_screencast_session()
        self._session = session
        width, height = session.width, session.height
        if width <= 0 or height <= 0:
            session.close()
            raise ScreenCastError("Taille de flux invalide retournée par le portail.")

        crop_rect = None
        if region_rect is not None:
            crop_rect = self._scale_rect(region_rect, region_overlay_size, width, height)

        pipeline = ["pipewiresrc", f"path={session.node_id}", "!", "videoconvert"]
        if crop_rect is not None:
            x, y, w, h = crop_rect
            left, top = max(0, x), max(0, y)
            right = max(0, width - (x + w))
            bottom = max(0, height - (y + h))
            pipeline += [
                "!",
                "videocrop",
                f"left={left}",
                f"top={top}",
                f"right={right}",
                f"bottom={bottom}",
            ]
            out_w, out_h = w, h
        else:
            out_w, out_h = width, height
        pipeline += [
            "!",
            "videorate",
            "!",
            f"video/x-raw,format=I420,framerate={FRAMERATE}/1",
            "!",
            "fdsink",
            "fd=1",
        ]

        self._gst_proc = subprocess.Popen(
            ["gst-launch-1.0", "-q", *pipeline],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self._ffmpeg_proc = subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "rawvideo",
                "-pix_fmt", "yuv420p",
                "-s", f"{out_w}x{out_h}",
                "-r", str(FRAMERATE),
                "-i", "-",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path,
            ],
            stdin=self._gst_proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._gst_proc.stdout.close()

    def _start_x11(self, output_path: str, region_rect, region_overlay_size):
        import mss

        with mss.mss() as sct:
            mon = sct.monitors[0]
        mon_width, mon_height = mon["width"], mon["height"]

        if region_rect is not None:
            x, y, w, h = self._scale_rect(region_rect, region_overlay_size, mon_width, mon_height)
            video_size = f"{w}x{h}"
            input_spec = f":0.0+{x},{y}"
        else:
            video_size = f"{mon_width}x{mon_height}"
            input_spec = ":0.0"

        self._ffmpeg_proc = subprocess.Popen(
            [
                "ffmpeg", "-y",
                "-f", "x11grab",
                "-video_size", video_size,
                "-framerate", str(FRAMERATE),
                "-i", input_spec,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self):
        if self._gst_proc is not None:
            self._gst_proc.send_signal(signal.SIGINT)
            self._gst_proc.wait(timeout=10)
            self._gst_proc = None
        if self._ffmpeg_proc is not None:
            if self._ffmpeg_proc.stdin is None:
                # x11grab : ffmpeg lit directement l'écran, on lui demande d'arrêter proprement.
                self._ffmpeg_proc.send_signal(signal.SIGINT)
            self._ffmpeg_proc.wait(timeout=15)
            self._ffmpeg_proc = None
        if self._session is not None:
            self._session.close()
            self._session = None
        self._started_at = 0.0
