"""Focus a window if it exists, otherwise print a hint.

A common automation building block: "is this app already open?". The script
does not launch the app itself — that is intentionally left to the caller so
this example stays single-purpose.

Usage:
    python examples/focus_or_launch.py "Visual Studio Code"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys


def call(args: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "pc_control", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    # `windows focus` exits non-zero when no match — we still want the JSON.
    if result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    return {"status": "error", "error": result.stderr.strip() or "no output"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("title", help="Partial window title to match")
    args = parser.parse_args()

    listing = call(["windows", "list", "--filter", args.title])
    windows = listing.get("windows", []) if listing.get("status") == "ok" else []

    if not windows:
        print(f"No visible window matches '{args.title}'.", file=sys.stderr)
        print("Launch the app first, then re-run this script.", file=sys.stderr)
        return 1

    focus = call(["windows", "focus", args.title])
    if focus.get("status") != "ok":
        print(f"focus error: {focus.get('error')}", file=sys.stderr)
        return 1

    print(f"Focused: {focus.get('title', args.title)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
