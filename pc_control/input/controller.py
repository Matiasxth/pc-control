"""Mouse and keyboard control via pyautogui."""

from __future__ import annotations

import json
import math
import sys
import time
from argparse import Namespace

import pyautogui

# Safety: disable pause between actions for speed, keep failsafe
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True


def _output(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


# ── Mouse ───────────────────────────────────────────────────


def mouse_click(x: int, y: int, button: str = "left", double: bool = False) -> None:
    """Move to `(x, y)` and click with the given mouse button."""
    clicks = 2 if double else 1
    pyautogui.click(x, y, clicks=clicks, button=button)
    _output(
        {
            "status": "ok",
            "action": "click",
            "x": x,
            "y": y,
            "button": button,
            "double": double,
        }
    )


def mouse_move(x: int, y: int, duration: float = 0.2) -> None:
    """Move the cursor to `(x, y)` over `duration` seconds."""
    pyautogui.moveTo(x, y, duration=duration)
    _output({"status": "ok", "action": "move", "x": x, "y": y})


def mouse_drag(
    x1: int, y1: int, x2: int, y2: int, duration: float = 0.5, button: str = "left"
) -> None:
    """Drag from `(x1, y1)` to `(x2, y2)` holding `button` the whole time."""
    pyautogui.moveTo(x1, y1, duration=0.1)
    pyautogui.drag(x2 - x1, y2 - y1, duration=duration, button=button)
    _output({"status": "ok", "action": "drag", "from": [x1, y1], "to": [x2, y2]})


def mouse_scroll(dx: int, dy: int) -> None:
    """Scroll `dy` vertical / `dx` horizontal clicks at the current position."""
    if dy != 0:
        pyautogui.scroll(dy)
    if dx != 0:
        pyautogui.hscroll(dx)
    _output({"status": "ok", "action": "scroll", "dx": dx, "dy": dy})


def mouse_position() -> None:
    """Emit the current cursor position."""
    x, y = pyautogui.position()
    _output({"status": "ok", "action": "position", "x": x, "y": y})


# ── Keyboard ────────────────────────────────────────────────


def keyboard_type(text: str, interval: float = 0.02) -> None:
    """Type `text` one character at a time with `interval` seconds between keys."""
    pyautogui.write(text, interval=interval)
    _output({"status": "ok", "action": "type", "length": len(text)})


def keyboard_key(key_name: str) -> None:
    """Press and release a single named key (e.g. `"enter"`, `"tab"`)."""
    pyautogui.press(key_name)
    _output({"status": "ok", "action": "key", "key": key_name})


def keyboard_hotkey(keys: list[str]) -> None:
    """Press a chord like `["ctrl", "c"]` — keys are held in order and released together."""
    pyautogui.hotkey(*keys)
    _output({"status": "ok", "action": "hotkey", "keys": keys})


def smooth_move(x: int, y: int, duration: float = 0.5, curve: str = "ease") -> None:
    """Move the cursor to `(x, y)` using an easing curve instead of linear motion.

    Args:
        x, y: Target screen coordinates.
        duration: Total animation time in seconds.
        curve: One of `"ease"` (smoothstep), `"ease-in"`, `"ease-out"`,
            `"ease-in-out"` (cosine), or `"linear"`.
    """
    sx, sy = pyautogui.position()
    steps = max(int(duration * 100), 10)

    for i in range(1, steps + 1):
        t = i / steps
        if curve == "ease":
            t = t * t * (3 - 2 * t)  # smoothstep
        elif curve == "ease-in":
            t = t * t
        elif curve == "ease-out":
            t = 1 - (1 - t) ** 2
        elif curve == "ease-in-out":
            t = 0.5 * (1 - math.cos(math.pi * t))

        cx = int(sx + (x - sx) * t)
        cy = int(sy + (y - sy) * t)
        pyautogui.moveTo(cx, cy, duration=0)
        time.sleep(duration / steps)

    _output({"status": "ok", "action": "smooth_move", "x": x, "y": y, "curve": curve})


def draw_path(points: list, duration: float = 1.0, hold_click: bool = True) -> None:
    """Draw a smooth Catmull-Rom curve through `points`, optionally dragging.

    Args:
        points: List of `[x, y]` pairs or `"x,y"` strings. At least 2 points
            are required.
        duration: Total animation time in seconds.
        hold_click: When True, the left mouse button is held down for the
            duration of the stroke (produces a drag).
    """
    if not points:
        _output({"status": "error", "error": "No points provided"})
        return

    parsed: list[list[int]] = []
    for p in points:
        if isinstance(p, str):
            parts = [int(x.strip()) for x in p.split(",")]
            parsed.append(parts)
        elif isinstance(p, (list, tuple)):
            parsed.append([int(p[0]), int(p[1])])

    if len(parsed) < 2:
        _output({"status": "error", "error": "Need at least 2 points"})
        return

    def catmull_rom(p0, p1, p2, p3, t: float) -> tuple[int, int]:
        t2 = t * t
        t3 = t2 * t
        x = 0.5 * (
            (2 * p1[0])
            + (-p0[0] + p2[0]) * t
            + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
            + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
        )
        y = 0.5 * (
            (2 * p1[1])
            + (-p0[1] + p2[1]) * t
            + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
            + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
        )
        return int(x), int(y)

    smooth: list[tuple[int, int]] = []
    # Phantom points at start and end so the spline has control on both ends.
    pts = [parsed[0]] + parsed + [parsed[-1]]
    segments = len(pts) - 3
    points_per_seg = max(5, int(60 / segments))

    for i in range(segments):
        for t_step in range(points_per_seg):
            t = t_step / points_per_seg
            p = catmull_rom(pts[i], pts[i + 1], pts[i + 2], pts[i + 3], t)
            smooth.append(p)
    smooth.append((parsed[-1][0], parsed[-1][1]))

    delay = duration / max(len(smooth), 1)

    pyautogui.moveTo(smooth[0][0], smooth[0][1], duration=0)
    if hold_click:
        pyautogui.mouseDown()

    for px, py in smooth[1:]:
        pyautogui.moveTo(px, py, duration=0)
        time.sleep(delay)

    if hold_click:
        pyautogui.mouseUp()

    _output(
        {
            "status": "ok",
            "action": "draw_path",
            "points_input": len(parsed),
            "points_smooth": len(smooth),
            "duration": duration,
        }
    )


# ── Dispatcher ──────────────────────────────────────────────


def handle_command(args: Namespace) -> None:
    """Dispatch `input <subcommand>` to the right handler."""
    cmd = args.input_command

    if cmd == "click":
        mouse_click(
            args.x,
            args.y,
            button=getattr(args, "button", "left"),
            double=getattr(args, "double", False),
        )
    elif cmd == "move":
        mouse_move(args.x, args.y, duration=getattr(args, "duration", 0.2))
    elif cmd == "drag":
        mouse_drag(
            args.x1,
            args.y1,
            args.x2,
            args.y2,
            duration=getattr(args, "duration", 0.5),
            button=getattr(args, "button", "left"),
        )
    elif cmd == "scroll":
        mouse_scroll(args.dx, args.dy)
    elif cmd == "position":
        mouse_position()
    elif cmd == "type":
        keyboard_type(args.text, interval=getattr(args, "interval", 0.02))
    elif cmd == "key":
        keyboard_key(args.key_name)
    elif cmd == "hotkey":
        keyboard_hotkey(args.keys)
    elif cmd == "smooth":
        smooth_move(
            args.x,
            args.y,
            duration=getattr(args, "duration", 0.5),
            curve=getattr(args, "curve", "ease"),
        )
    elif cmd == "draw":
        draw_path(
            args.points,
            duration=getattr(args, "duration", 1.0),
            hold_click=not getattr(args, "no_click", False),
        )
    else:
        print(f"Unknown input command: {cmd}", file=sys.stderr)
        sys.exit(1)
