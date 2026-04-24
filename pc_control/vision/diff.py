"""Screen diffing — compare screenshots using PIL + numpy."""

import io
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from pc_control.config import SCREENSHOTS_DIR

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def diff_screenshots(path1: str, path2: str, threshold: int = 30):
    """Compare two images and report changes."""
    p1, p2 = Path(path1), Path(path2)
    if not p1.exists():
        _output({"status": "error", "error": f"File not found: {path1}"})
        return
    if not p2.exists():
        _output({"status": "error", "error": f"File not found: {path2}"})
        return

    img1 = Image.open(p1).convert("L")  # grayscale
    img2 = Image.open(p2).convert("L")

    # Resize to match if needed
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    arr1 = np.array(img1, dtype=np.int16)
    arr2 = np.array(img2, dtype=np.int16)

    diff = np.abs(arr1 - arr2)
    changed_mask = diff > threshold

    total_pixels = changed_mask.size
    changed_pixels = int(np.sum(changed_mask))
    change_percent = round(changed_pixels / total_pixels * 100, 2)

    # Find bounding boxes of changed regions
    regions = _find_regions(changed_mask)

    # Generate highlighted diff image
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    diff_path = SCREENSHOTS_DIR / f"diff_{ts}.png"
    _save_diff_image(Image.open(p2).convert("RGB"), regions, diff_path)

    _output(
        {
            "status": "ok",
            "action": "diff",
            "change_percent": change_percent,
            "changed_pixels": changed_pixels,
            "total_pixels": total_pixels,
            "regions": len(regions),
            "bounding_boxes": regions,
            "diff_image": str(diff_path.resolve()),
        }
    )


def diff_screen(reference: str = None):
    """Take a screenshot and compare to a reference or the previous screenshot."""
    from pc_control.screen.capture import screenshot

    # Take new screenshot
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    screenshot()
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    try:
        result = json.loads(output)
        new_path = result["path"]
    except Exception:
        _output({"status": "error", "error": "Failed to take screenshot"})
        return

    if reference:
        ref_path = reference
    else:
        # Find the most recent previous screenshot
        screenshots = sorted(SCREENSHOTS_DIR.glob("screen_*.png"))
        screenshots = [s for s in screenshots if str(s.resolve()) != new_path]
        if not screenshots:
            _output(
                {
                    "status": "error",
                    "error": "No previous screenshot to compare against. Provide --reference",
                }
            )
            return
        ref_path = str(screenshots[-1])

    diff_screenshots(ref_path, new_path)


def _find_regions(mask: np.ndarray, min_size: int = 50) -> list:
    """Find bounding boxes of changed regions using connected components."""
    regions = []
    visited = np.zeros_like(mask, dtype=bool)
    rows, cols = mask.shape

    for y in range(0, rows, 10):  # Sample every 10 pixels for speed
        for x in range(0, cols, 10):
            if mask[y, x] and not visited[y, x]:
                # Flood fill to find region bounds
                min_y, max_y, min_x, max_x = y, y, x, x
                stack = [(y, x)]
                count = 0
                while stack and count < 5000:
                    cy, cx = stack.pop()
                    if cy < 0 or cy >= rows or cx < 0 or cx >= cols:
                        continue
                    if visited[cy, cx] or not mask[cy, cx]:
                        continue
                    visited[cy, cx] = True
                    count += 1
                    min_y, max_y = min(min_y, cy), max(max_y, cy)
                    min_x, max_x = min(min_x, cx), max(max_x, cx)
                    for dy, dx in [(-5, 0), (5, 0), (0, -5), (0, 5)]:
                        stack.append((cy + dy, cx + dx))

                w = max_x - min_x
                h = max_y - min_y
                if w >= min_size or h >= min_size:
                    regions.append(
                        {"x": int(min_x), "y": int(min_y), "width": int(w), "height": int(h)}
                    )

    return regions


def _save_diff_image(img: Image.Image, regions: list, path: Path):
    """Draw red rectangles on changed regions."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    for r in regions:
        x, y, w, h = r["x"], r["y"], r["width"], r["height"]
        draw.rectangle([x, y, x + w, y + h], outline="red", width=3)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))
