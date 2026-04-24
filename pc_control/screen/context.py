"""Screen context — fast text-based screen summary without screenshots."""
import json
import sys
import io

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    import win32gui
    import win32process
    import win32con
    import psutil
    import ctypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _get_window_state(hwnd):
    placement = win32gui.GetWindowPlacement(hwnd)
    show_cmd = placement[1]
    if show_cmd == win32con.SW_SHOWMINIMIZED:
        return "minimized"
    elif show_cmd == win32con.SW_SHOWMAXIMIZED:
        return "maximized"
    return "normal"


def get_context():
    """Get a text-based summary of current screen state."""
    if not HAS_WIN32:
        _output({"status": "error", "error": "pywin32 not available"})
        return

    # Active (foreground) window
    fg_hwnd = win32gui.GetForegroundWindow()
    fg_title = win32gui.GetWindowText(fg_hwnd) if fg_hwnd else ""
    fg_process = ""
    fg_pid = 0
    if fg_hwnd:
        _, fg_pid = win32process.GetWindowThreadProcessId(fg_hwnd)
        try:
            fg_process = psutil.Process(fg_pid).name()
        except Exception:
            pass

    fg_rect = win32gui.GetWindowRect(fg_hwnd) if fg_hwnd else (0, 0, 0, 0)

    active = {
        "hwnd": fg_hwnd,
        "title": fg_title,
        "process": fg_process,
        "pid": fg_pid,
        "state": _get_window_state(fg_hwnd) if fg_hwnd else "unknown",
        "rect": {"left": fg_rect[0], "top": fg_rect[1], "right": fg_rect[2], "bottom": fg_rect[3]},
    }

    # All visible windows
    windows = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid).name()
        except Exception:
            proc = "unknown"

        rect = win32gui.GetWindowRect(hwnd)
        state = _get_window_state(hwnd)
        # Skip zero-size windows (invisible system windows)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w <= 0 and h <= 0 and state != "minimized":
            return True

        windows.append({
            "title": title[:80],
            "process": proc,
            "state": state,
        })
        return True

    win32gui.EnumWindows(callback, None)

    # Work area
    from ctypes import wintypes
    work_rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(work_rect), 0)

    _output({
        "status": "ok",
        "action": "context",
        "active_window": active,
        "visible_windows": windows,
        "window_count": len(windows),
        "work_area": {
            "width": work_rect.right - work_rect.left,
            "height": work_rect.bottom - work_rect.top,
        },
    })
