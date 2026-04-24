"""Workflow engine — predefined action sequences triggered by a single command."""
import json
import os
import subprocess
import sys
import time


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _run(cmd: str, silent=True):
    """Run a pc_control command and return parsed result."""
    r = subprocess.run(
        [sys.executable, "-m", "pc_control"] + cmd.split(),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"status": "error", "output": r.stdout, "error": r.stderr}


def _steps(name, actions):
    """Execute a list of actions and report results."""
    results = []
    for desc, cmd in actions:
        if cmd.startswith("sleep:"):
            time.sleep(float(cmd.split(":")[1]))
            results.append({"step": desc, "status": "ok"})
        elif cmd.startswith("startfile:"):
            os.startfile(cmd.split(":", 1)[1])
            results.append({"step": desc, "status": "ok"})
        else:
            r = _run(cmd)
            results.append({"step": desc, "status": r.get("status", "?")})

    ok = sum(1 for r in results if r["status"] == "ok")
    _output({
        "status": "ok",
        "action": "workflow",
        "name": name,
        "steps_total": len(results),
        "steps_ok": ok,
        "results": results,
    })


# ── Predefined Workflows ──────────────────────────────

def workflow_work():
    """Set up a coding work environment."""
    _steps("work", [
        ("Set volume to 30%", "audio volume 30"),
        ("Open VS Code", "app open vscode"),
        ("Open Chrome", "app open chrome"),
        ("Play lo-fi music", "desktop play spotify lofi beats study"),
        ("Wait for apps", "sleep:3"),
        ("Snap terminal left", "windows snap conversation left"),
        ("Snap Chrome right", "windows snap Chrome right"),
    ])


def workflow_relax():
    """Chill mode — music + close work apps."""
    _steps("relax", [
        ("Set volume to 50%", "audio volume 50"),
        ("Play chill music", "desktop play spotify chill vibes playlist"),
        ("Maximize Spotify", "windows snap Spotify maximize"),
    ])


def workflow_present():
    """Presentation mode — clean desktop, mute, maximize main app."""
    _steps("present", [
        ("Mute audio", "audio mute"),
        ("Save current layout", "windows layout save pre-present"),
        ("Maximize Chrome", "windows snap Chrome maximize"),
    ])


def workflow_reset():
    """Reset — restore saved layout, unmute."""
    _steps("reset", [
        ("Unmute audio", "audio unmute"),
        ("Load saved layout", "windows layout load pre-present"),
    ])


_WORKFLOWS = {
    "work": workflow_work,
    "relax": workflow_relax,
    "present": workflow_present,
    "reset": workflow_reset,
}


def run_workflow(name: str):
    if name in _WORKFLOWS:
        _WORKFLOWS[name]()
    else:
        _output({
            "status": "error",
            "error": f"Unknown workflow: {name}",
            "available": list(_WORKFLOWS.keys()),
        })


def list_workflows():
    workflows = [{"name": k, "description": v.__doc__.strip()} for k, v in _WORKFLOWS.items()]
    _output({"status": "ok", "action": "list_workflows", "workflows": workflows})


def handle_command(args):
    cmd = args.workflow_command
    if cmd == "run":
        run_workflow(args.name)
    elif cmd == "list":
        list_workflows()
    else:
        print(f"Unknown workflow command: {cmd}", file=sys.stderr)
        sys.exit(1)
