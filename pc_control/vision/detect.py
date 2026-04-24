"""Element and text detection — find text/elements on screen with coordinates."""
import asyncio
import io
import json
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


async def _ocr_with_bounds_async(image_path: str, language: str = "es") -> dict:
    """Run OCR and return text with bounding rectangles."""
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage import FileAccessMode, StorageFile

    abs_path = str(Path(image_path).resolve())
    file = await StorageFile.get_file_from_path_async(abs_path)
    stream = await file.open_async(FileAccessMode.READ)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()

    lang = Language(language)
    engine = OcrEngine.try_create_from_language(lang)
    if engine is None:
        engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError(f"OCR not available for language: {language}")

    result = await engine.recognize_async(bitmap)
    stream.close()

    lines = []
    for line in result.lines:
        words = []
        for word in line.words:
            rect = word.bounding_rect
            words.append({
                "text": word.text,
                "bounds": {"x": int(rect.x), "y": int(rect.y),
                           "width": int(rect.width), "height": int(rect.height)},
            })
        # Line bounds from first/last word
        if words:
            lx = words[0]["bounds"]["x"]
            ly = min(w["bounds"]["y"] for w in words)
            lw = words[-1]["bounds"]["x"] + words[-1]["bounds"]["width"] - lx
            lh = max(w["bounds"]["y"] + w["bounds"]["height"] for w in words) - ly
            lines.append({
                "text": " ".join(w["text"] for w in words),
                "bounds": {"x": lx, "y": ly, "width": lw, "height": lh},
                "words": words,
            })

    return {"text": result.text, "lines": lines}


def find_text(query: str, region=None, window=None, language="es"):
    """Find text on screen and return its coordinates."""
    # Take screenshot
    from pc_control.screen.capture import screenshot
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    screenshot(region=region, window=window)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    try:
        result = json.loads(output)
        image_path = result["path"]
    except Exception:
        _output({"status": "error", "error": "Failed to take screenshot"})
        return

    # Run OCR with bounds
    try:
        ocr_result = asyncio.run(_ocr_with_bounds_async(image_path, language))
    except Exception as e:
        _output({"status": "error", "error": f"OCR failed: {e}"})
        return

    # Search for query in OCR results
    query_lower = query.lower()
    matches = []

    for line in ocr_result["lines"]:
        if query_lower in line["text"].lower():
            matches.append({
                "text": line["text"],
                "bounds": line["bounds"],
                "center_x": line["bounds"]["x"] + line["bounds"]["width"] // 2,
                "center_y": line["bounds"]["y"] + line["bounds"]["height"] // 2,
            })

        # Also check individual words
        for word in line["words"]:
            if query_lower in word["text"].lower() and not any(
                m["text"] == word["text"] for m in matches
            ):
                matches.append({
                    "text": word["text"],
                    "bounds": word["bounds"],
                    "center_x": word["bounds"]["x"] + word["bounds"]["width"] // 2,
                    "center_y": word["bounds"]["y"] + word["bounds"]["height"] // 2,
                })

    _output({
        "status": "ok",
        "action": "find_text",
        "query": query,
        "found": len(matches),
        "matches": matches,
        "screenshot": image_path,
    })


def detect_elements(region=None, window=None, language="es"):
    """Detect UI elements on screen using OCR bounding boxes."""
    from pc_control.screen.capture import screenshot
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    screenshot(region=region, window=window)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    try:
        result = json.loads(output)
        image_path = result["path"]
    except Exception:
        _output({"status": "error", "error": "Failed to take screenshot"})
        return

    try:
        ocr_result = asyncio.run(_ocr_with_bounds_async(image_path, language))
    except Exception as e:
        _output({"status": "error", "error": f"OCR failed: {e}"})
        return

    elements = []
    for line in ocr_result["lines"]:
        text = line["text"].strip()
        if not text:
            continue

        # Classify element type heuristically
        b = line["bounds"]
        is_short = len(text) < 30
        is_small = b["height"] < 40

        if is_short and is_small:
            elem_type = "button_or_label"
        elif b["width"] > 200 and b["height"] < 30:
            elem_type = "text_field"
        else:
            elem_type = "text"

        elements.append({
            "text": text,
            "type": elem_type,
            "bounds": b,
            "center_x": b["x"] + b["width"] // 2,
            "center_y": b["y"] + b["height"] // 2,
        })

    _output({
        "status": "ok",
        "action": "elements",
        "count": len(elements),
        "elements": elements,
        "screenshot": image_path,
    })
