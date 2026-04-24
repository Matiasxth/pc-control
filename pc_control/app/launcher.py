"""App launcher — unified way to open any application."""
import json
import os
import subprocess
import sys

def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


# App registry: name -> {cmd, args_format, description}
_APPS = {
    "chrome":      {"cmd": "start chrome", "with_arg": "start chrome \"{arg}\"", "desc": "Google Chrome"},
    "edge":        {"cmd": "start msedge:", "with_arg": "start msedge:\"{arg}\"", "desc": "Microsoft Edge"},
    "firefox":     {"cmd": "start firefox", "with_arg": "start firefox \"{arg}\"", "desc": "Mozilla Firefox"},
    "spotify":     {"cmd": "start spotify:", "with_arg": "start spotify:search:{arg}", "desc": "Spotify"},
    "notepad":     {"cmd": "start notepad", "with_arg": "start notepad \"{arg}\"", "desc": "Notepad"},
    "calc":        {"cmd": "start calc", "desc": "Calculator"},
    "explorer":    {"cmd": "start explorer", "with_arg": "start explorer \"{arg}\"", "desc": "File Explorer"},
    "cmd":         {"cmd": "start cmd", "desc": "Command Prompt"},
    "powershell":  {"cmd": "start powershell", "desc": "PowerShell"},
    "vscode":      {"cmd": "start code", "with_arg": "start code \"{arg}\"", "desc": "Visual Studio Code"},
    "discord":     {"cmd": "start discord:", "desc": "Discord"},
    "slack":       {"cmd": "start slack:", "desc": "Slack"},
    "teams":       {"cmd": "start msteams:", "desc": "Microsoft Teams"},
    "word":        {"cmd": "start winword", "with_arg": "start winword \"{arg}\"", "desc": "Microsoft Word"},
    "excel":       {"cmd": "start excel", "with_arg": "start excel \"{arg}\"", "desc": "Microsoft Excel"},
    "paint":       {"cmd": "start mspaint", "with_arg": "start mspaint \"{arg}\"", "desc": "Paint"},
    "terminal":    {"cmd": "start wt", "desc": "Windows Terminal"},
    "settings":    {"cmd": "start ms-settings:", "with_arg": "start ms-settings:{arg}", "desc": "Windows Settings"},
    "mail":        {"cmd": "start outlookmail:", "desc": "Mail"},
    "photos":      {"cmd": "start ms-photos:", "desc": "Photos"},
    "snip":        {"cmd": "start ms-screenclip:", "desc": "Snipping Tool"},
    "store":       {"cmd": "start ms-windows-store:", "desc": "Microsoft Store"},
}


def open_app(name: str, target: str = None):
    """Open an application by name, optionally with a target (URL, file, path)."""
    key = name.lower().strip()

    if key not in _APPS:
        # Try as a direct command
        try:
            cmd = f"start {name}" if not target else f"start {name} \"{target}\""
            subprocess.Popen(cmd, shell=True)
            _output({"status": "ok", "action": "open", "app": name, "target": target, "method": "direct"})
            return
        except Exception as e:
            _output({"status": "error", "error": f"Unknown app: {name}. Use 'app list' to see available apps."})
            return

    app = _APPS[key]

    if target and "with_arg" in app:
        cmd = app["with_arg"].replace("{arg}", target)
    else:
        cmd = app["cmd"]

    try:
        subprocess.Popen(cmd, shell=True)
        _output({
            "status": "ok",
            "action": "open",
            "app": key,
            "description": app["desc"],
            "target": target,
        })
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def list_apps():
    """List all known applications."""
    apps = [{"name": k, "description": v["desc"], "supports_arg": "with_arg" in v} for k, v in _APPS.items()]
    _output({"status": "ok", "action": "list_apps", "count": len(apps), "apps": apps})


def handle_command(args):
    cmd = args.app_command
    if cmd == "open":
        open_app(args.name, target=getattr(args, "target", None))
    elif cmd == "list":
        list_apps()
    else:
        print(f"Unknown app command: {cmd}", file=sys.stderr)
        sys.exit(1)
