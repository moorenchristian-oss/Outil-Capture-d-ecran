import subprocess
import time
from contextlib import contextmanager

# GNOME plays the shutter sound asynchronously, slightly after the portal
# Response signal arrives — unmuting immediately on response can still let it
# through, so we hold the mute a bit longer before restoring it.
UNMUTE_DELAY_SECONDS = 0.8


def _set_mute(muted: bool):
    # wpctl (WirePlumber) n'est pas garanti présent/actif sur toutes les versions
    # d'Ubuntu (ex. PulseAudio encore par défaut) — la coupure du son est une
    # amélioration de confort, jamais une condition pour que la capture fonctionne.
    try:
        subprocess.run(
            ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0"],
            capture_output=True,
        )
    except OSError:
        pass


@contextmanager
def muted_during_capture(enabled: bool):
    if not enabled:
        yield
        return
    _set_mute(True)
    try:
        yield
    finally:
        time.sleep(UNMUTE_DELAY_SECONDS)
        _set_mute(False)
