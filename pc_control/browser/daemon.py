"""Browser daemon — launch/kill persistent Chromium via CDP."""
import json
import os
import subprocess
import time
from pathlib import Path

import psutil

from pc_control.config import (
    BROWSER_STATE_DIR,
    BROWSER_STATE_FILE,
    BROWSER_USER_DATA,
    DEFAULT_CDP_PORT,
)

# Chromium from Playwright installation
CHROMIUM_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-1208" / "chrome-win64" / "chrome.exe"


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _load_state() -> dict | None:
    if BROWSER_STATE_FILE.exists():
        return json.loads(BROWSER_STATE_FILE.read_text())
    return None


def _save_state(state: dict):
    BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_STATE_FILE.write_text(json.dumps(state, indent=2))


def _clear_state():
    if BROWSER_STATE_FILE.exists():
        BROWSER_STATE_FILE.unlink()


def _is_alive(pid: int) -> bool:
    return psutil.pid_exists(pid)


def _is_cdp_responsive(port: int) -> bool:
    import urllib.request
    try:
        resp = urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=3)
        return resp.status == 200
    except Exception:
        return False


def start(headed=False, port=None):
    """Launch persistent Chromium with CDP debugging."""
    port = port or DEFAULT_CDP_PORT

    # Check if already running
    state = _load_state()
    if state and _is_alive(state["pid"]) and _is_cdp_responsive(state["port"]):
        _output({"status": "ok", "action": "browser_start", "message": "Already running",
                 "pid": state["pid"], "port": state["port"]})
        return

    # Clean stale state
    _clear_state()

    if not CHROMIUM_EXE.exists():
        _output({"status": "error", "error": f"Chromium not found at {CHROMIUM_EXE}"})
        return

    BROWSER_USER_DATA.mkdir(parents=True, exist_ok=True)

    args = [
        str(CHROMIUM_EXE),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={BROWSER_USER_DATA}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
    ]

    if not headed:
        args.append("--headless=new")

    # Launch as detached process
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    DETACHED_PROCESS = 0x00000008
    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
    )

    # Wait for CDP to become responsive
    for _ in range(30):
        time.sleep(0.5)
        if _is_cdp_responsive(port):
            break
    else:
        _output({"status": "error", "error": "Browser started but CDP not responding after 15s"})
        return

    state = {
        "pid": proc.pid,
        "port": port,
        "headless": not headed,
        "user_data_dir": str(BROWSER_USER_DATA),
    }
    _save_state(state)

    _output({"status": "ok", "action": "browser_start", "pid": proc.pid, "port": port, "headed": headed})


def status():
    """Check browser daemon status."""
    state = _load_state()
    if not state:
        _output({"status": "ok", "action": "browser_status", "running": False})
        return

    alive = _is_alive(state["pid"])
    cdp_ok = _is_cdp_responsive(state["port"]) if alive else False

    if not alive:
        _clear_state()

    _output({
        "status": "ok",
        "action": "browser_status",
        "running": alive and cdp_ok,
        "pid": state.get("pid"),
        "port": state.get("port"),
        "headless": state.get("headless"),
        "process_alive": alive,
        "cdp_responsive": cdp_ok,
    })


def stop():
    """Stop the persistent browser."""
    state = _load_state()
    if not state:
        _output({"status": "ok", "action": "browser_stop", "message": "Not running"})
        return

    pid = state["pid"]
    try:
        if _is_alive(pid):
            parent = psutil.Process(pid)
            # Kill child processes too
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.kill()
    except psutil.NoSuchProcess:
        pass

    _clear_state()
    _output({"status": "ok", "action": "browser_stop", "killed_pid": pid})
