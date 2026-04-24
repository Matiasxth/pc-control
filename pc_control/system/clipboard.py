"""Clipboard module — get/set via win32clipboard."""
import json
import sys

try:
    import win32clipboard
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def get_clipboard():
    """Get text content from clipboard."""
    if not HAS_WIN32:
        _output({"status": "error", "error": "pywin32 not available"})
        return
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        else:
            text = None
        win32clipboard.CloseClipboard()
        _output({"status": "ok", "action": "clipboard_get", "text": text})
    except Exception as e:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        _output({"status": "error", "error": str(e)})


def set_clipboard(text: str):
    """Set clipboard text content."""
    if not HAS_WIN32:
        _output({"status": "error", "error": "pywin32 not available"})
        return
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        _output({"status": "ok", "action": "clipboard_set", "length": len(text)})
    except Exception as e:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        _output({"status": "error", "error": str(e)})


def clear_clipboard():
    """Clear clipboard."""
    if not HAS_WIN32:
        _output({"status": "error", "error": "pywin32 not available"})
        return
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.CloseClipboard()
        _output({"status": "ok", "action": "clipboard_clear"})
    except Exception as e:
        try:
            win32clipboard.CloseClipboard()
        except Exception:
            pass
        _output({"status": "error", "error": str(e)})


def handle_command(args):
    """Handle clipboard subcommands."""
    if args.clipboard_command == "get":
        get_clipboard()
    elif args.clipboard_command == "set":
        set_clipboard(args.text)
    elif args.clipboard_command == "clear":
        clear_clipboard()
    else:
        print(f"Unknown clipboard command: {args.clipboard_command}", file=sys.stderr)
        sys.exit(1)
