"""Screen diffing — compare screenshots using PIL + numpy."""

from __future__ import annotations

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


def _output(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def diff_screenshots(path1: str, path2: str, threshold: int = 30) -> None:
    """Compare two image files and emit a summary of the changed regions.

    The images are converted to grayscale and resized to match (image 2 is
    resized to image 1's dimensions when they differ). A pixel counts as
    "changed" when its absolute intensity difference exceeds `threshold`
    (0–255). The response includes:

      - `change_percent` — ratio of changed pixels, 0-100
      - `regions` / `bounding_boxes` — connected components above a minimum
        size, as `{x, y, width, height}` in image-1 coordinates
      - `diff_image` — path to a copy of image 2 with red rectangles drawn
        over the changed regions
    """
    p1, p2 = Path(path1), Path(path2)
    if not p1.exists():
        _output({"status": "error", "error": f"File not found: {path1}"})
        return
    if not p2.exists():
        _output({"status": "error", "error": f"File not found: {path2}"})
        return

    img1 = Image.open(p1).convert("L")
    img2 = Image.open(p2).convert("L")

    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    arr1 = np.array(img1, dtype=np.int16)
    arr2 = np.array(img2, dtype=np.int16)

    diff = np.abs(arr1 - arr2)
    changed_mask = diff > threshold

    total_pixels = changed_mask.size
    changed_pixels = int(np.sum(changed_mask))
    change_percent = round(changed_pixels / total_pixels * 100, 2)

    regions = _find_regions(changed_mask)

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


def diff_screen(reference: str | None = None) -> None:
    """Take a fresh screenshot and compare it against `reference` (or the most
    recent previous screenshot under `SCREENSHOTS_DIR`).

    When `reference` is omitted and there is no earlier screenshot available,
    emits an error asking the caller to supply one.
    """
    from pc_control.screen.capture import screenshot

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


def _find_regions(mask: np.ndarray, min_size: int = 50) -> list[dict]:
    """Return bounding boxes of changed-pixel regions via sampled flood fill.

    The mask is sampled on a 10-pixel grid and each seed triggers a bounded
    flood fill (capped at 5000 cells) with a 5-pixel stride. This is a
    speed/accuracy trade — precise region counts aren't the goal; coarse
    bounding boxes are.
    """
    regions: list[dict] = []
    visited = np.zeros_like(mask, dtype=bool)
    rows, cols = mask.shape

    for y in range(0, rows, 10):
        for x in range(0, cols, 10):
            if mask[y, x] and not visited[y, x]:
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


def _save_diff_image(img: Image.Image, regions: list[dict], path: Path) -> None:
    """Draw red outlines on `img` around each region and save to `path`."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    for r in regions:
        x, y, w, h = r["x"], r["y"], r["width"], r["height"]
        draw.rectangle([x, y, x + w, y + h], outline="red", width=3)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path))
