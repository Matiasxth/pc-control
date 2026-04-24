"""Desktop automation command dispatcher — uses daemon when available."""
import json
import subprocess
import sys


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _try_daemon(cmd: dict) -> dict | None:
    """Try sending command to daemon. Returns result or None if daemon not running."""
    try:
        from pc_control.desktop.daemon import is_daemon_running, send_command
        if is_daemon_running():
            return send_command(cmd)
    except Exception:
        pass
    return None


def handle_command(args):
    cmd = args.desktop_command

    if cmd == "daemon":
        _handle_daemon(args)
        return

    if cmd == "inspect":
        from pc_control.desktop.inspector import inspect_app
        inspect_app(args.app)

    elif cmd == "tree":
        from pc_control.desktop.inspector import get_tree
        get_tree(args.app, depth=getattr(args, "depth", 3))

    elif cmd == "scan":
        # Try daemon first (fast path)
        result = _try_daemon({
            "action": "scan",
            "app": args.app,
            "filter_type": getattr(args, "type", None),
            "filter_name": getattr(args, "name", None),
            "refresh": getattr(args, "refresh", False),
        })
        if result:
            _output(result)
            return

        # Fallback: direct
        from pc_control.desktop.inspector import scan_app
        scan_app(
            args.app,
            filter_type=getattr(args, "type", None),
            filter_name=getattr(args, "name", None),
        )

    elif cmd == "read":
        from pc_control.desktop.inspector import read_control
        read_control(args.app, args.control_path)

    elif cmd == "click":
        name = getattr(args, "name", None)
        control_type = getattr(args, "control_type", None)
        control_path = getattr(args, "control_path", None)

        # Try daemon first
        result = _try_daemon({
            "action": "click",
            "app": args.app,
            "name": name,
            "control_type": control_type,
            "control_path": control_path,
        })
        if result:
            _output(result)
            return

        # Fallback: direct
        from pc_control.desktop.controller import click_control
        click_control(args.app, control_path, name=name, control_type=control_type)

    elif cmd == "type":
        name = getattr(args, "name", None)
        control_path = getattr(args, "control_path", None)

        # Try daemon first
        result = _try_daemon({
            "action": "type",
            "app": args.app,
            "text": args.text,
            "name": name,
            "control_path": control_path,
        })
        if result:
            _output(result)
            return

        # Fallback: direct
        from pc_control.desktop.controller import type_in_control
        type_in_control(args.app, control_path, args.text, name=name)

    elif cmd == "play":
        result = _try_daemon({"action": "play", "app": args.app, "query": args.query})
        if result:
            _output(result)
            return
        # Fallback without daemon
        import os
        os.startfile(f"spotify:search:{args.query}")
        _output({"status": "ok", "action": "play_search_opened", "query": args.query})

    elif cmd == "select":
        from pc_control.desktop.controller import select_item
        select_item(args.app, args.control_path, args.item)

    else:
        print(f"Unknown desktop command: {cmd}", file=sys.stderr)
        sys.exit(1)


def _handle_daemon(args):
    """Handle daemon start/stop/status."""
    daemon_cmd = args.daemon_command

    if daemon_cmd == "start":
        from pc_control.desktop.daemon import is_daemon_running
        if is_daemon_running():
            _output({"status": "ok", "daemon": "already_running"})
            return

        # Launch daemon as a background subprocess
        python = sys.executable
        from pc_control.config import PROJECT_ROOT
        proc = subprocess.Popen(
            [python, "-c", "from pc_control.desktop.daemon import start_daemon; start_daemon()"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        # Read first line (startup confirmation)
        import time
        time.sleep(1.0)
        if proc.poll() is None:
            _output({"status": "ok", "action": "daemon_started", "pid": proc.pid})
        else:
            _output({"status": "error", "error": "Daemon failed to start"})

    elif daemon_cmd == "stop":
        from pc_control.desktop.daemon import stop_daemon
        result = stop_daemon()
        _output(result)

    elif daemon_cmd == "status":
        from pc_control.desktop.daemon import daemon_status
        result = daemon_status()
        _output(result)
