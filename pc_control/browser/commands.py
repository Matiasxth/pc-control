"""Browser command dispatcher — routes CLI args to browser modules."""

from __future__ import annotations

import sys
from argparse import Namespace

from pc_control.browser import daemon, navigate


def handle_command(args: Namespace) -> None:
    """Dispatch `browser <subcommand>` to daemon / navigate / recording."""
    cmd = args.browser_command

    # Daemon commands
    if cmd == "start":
        daemon.start(
            headed=getattr(args, "headed", False),
            port=getattr(args, "port", None),
        )
    elif cmd == "status":
        daemon.status()
    elif cmd == "stop":
        daemon.stop()

    # Navigation commands
    elif cmd == "goto":
        navigate.goto(args.url, new_tab=getattr(args, "new_tab", False))
    elif cmd == "tabs":
        navigate.tabs()
    elif cmd == "tab":
        close_idx = getattr(args, "close", None)
        if close_idx is not None:
            navigate.close_tab(close_idx)
        elif args.index is not None:
            navigate.switch_tab(args.index)
        else:
            print("Provide tab index or --close", file=sys.stderr)
            sys.exit(1)
    elif cmd == "click":
        navigate.click(args.selector)
    elif cmd == "fill":
        navigate.fill(args.selector, args.value)
    elif cmd == "select":
        navigate.select_option(args.selector, args.value)
    elif cmd == "check":
        navigate.check(args.selector)
    elif cmd == "text":
        navigate.text(args.selector)
    elif cmd == "html":
        navigate.html(args.selector)
    elif cmd == "attr":
        navigate.attr(args.selector, args.attribute)
    elif cmd == "eval":
        navigate.evaluate(args.js)
    elif cmd == "screenshot":
        navigate.screenshot(
            selector=getattr(args, "selector", None),
            output=getattr(args, "output", None),
        )
    elif cmd == "wait":
        navigate.wait_for(args.selector, timeout=getattr(args, "timeout", 10))
    elif cmd == "save-storage":
        navigate.save_storage(args.path)
    elif cmd == "load-storage":
        navigate.load_storage(args.path)

    # Recording commands
    elif cmd == "record":
        from pc_control.browser.recording import handle_record_command

        handle_record_command(args)

    else:
        print(f"Unknown browser command: {cmd}", file=sys.stderr)
        sys.exit(1)
