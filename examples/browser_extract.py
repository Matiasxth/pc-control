"""Start the persistent browser, navigate to a URL, and extract <h1> text.

The browser is left running after the script exits so subsequent calls reuse
the same Chromium — that is the intended pattern for real automations. Call
`python -m pc_control browser stop` when you are done for the session.

Usage:
    python examples/browser_extract.py https://example.com

Requires the `[browser]` extra and `python -m playwright install chromium`.
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
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "error": result.stderr.strip() or "non-JSON output",
        }


def ensure_browser_running() -> None:
    """Start the persistent browser if it isn't already."""
    status = call(["browser", "status"])
    if status.get("running"):
        return
    started = call(["browser", "start"])
    if started.get("status") != "ok":
        raise RuntimeError(f"failed to start browser: {started.get('error')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("url", help="URL to navigate to")
    parser.add_argument(
        "--selector", default="h1", help="CSS selector to extract (default: h1)"
    )
    args = parser.parse_args()

    try:
        ensure_browser_running()
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    nav = call(["browser", "goto", args.url])
    if nav.get("status") != "ok":
        print(f"navigation error: {nav.get('error')}", file=sys.stderr)
        return 1

    text = call(["browser", "text", args.selector])
    if text.get("status") != "ok":
        print(f"text extract error: {text.get('error')}", file=sys.stderr)
        return 1

    print(text.get("text", "").strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
