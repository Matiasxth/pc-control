"""Mouse and keyboard control via pyautogui."""
import json
import sys
import time

import pyautogui

# Safety: disable pause between actions for speed, keep failsafe
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


# ── Mouse ───────────────────────────────────────────────────

def mouse_click(x, y, button="left", double=False):
    clicks = 2 if double else 1
    pyautogui.click(x, y, clicks=clicks, button=button)
    _output({"status": "ok", "action": "click", "x": x, "y": y, "button": button, "double": double})


def mouse_move(x, y, duration=0.2):
    pyautogui.moveTo(x, y, duration=duration)
    _output({"status": "ok", "action": "move", "x": x, "y": y})


def mouse_drag(x1, y1, x2, y2, duration=0.5, button="left"):
    pyautogui.moveTo(x1, y1, duration=0.1)
    pyautogui.drag(x2 - x1, y2 - y1, duration=duration, button=button)
    _output({"status": "ok", "action": "drag", "from": [x1, y1], "to": [x2, y2]})


def mouse_scroll(dx, dy):
    if dy != 0:
        pyautogui.scroll(dy)
    if dx != 0:
        pyautogui.hscroll(dx)
    _output({"status": "ok", "action": "scroll", "dx": dx, "dy": dy})


def mouse_position():
    x, y = pyautogui.position()
    _output({"status": "ok", "action": "position", "x": x, "y": y})


# ── Keyboard ────────────────────────────────────────────────

def keyboard_type(text, interval=0.02):
    pyautogui.write(text, interval=interval)
    _output({"status": "ok", "action": "type", "length": len(text)})


def keyboard_key(key_name):
    pyautogui.press(key_name)
    _output({"status": "ok", "action": "key", "key": key_name})


def keyboard_hotkey(keys):
    pyautogui.hotkey(*keys)
    _output({"status": "ok", "action": "hotkey", "keys": keys})


def smooth_move(x, y, duration=0.5, curve="ease"):
    """Move mouse smoothly to (x, y) with easing curves."""
    import math
    sx, sy = pyautogui.position()
    steps = max(int(duration * 100), 10)

    for i in range(1, steps + 1):
        t = i / steps
        # Apply easing
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


def draw_path(points, duration=1.0, hold_click=True):
    """Draw a smooth path through a list of points with mouse held down.

    Points: list of [x, y] or "x,y" strings.
    Uses Catmull-Rom spline interpolation for smooth curves.
    """
    if not points:
        _output({"status": "error", "error": "No points provided"})
        return

    # Parse points
    parsed = []
    for p in points:
        if isinstance(p, str):
            parts = [int(x.strip()) for x in p.split(",")]
            parsed.append(parts)
        elif isinstance(p, (list, tuple)):
            parsed.append([int(p[0]), int(p[1])])

    if len(parsed) < 2:
        _output({"status": "error", "error": "Need at least 2 points"})
        return

    # Catmull-Rom spline interpolation
    def catmull_rom(p0, p1, p2, p3, t):
        t2 = t * t
        t3 = t2 * t
        x = 0.5 * ((2 * p1[0]) +
                    (-p0[0] + p2[0]) * t +
                    (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                    (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
        y = 0.5 * ((2 * p1[1]) +
                    (-p0[1] + p2[1]) * t +
                    (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                    (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
        return int(x), int(y)

    # Generate smooth points using Catmull-Rom
    smooth = []
    # Add phantom points at start and end for the spline
    pts = [parsed[0]] + parsed + [parsed[-1]]
    segments = len(pts) - 3
    points_per_seg = max(5, int(60 / segments))

    for i in range(segments):
        for t_step in range(points_per_seg):
            t = t_step / points_per_seg
            p = catmull_rom(pts[i], pts[i + 1], pts[i + 2], pts[i + 3], t)
            smooth.append(p)
    smooth.append(parsed[-1])

    # Draw
    total_time = duration
    delay = total_time / max(len(smooth), 1)

    pyautogui.moveTo(smooth[0][0], smooth[0][1], duration=0)
    if hold_click:
        pyautogui.mouseDown()

    for px, py in smooth[1:]:
        pyautogui.moveTo(px, py, duration=0)
        time.sleep(delay)

    if hold_click:
        pyautogui.mouseUp()

    _output({
        "status": "ok",
        "action": "draw_path",
        "points_input": len(parsed),
        "points_smooth": len(smooth),
        "duration": duration,
    })


# ── Dispatcher ──────────────────────────────────────────────

def handle_command(args):
    cmd = args.input_command

    if cmd == "click":
        mouse_click(args.x, args.y,
                     button=getattr(args, "button", "left"),
                     double=getattr(args, "double", False))
    elif cmd == "move":
        mouse_move(args.x, args.y, duration=getattr(args, "duration", 0.2))
    elif cmd == "drag":
        mouse_drag(args.x1, args.y1, args.x2, args.y2,
                    duration=getattr(args, "duration", 0.5),
                    button=getattr(args, "button", "left"))
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
        smooth_move(args.x, args.y,
                     duration=getattr(args, "duration", 0.5),
                     curve=getattr(args, "curve", "ease"))
    elif cmd == "draw":
        draw_path(args.points,
                   duration=getattr(args, "duration", 1.0),
                   hold_click=not getattr(args, "no_click", False))
    else:
        print(f"Unknown input command: {cmd}", file=sys.stderr)
        sys.exit(1)
