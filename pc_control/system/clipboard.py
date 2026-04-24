"""Clipboard read/write via the Win32 clipboard API."""

from __future__ import annotations

import json
import sys
from argparse import Namespace

try:
    import win32clipboard
    import win32con

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


def _output(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def _close_silently() -> None:
    """Close the clipboard, swallowing any errors. Used after failures where
    the clipboard may or may not still be open."""
    try:
        win32clipboard.CloseClipboard()
    except Exception:
        pass


def get_clipboard() -> None:
    """Print the current Unicode text on the clipboard (or `null` if none)."""
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
        _close_silently()
        _output({"status": "error", "error": str(e)})


def set_clipboard(text: str) -> None:
    """Replace clipboard contents with `text` (Unicode)."""
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
        _close_silently()
        _output({"status": "error", "error": str(e)})


def clear_clipboard() -> None:
    """Empty the clipboard."""
    if not HAS_WIN32:
        _output({"status": "error", "error": "pywin32 not available"})
        return
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.CloseClipboard()
        _output({"status": "ok", "action": "clipboard_clear"})
    except Exception as e:
        _close_silently()
        _output({"status": "error", "error": str(e)})


def handle_command(args: Namespace) -> None:
    """Dispatch `clipboard <subcommand>` to the right handler."""
    if args.clipboard_command == "get":
        get_clipboard()
    elif args.clipboard_command == "set":
        set_clipboard(args.text)
    elif args.clipboard_command == "clear":
        clear_clipboard()
    else:
        print(f"Unknown clipboard command: {args.clipboard_command}", file=sys.stderr)
        sys.exit(1)
