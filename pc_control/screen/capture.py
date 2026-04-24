"""Screen capture module — screenshots via PIL.ImageGrab + win32gui."""
import json
import sys
from datetime import datetime
from pathlib import Path

from PIL import ImageGrab

from pc_control.config import SCREENSHOT_FORMAT, SCREENSHOT_QUALITY, SCREENSHOTS_DIR

try:
    import win32con
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _generate_filename(prefix: str = "screen", fmt: str = None) -> Path:
    fmt = fmt or SCREENSHOT_FORMAT
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return SCREENSHOTS_DIR / f"{prefix}_{ts}.{fmt}"


def _find_window(title_query: str) -> int | None:
    """Find window handle by partial title match (case-insensitive)."""
    if not HAS_WIN32:
        return None
    results = []
    query_lower = title_query.lower()

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and query_lower in title.lower():
                results.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, None)
    return results[0][0] if results else None


def screenshot(region=None, window=None, output=None, fmt=None, quality=None):
    """Take a screenshot and save it."""
    fmt = fmt or SCREENSHOT_FORMAT
    quality = quality or SCREENSHOT_QUALITY
    output_path = Path(output) if output else _generate_filename(fmt=fmt)

    bbox = None

    if region:
        # Parse "x1,y1,x2,y2"
        parts = [int(x.strip()) for x in region.split(",")]
        if len(parts) == 4:
            bbox = tuple(parts)
        else:
            _output({"status": "error", "error": "Region must be x1,y1,x2,y2"})
            return

    elif window:
        if not HAS_WIN32:
            _output({"status": "error", "error": "pywin32 not available"})
            return
        hwnd = _find_window(window)
        if not hwnd:
            _output({"status": "error", "error": f"Window not found: {window}"})
            return
        # Restore if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        rect = win32gui.GetWindowRect(hwnd)
        bbox = rect  # (left, top, right, bottom)

    img = ImageGrab.grab(bbox=bbox, all_screens=True)

    save_kwargs = {}
    if fmt == "jpeg":
        save_kwargs["quality"] = quality

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), **save_kwargs)

    _output({
        "status": "ok",
        "action": "screenshot",
        "path": str(output_path.resolve()),
        "size": list(img.size),
        "format": fmt,
    })


def handle_command(args):
    """Handle screen subcommands."""
    if args.screen_command == "context":
        from pc_control.screen.context import get_context
        get_context()
        return

    if args.screen_command == "shot":
        screenshot(
            region=getattr(args, "region", None),
            window=getattr(args, "window", None),
            output=getattr(args, "output", None),
            fmt=getattr(args, "format", None),
            quality=getattr(args, "quality", None),
        )
    else:
        print(f"Unknown screen command: {args.screen_command}", file=sys.stderr)
        sys.exit(1)
