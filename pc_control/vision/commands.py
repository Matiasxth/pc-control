"""Vision module command dispatcher."""

from __future__ import annotations

import sys
from argparse import Namespace


def handle_command(args: Namespace) -> None:
    """Dispatch `vision <subcommand>` to diff / detect / template."""
    cmd = args.vision_command

    if cmd == "diff":
        from pc_control.vision.diff import diff_screenshots

        diff_screenshots(args.path1, args.path2, threshold=getattr(args, "threshold", 30))

    elif cmd == "diff-screen":
        from pc_control.vision.diff import diff_screen

        diff_screen(reference=getattr(args, "reference", None))

    elif cmd == "find-text":
        from pc_control.vision.detect import find_text

        find_text(
            args.query,
            region=getattr(args, "region", None),
            window=getattr(args, "window", None),
        )

    elif cmd == "find-image":
        from pc_control.vision.template import find_image

        find_image(
            args.template,
            threshold=getattr(args, "threshold", 0.8),
        )

    elif cmd == "elements":
        from pc_control.vision.detect import detect_elements

        detect_elements(
            region=getattr(args, "region", None),
            window=getattr(args, "window", None),
        )

    else:
        print(f"Unknown vision command: {cmd}", file=sys.stderr)
        sys.exit(1)
