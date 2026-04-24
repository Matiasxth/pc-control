"""Window layouts — save and restore window arrangements."""
import io
import json
import sys
import time

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

from pc_control.config import PROJECT_ROOT

LAYOUTS_DIR = PROJECT_ROOT / ".layouts"
LAYOUTS_DIR.mkdir(exist_ok=True)


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


def save_layout(name: str):
    """Save current window arrangement."""
    if not HAS_WIN32:
        _output({"status": "error", "error": "pywin32 not available"})
        return

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
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w <= 0 and h <= 0 and state != "minimized":
            return True

        windows.append({
            "process": proc,
            "title": title,
            "state": state,
            "rect": {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3]},
            "width": w,
            "height": h,
        })
        return True

    win32gui.EnumWindows(callback, None)

    layout = {"name": name, "window_count": len(windows), "windows": windows}
    path = LAYOUTS_DIR / f"{name}.json"
    path.write_text(json.dumps(layout, indent=2, ensure_ascii=False), encoding="utf-8")

    _output({"status": "ok", "action": "layout_save", "name": name, "windows": len(windows), "path": str(path)})


def load_layout(name: str):
    """Restore a saved window arrangement."""
    if not HAS_WIN32:
        _output({"status": "error", "error": "pywin32 not available"})
        return

    path = LAYOUTS_DIR / f"{name}.json"
    if not path.exists():
        _output({"status": "error", "error": f"Layout not found: {name}"})
        return

    layout = json.loads(path.read_text(encoding="utf-8"))
    restored = 0
    skipped = 0

    for saved in layout["windows"]:
        # Find matching window by process name
        hwnd = _find_window_by_process(saved["process"])
        if not hwnd:
            skipped += 1
            continue

        state = saved["state"]
        rect = saved["rect"]

        try:
            if state == "maximized":
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            elif state == "minimized":
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            else:
                # Restore first in case it's maximized/minimized
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)
                w = rect["right"] - rect["left"]
                h = rect["bottom"] - rect["top"]
                win32gui.MoveWindow(hwnd, rect["left"], rect["top"], w, h, True)
            restored += 1
        except Exception:
            skipped += 1

    _output({"status": "ok", "action": "layout_load", "name": name, "restored": restored, "skipped": skipped})


def list_layouts():
    """List saved layouts."""
    layouts = []
    for f in sorted(LAYOUTS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            layouts.append({"name": f.stem, "windows": data.get("window_count", 0)})
        except Exception:
            layouts.append({"name": f.stem, "windows": "?"})

    _output({"status": "ok", "action": "layout_list", "count": len(layouts), "layouts": layouts})


def delete_layout(name: str):
    """Delete a saved layout."""
    path = LAYOUTS_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
        _output({"status": "ok", "action": "layout_delete", "name": name})
    else:
        _output({"status": "error", "error": f"Layout not found: {name}"})


def _find_window_by_process(process_name: str) -> int | None:
    """Find first visible window matching process name."""
    result = [None]

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            proc = psutil.Process(pid).name()
            if proc.lower() == process_name.lower():
                result[0] = hwnd
                return False
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(callback, None)
    except Exception:
        pass
    return result[0]


def handle_command(args):
    cmd = args.layout_command
    if cmd == "save":
        save_layout(args.name)
    elif cmd == "load":
        load_layout(args.name)
    elif cmd == "list":
        list_layouts()
    elif cmd == "delete":
        delete_layout(args.name)
    else:
        print(f"Unknown layout command: {cmd}", file=sys.stderr)
        sys.exit(1)
