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


def _playwright_browsers_dir() -> Path:
    """Return the directory where Playwright stores its browsers.

    Honors ``PLAYWRIGHT_BROWSERS_PATH`` the same way Playwright does,
    falling back to the default ``%LOCALAPPDATA%\\ms-playwright``.
    """
    custom = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if custom and custom != "0":
        return Path(custom)
    return Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"


def find_chromium_exe(browsers_dir: Path | None = None) -> Path | None:
    """Locate the newest Playwright-installed Chromium executable.

    Playwright installs Chromium into ``chromium-<revision>`` folders whose
    revision changes with every Playwright release, so the path can't be
    hard-coded. Picks the highest installed revision that has a
    ``chrome.exe``; returns ``None`` if none is installed.
    """
    base = browsers_dir if browsers_dir is not None else _playwright_browsers_dir()
    candidates = []
    for exe in base.glob("chromium-*/chrome-win64/chrome.exe"):
        revision = exe.parent.parent.name.removeprefix("chromium-")
        if revision.isdigit():
            candidates.append((int(revision), exe))
    if not candidates:
        return None
    return max(candidates)[1]


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
        _output(
            {
                "status": "ok",
                "action": "browser_start",
                "message": "Already running",
                "pid": state["pid"],
                "port": state["port"],
            }
        )
        return

    # Clean stale state
    _clear_state()

    chromium_exe = find_chromium_exe()
    if chromium_exe is None:
        _output(
            {
                "status": "error",
                "error": (
                    f"Playwright Chromium not found in {_playwright_browsers_dir()}. "
                    "Run: python -m playwright install chromium"
                ),
            }
        )
        return

    BROWSER_USER_DATA.mkdir(parents=True, exist_ok=True)

    args = [
        str(chromium_exe),
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

    _output(
        {"status": "ok", "action": "browser_start", "pid": proc.pid, "port": port, "headed": headed}
    )


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

    _output(
        {
            "status": "ok",
            "action": "browser_status",
            "running": alive and cdp_ok,
            "pid": state.get("pid"),
            "port": state.get("port"),
            "headless": state.get("headless"),
            "process_alive": alive,
            "cdp_responsive": cdp_ok,
        }
    )


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
