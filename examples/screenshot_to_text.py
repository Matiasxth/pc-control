"""Screenshot a screen region and OCR it to stdout.

Combines two pc-control commands in sequence: `screen shot` and `ocr file`.

Usage:
    python examples/screenshot_to_text.py 0,0,800,600
    python examples/screenshot_to_text.py --window "Notepad"

Requires the `[ocr]` extra: `pip install -e ".[ocr]"`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def call(args: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "pc_control", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pc-control failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("region", nargs="?", help='Region "x1,y1,x2,y2"')
    src.add_argument("--window", help="Capture a window by partial title")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        shot_path = str(Path(tmp) / "capture.png")

        shot_args = ["screen", "shot", "--output", shot_path]
        if args.region:
            shot_args += ["--region", args.region]
        else:
            shot_args += ["--window", args.window]

        shot = call(shot_args)
        if shot.get("status") != "ok":
            print(f"screenshot error: {shot.get('error')}", file=sys.stderr)
            return 1

        ocr = call(["ocr", "file", shot_path])
        if ocr.get("status") != "ok":
            print(f"ocr error: {ocr.get('error')}", file=sys.stderr)
            return 1

        print(ocr.get("text", "").strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
