"""Audio control — volume and mute via pycaw or media keys fallback."""
import json
import sys


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))

try:
    from pycaw.pycaw import AudioUtilities
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False


def _get_volume_interface():
    return AudioUtilities.GetSpeakers().EndpointVolume


def get_volume():
    if HAS_PYCAW:
        vol = _get_volume_interface()
        level = round(vol.GetMasterVolumeLevelScalar() * 100)
        muted = bool(vol.GetMute())
        _output({"status": "ok", "action": "get_volume", "volume": level, "muted": muted})
    else:
        _output({"status": "error", "error": "pycaw not installed. pip install pycaw"})


def set_volume(level: int):
    level = max(0, min(100, level))
    if HAS_PYCAW:
        vol = _get_volume_interface()
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        _output({"status": "ok", "action": "set_volume", "volume": level})
    else:
        # Fallback: media keys
        import pyautogui
        for _ in range(50):
            pyautogui.press('volumedown')
        for _ in range(level // 2):
            pyautogui.press('volumeup')
        _output({"status": "ok", "action": "set_volume", "volume": level, "method": "media_keys"})


def mute():
    if HAS_PYCAW:
        vol = _get_volume_interface()
        vol.SetMute(1, None)
        _output({"status": "ok", "action": "mute"})
    else:
        import pyautogui
        pyautogui.press('volumemute')
        _output({"status": "ok", "action": "mute", "method": "media_key"})


def unmute():
    if HAS_PYCAW:
        vol = _get_volume_interface()
        vol.SetMute(0, None)
        _output({"status": "ok", "action": "unmute"})
    else:
        import pyautogui
        pyautogui.press('volumemute')
        _output({"status": "ok", "action": "unmute", "method": "media_key"})


def toggle_mute():
    if HAS_PYCAW:
        vol = _get_volume_interface()
        current = vol.GetMute()
        vol.SetMute(0 if current else 1, None)
        _output({"status": "ok", "action": "toggle_mute", "muted": not bool(current)})
    else:
        import pyautogui
        pyautogui.press('volumemute')
        _output({"status": "ok", "action": "toggle_mute", "method": "media_key"})


def handle_command(args):
    cmd = args.audio_command
    if cmd == "volume":
        level = getattr(args, "level", None)
        if level is not None:
            set_volume(level)
        else:
            get_volume()
    elif cmd == "mute":
        mute()
    elif cmd == "unmute":
        unmute()
    elif cmd == "toggle":
        toggle_mute()
    else:
        print(f"Unknown audio command: {cmd}", file=sys.stderr)
        sys.exit(1)
