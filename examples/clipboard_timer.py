"""Refresh the clipboard with an ISO timestamp every N seconds.

Useful as a live "copy current time" helper while writing notes. Ctrl+C to stop.

Usage:
    python examples/clipboard_timer.py --interval 5

Windows only (pywin32).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime


def set_clipboard(text: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "pc_control", "clipboard", "set", text],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "error": result.stderr.strip() or "no output"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--interval", type=float, default=5.0, help="Seconds between updates"
    )
    parser.add_argument(
        "--once", action="store_true", help="Update once and exit"
    )
    args = parser.parse_args()

    try:
        while True:
            stamp = datetime.now().isoformat(timespec="seconds")
            result = set_clipboard(stamp)
            if result.get("status") != "ok":
                print(f"error: {result.get('error')}", file=sys.stderr)
                return 1
            print(f"clipboard = {stamp}")
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
