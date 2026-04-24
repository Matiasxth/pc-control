"""OCR module — Windows.Media.Ocr via Python WinRT bindings."""
import asyncio
import io
import json
import sys
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


async def _ocr_async(image_path: str, language: str = "es") -> str:
    """Run Windows OCR on an image file."""
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage import StorageFile, FileAccessMode
    from winrt.windows.globalization import Language

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
    return result.text


def ocr_file(image_path, language="es"):
    """Run OCR on an image file."""
    path = Path(image_path)
    if not path.exists():
        _output({"status": "error", "error": f"File not found: {image_path}"})
        return

    try:
        text = asyncio.run(_ocr_async(str(path), language))
        _output({"status": "ok", "action": "ocr", "text": text, "file": str(path.resolve()), "length": len(text)})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def ocr_screen(region=None, window=None, language="es"):
    """Take a screenshot and run OCR on it."""
    from pc_control.screen.capture import screenshot

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    screenshot(region=region, window=window)
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout

    try:
        result = json.loads(output)
        if result.get("status") != "ok":
            _output(result)
            return
        image_path = result["path"]
    except Exception:
        _output({"status": "error", "error": "Failed to take screenshot"})
        return

    ocr_file(image_path, language=language)


def handle_command(args):
    """Handle OCR subcommands."""
    cmd = args.ocr_command
    if cmd == "file":
        ocr_file(args.path, language=getattr(args, "lang", "es"))
    elif cmd == "screen":
        ocr_screen(
            region=getattr(args, "region", None),
            window=getattr(args, "window", None),
            language=getattr(args, "lang", "es"),
        )
    else:
        print(f"Unknown OCR command: {cmd}", file=sys.stderr)
        sys.exit(1)
