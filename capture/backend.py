import os
import time
from urllib.parse import unquote

from PyQt6.QtGui import QImage

from capture.sound import muted_during_capture


def session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "unknown")


class CaptureBackend:
    def grab_fullscreen(self, mute_sound: bool = False) -> QImage:
        raise NotImplementedError

    def grab_region(self, x: int, y: int, width: int, height: int, mute_sound: bool = False) -> QImage:
        image = self.grab_fullscreen(mute_sound=mute_sound)
        return image.copy(x, y, width, height)


class X11Backend(CaptureBackend):
    def grab_fullscreen(self, mute_sound: bool = False) -> QImage:
        import mss

        with muted_during_capture(mute_sound):
            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[0])
                image = QImage(
                    shot.bgra, shot.width, shot.height, QImage.Format.Format_ARGB32
                )
                return image.copy()


class WaylandBackend(CaptureBackend):
    def grab_fullscreen(self, mute_sound: bool = False) -> QImage:
        import dbus
        from dbus.mainloop.glib import DBusGMainLoop
        from gi.repository import GLib

        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        portal = bus.get_object(
            "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
        )
        screenshot_iface = dbus.Interface(portal, "org.freedesktop.portal.Screenshot")

        token = f"screencapture{int(time.time() * 1000)}"
        unique_name = bus.get_unique_name().replace(":", "").replace(".", "_")
        request_path = f"/org/freedesktop/portal/desktop/request/{unique_name}/{token}"

        result = {}
        loop = GLib.MainLoop()

        def on_response(response_code, results):
            result["code"] = int(response_code)
            result["results"] = {str(k): v for k, v in results.items()}
            loop.quit()

        bus.add_signal_receiver(
            on_response,
            signal_name="Response",
            dbus_interface="org.freedesktop.portal.Request",
            path=request_path,
        )

        with muted_during_capture(mute_sound):
            screenshot_iface.Screenshot(
                "", {"handle_token": token, "interactive": False}
            )

            GLib.timeout_add_seconds(20, loop.quit)
            loop.run()

        if result.get("code") != 0:
            raise RuntimeError(
                "Capture d'écran annulée ou refusée par le portail Wayland."
            )

        uri = str(result["results"]["uri"])
        file_path = unquote(uri.removeprefix("file://"))
        image = QImage(file_path)
        if image.isNull():
            raise RuntimeError(f"Impossible de charger l'image capturée : {file_path}")
        return image


def get_backend() -> CaptureBackend:
    if session_type() == "wayland":
        return WaylandBackend()
    return X11Backend()
