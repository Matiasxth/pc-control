"""Window management module — list, focus, resize, minimize/maximize via win32gui."""

import ctypes
import io
import json
import sys
import time

# Fix stdout encoding for Unicode window titles
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    import psutil
    import win32con
    import win32gui
    import win32process

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _check_win32():
    if not HAS_WIN32:
        _output({"status": "error", "error": "pywin32 not available"})
        sys.exit(1)


def _get_window_state(hwnd):
    placement = win32gui.GetWindowPlacement(hwnd)
    show_cmd = placement[1]
    if show_cmd == win32con.SW_SHOWMINIMIZED:
        return "minimized"
    elif show_cmd == win32con.SW_SHOWMAXIMIZED:
        return "maximized"
    return "normal"


def list_windows(filter_query=None):
    """List all visible windows."""
    _check_win32()
    windows = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        if filter_query and filter_query.lower() not in title.lower():
            return True

        rect = win32gui.GetWindowRect(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc_name = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            proc_name = "unknown"

        windows.append(
            {
                "hwnd": hwnd,
                "title": title,
                "pid": pid,
                "process": proc_name,
                "rect": {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3]},
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
                "state": _get_window_state(hwnd),
            }
        )
        return True

    win32gui.EnumWindows(callback, None)
    _output({"status": "ok", "action": "list_windows", "count": len(windows), "windows": windows})


def _find_window(query) -> int | None:
    """Find first window matching query (partial title, case-insensitive)."""
    query_lower = query.lower()
    result = [None]

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and query_lower in title.lower():
                result[0] = hwnd
                return False  # stop enumeration
        return True

    try:
        win32gui.EnumWindows(callback, None)
    except Exception:
        pass  # EnumWindows raises when callback returns False
    return result[0]


def _resolve_hwnd(args) -> int | None:
    hwnd = getattr(args, "hwnd", None)
    if hwnd:
        return int(hwnd)
    query = getattr(args, "query", None)
    if query:
        hwnd = _find_window(query)
        if not hwnd:
            _output({"status": "error", "error": f"Window not found: {query}"})
        return hwnd
    _output({"status": "error", "error": "Provide window title or --hwnd"})
    return None


def focus_window(hwnd):
    """Bring window to foreground."""
    _check_win32()
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
        # Alt-key trick to allow SetForegroundWindow from background
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU down
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # VK_MENU up
        win32gui.SetForegroundWindow(hwnd)
        title = win32gui.GetWindowText(hwnd)
        _output({"status": "ok", "action": "focus", "hwnd": hwnd, "title": title})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def resize_window(hwnd, width, height):
    """Resize window keeping current position."""
    _check_win32()
    rect = win32gui.GetWindowRect(hwnd)
    win32gui.MoveWindow(hwnd, rect[0], rect[1], width, height, True)
    title = win32gui.GetWindowText(hwnd)
    _output(
        {
            "status": "ok",
            "action": "resize",
            "hwnd": hwnd,
            "title": title,
            "width": width,
            "height": height,
        }
    )


def move_window(hwnd, x, y):
    """Move window to position."""
    _check_win32()
    rect = win32gui.GetWindowRect(hwnd)
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]
    win32gui.MoveWindow(hwnd, x, y, w, h, True)
    title = win32gui.GetWindowText(hwnd)
    _output({"status": "ok", "action": "move", "hwnd": hwnd, "title": title, "x": x, "y": y})


def minimize_window(hwnd):
    _check_win32()
    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    _output({"status": "ok", "action": "minimize", "hwnd": hwnd})


def maximize_window(hwnd):
    _check_win32()
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    _output({"status": "ok", "action": "maximize", "hwnd": hwnd})


def restore_window(hwnd):
    _check_win32()
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    _output({"status": "ok", "action": "restore", "hwnd": hwnd})


def close_window(hwnd):
    _check_win32()
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    _output({"status": "ok", "action": "close", "hwnd": hwnd})


def snap_window(hwnd, position):
    """Snap window using Windows Snap Assist (Win+Arrow).

    Positions: left, right, top-left, top-right, bottom-left, bottom-right, maximize
    """
    _check_win32()
    import pyautogui

    # Snap mapping: position -> sequence of Win+Arrow keys
    _SNAP_KEYS = {
        "left": [("win", "left")],
        "right": [("win", "right")],
        "maximize": [("win", "up")],
        "top-left": [("win", "left"), ("win", "up")],
        "top-right": [("win", "right"), ("win", "up")],
        "bottom-left": [("win", "left"), ("win", "down")],
        "bottom-right": [("win", "right"), ("win", "down")],
    }

    if position not in _SNAP_KEYS:
        _output(
            {
                "status": "error",
                "error": f"Invalid position: {position}. Use: {', '.join(_SNAP_KEYS.keys())}",
            }
        )
        return

    # 1. Focus and maximize first (resets snap state so snap always works)
    focus_window(hwnd)
    time.sleep(0.2)
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    time.sleep(0.3)

    # 2. Apply snap sequence
    for keys in _SNAP_KEYS[position]:
        pyautogui.hotkey(*keys)
        time.sleep(0.2)

    title = win32gui.GetWindowText(hwnd)
    _output({"status": "ok", "action": "snap", "hwnd": hwnd, "title": title, "position": position})


def handle_command(args):
    """Handle windows subcommands."""
    cmd = args.windows_command
    if cmd == "list":
        list_windows(filter_query=getattr(args, "filter", None))
        return

    if cmd == "snap":
        hwnd = _resolve_hwnd(args)
        if hwnd:
            snap_window(hwnd, args.position)
        return

    if cmd == "layout":
        from pc_control.windows.layouts import handle_command as layout_handle

        layout_handle(args)
        return

    hwnd = _resolve_hwnd(args)
    if not hwnd:
        return

    if cmd == "focus":
        focus_window(hwnd)
    elif cmd == "resize":
        resize_window(hwnd, args.width, args.height)
    elif cmd == "move":
        move_window(hwnd, args.x, args.y)
    elif cmd == "minimize":
        minimize_window(hwnd)
    elif cmd == "maximize":
        maximize_window(hwnd)
    elif cmd == "restore":
        restore_window(hwnd)
    elif cmd == "close":
        close_window(hwnd)
    else:
        print(f"Unknown windows command: {cmd}", file=sys.stderr)
        sys.exit(1)
