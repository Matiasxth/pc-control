"""Template matching — find an image/icon on screen."""
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def find_image(template_path: str, screenshot_path: str = None, threshold: float = 0.8):
    """Find a template image on screen."""
    tpl_path = Path(template_path)
    if not tpl_path.exists():
        _output({"status": "error", "error": f"Template not found: {template_path}"})
        return

    # Take screenshot if not provided
    if not screenshot_path:
        from pc_control.screen.capture import screenshot
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        screenshot()
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        try:
            result = json.loads(output)
            screenshot_path = result["path"]
        except Exception:
            _output({"status": "error", "error": "Failed to take screenshot"})
            return

    if HAS_OPENCV:
        _find_opencv(str(tpl_path), screenshot_path, threshold)
    else:
        _find_pil(str(tpl_path), screenshot_path, threshold)


def _find_opencv(template_path: str, screenshot_path: str, threshold: float):
    """Template matching using OpenCV (fast)."""
    screen = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if screen is None or template is None:
        _output({"status": "error", "error": "Could not load images"})
        return

    th, tw = template.shape[:2]
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)

    # Find all matches above threshold
    locations = np.where(result >= threshold)
    matches = []
    seen = set()

    for pt in zip(*locations[::-1]):
        x, y = int(pt[0]), int(pt[1])
        # Deduplicate nearby matches (within 10px)
        key = (x // 10, y // 10)
        if key in seen:
            continue
        seen.add(key)

        confidence = float(result[y, x])
        matches.append({
            "x": x, "y": y, "width": tw, "height": th,
            "center_x": x + tw // 2,
            "center_y": y + th // 2,
            "confidence": round(confidence, 3),
        })

    matches.sort(key=lambda m: m["confidence"], reverse=True)
    matches = matches[:20]  # Limit results

    _output({
        "status": "ok",
        "action": "find_image",
        "engine": "opencv",
        "template": template_path,
        "found": len(matches),
        "matches": matches,
    })


def _find_pil(template_path: str, screenshot_path: str, threshold: float):
    """Template matching using PIL (slower fallback)."""
    screen = Image.open(screenshot_path).convert("L")
    template = Image.open(template_path).convert("L")

    # Downscale for speed
    scale = 2
    sw, sh = screen.size[0] // scale, screen.size[1] // scale
    tw, th = template.size[0] // scale, template.size[1] // scale

    if tw < 5 or th < 5:
        _output({"status": "error", "error": "Template too small"})
        return

    screen_small = screen.resize((sw, sh))
    tpl_small = template.resize((tw, th))

    screen_arr = np.array(screen_small, dtype=np.float32)
    tpl_arr = np.array(tpl_small, dtype=np.float32)
    tpl_mean = tpl_arr.mean()
    tpl_std = tpl_arr.std()

    if tpl_std < 1:
        _output({"status": "error", "error": "Template has no contrast"})
        return

    matches = []
    # Slide template across screen
    for y in range(0, sh - th, 4):
        for x in range(0, sw - tw, 4):
            region = screen_arr[y:y + th, x:x + tw]
            region_mean = region.mean()
            region_std = region.std()
            if region_std < 1:
                continue
            ncc = np.mean((region - region_mean) * (tpl_arr - tpl_mean)) / (region_std * tpl_std)
            if ncc >= threshold:
                matches.append({
                    "x": x * scale, "y": y * scale,
                    "width": tw * scale, "height": th * scale,
                    "center_x": (x + tw // 2) * scale,
                    "center_y": (y + th // 2) * scale,
                    "confidence": round(float(ncc), 3),
                })

    matches.sort(key=lambda m: m["confidence"], reverse=True)
    matches = matches[:10]

    _output({
        "status": "ok",
        "action": "find_image",
        "engine": "pil_fallback",
        "template": template_path,
        "found": len(matches),
        "matches": matches,
    })
