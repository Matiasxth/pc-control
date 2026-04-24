"""Screen capture — PIL.ImageGrab for full/region, win32gui for window bounds."""
from __future__ import annotations

import json
import sys
from argparse import Namespace
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


def _output(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def _generate_filename(prefix: str = "screen", fmt: str | None = None) -> Path:
    """Build a timestamped path inside SCREENSHOTS_DIR (not yet written)."""
    fmt = fmt or SCREENSHOT_FORMAT
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return SCREENSHOTS_DIR / f"{prefix}_{ts}.{fmt}"


def _find_window(title_query: str) -> int | None:
    """Return HWND of first visible window whose title contains `title_query`
    (case-insensitive), or None if pywin32 is unavailable or no match is found.
    """
    if not HAS_WIN32:
        return None
    results: list[tuple[int, str]] = []
    query_lower = title_query.lower()

    def callback(hwnd: int, _: object) -> bool:
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and query_lower in title.lower():
                results.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, None)
    return results[0][0] if results else None


def screenshot(
    region: str | None = None,
    window: str | None = None,
    output: str | None = None,
    fmt: str | None = None,
    quality: int | None = None,
) -> None:
    """Capture a screenshot and write it to disk.

    Exactly one of `region`, `window`, or neither may be set. When neither is
    given the capture spans all monitors.

    Args:
        region: Bounding box as `"x1,y1,x2,y2"` (screen coords). Wins over `window`.
        window: Partial window title; the matched window is restored if minimized.
        output: Destination path. When omitted a timestamped file is created under
            `SCREENSHOTS_DIR`.
        fmt: Output format (`"png"` or `"jpeg"`). Defaults to `SCREENSHOT_FORMAT`.
        quality: JPEG quality (1–100). Ignored for PNG.

    Emits a JSON record on stdout with `status`, `path`, and image `size`.
    """
    fmt = fmt or SCREENSHOT_FORMAT
    quality = quality or SCREENSHOT_QUALITY
    output_path = Path(output) if output else _generate_filename(fmt=fmt)

    bbox: tuple[int, int, int, int] | None = None

    if region:
        parts = [int(x.strip()) for x in region.split(",")]
        if len(parts) == 4:
            bbox = (parts[0], parts[1], parts[2], parts[3])
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
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        bbox = win32gui.GetWindowRect(hwnd)

    img = ImageGrab.grab(bbox=bbox, all_screens=True)

    save_kwargs: dict = {}
    if fmt == "jpeg":
        save_kwargs["quality"] = quality

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), **save_kwargs)

    _output(
        {
            "status": "ok",
            "action": "screenshot",
            "path": str(output_path.resolve()),
            "size": list(img.size),
            "format": fmt,
        }
    )


def handle_command(args: Namespace) -> None:
    """Dispatch `screen <subcommand>` to the right handler."""
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
