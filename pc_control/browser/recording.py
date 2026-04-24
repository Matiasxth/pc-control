"""Browser recording — record user actions via background daemon."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

from pc_control.config import RECORDINGS_DIR, DEFAULT_CDP_PORT


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


RECORDING_STATE = RECORDINGS_DIR / ".recording_state.json"
DAEMON_SCRIPT = Path(__file__).parent / "recorder_daemon.py"


def _save_state(state: dict):
    RECORDING_STATE.write_text(json.dumps(state, indent=2))


def _load_state() -> dict | None:
    if RECORDING_STATE.exists():
        return json.loads(RECORDING_STATE.read_text())
    return None


def _clear_state():
    if RECORDING_STATE.exists():
        RECORDING_STATE.unlink()


def start_recording(url=None, session_name=None):
    """Start recording by launching background daemon."""
    # Check if already recording
    state = _load_state()
    if state and psutil.pid_exists(state.get("daemon_pid", 0)):
        _output({"status": "error", "error": "Already recording. Run 'browser record stop' first."})
        return

    from pc_control.browser.daemon import _load_state as load_browser_state, _is_alive
    browser_state = load_browser_state()
    if not browser_state or not _is_alive(browser_state["pid"]):
        _output({"status": "error", "error": "Browser not running. Run 'browser start --headed' first."})
        return

    port = browser_state["port"]
    session_name = session_name or datetime.now().strftime("recording_%Y%m%d_%H%M%S")
    events_file = RECORDINGS_DIR / f"{session_name}.events.json"

    # Launch daemon as background process
    cmd = [sys.executable, str(DAEMON_SCRIPT), str(port), str(events_file)]
    if url:
        cmd.append(url)

    CREATE_NEW_PROCESS_GROUP = 0x00000200
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NEW_PROCESS_GROUP,
    )

    # Wait for RECORDER_READY signal
    try:
        for _ in range(30):  # 15 seconds max
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode(errors="replace")
                _output({"status": "error", "error": f"Daemon exited: {stderr}"})
                return
            # Check if ready line is available
            import select
            line = proc.stdout.readline().decode(errors="replace").strip()
            if line.startswith("RECORDER_READY:"):
                break
            time.sleep(0.5)
        else:
            proc.kill()
            _output({"status": "error", "error": "Daemon did not become ready in time"})
            return
    except Exception as e:
        proc.kill()
        _output({"status": "error", "error": f"Error starting daemon: {e}"})
        return

    _save_state({
        "session_name": session_name,
        "daemon_pid": proc.pid,
        "events_file": str(events_file),
        "started_at": datetime.now().isoformat(),
        "url": url,
    })

    _output({
        "status": "ok",
        "action": "record_start",
        "session": session_name,
        "daemon_pid": proc.pid,
        "message": "Recording. Interact with the browser, then run 'browser record stop'.",
    })


def stop_recording(output_path=None):
    """Stop daemon and generate script from recorded events."""
    state = _load_state()
    if not state:
        _output({"status": "error", "error": "No recording session active"})
        return

    daemon_pid = state.get("daemon_pid")
    session_name = state["session_name"]
    events_file = Path(state["events_file"])

    # Signal daemon to stop gracefully
    if daemon_pid and psutil.pid_exists(daemon_pid):
        try:
            p = psutil.Process(daemon_pid)
            p.terminate()
            p.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            try:
                p.kill()
            except Exception:
                pass

    # Read events
    actions = []
    if events_file.exists():
        try:
            actions = json.loads(events_file.read_text(encoding="utf-8"))
        except Exception:
            actions = []

    output_file = Path(output_path) if output_path else RECORDINGS_DIR / f"{session_name}.py"

    if not actions:
        _clear_state()
        _output({"status": "error", "error": "No actions recorded. Did you interact with the browser?"})
        return

    # Generate Python script
    script = _generate_script(actions, state)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(script, encoding="utf-8")

    # Save raw JSON too
    raw_file = output_file.with_suffix(".json")
    raw_file.write_text(json.dumps(actions, indent=2, ensure_ascii=False), encoding="utf-8")

    # Cleanup
    if events_file.exists():
        events_file.unlink()
    _clear_state()

    _output({
        "status": "ok",
        "action": "record_stop",
        "session": session_name,
        "actions_count": len(actions),
        "script": str(output_file.resolve()),
        "raw_data": str(raw_file.resolve()),
    })


def _generate_script(actions: list, state: dict) -> str:
    """Transform recorded actions into a Playwright Python script."""
    lines = [
        f'"""Recorded browser actions — {state.get("started_at", "")}',
        f'Start URL: {state.get("url", "N/A")}',
        f'Actions: {len(actions)}',
        '"""',
        'from playwright.sync_api import sync_playwright',
        '',
        '',
        'def run(page=None):',
        '    """Run recorded actions. Pass a page object or run standalone."""',
        '    standalone = page is None',
        '    pw = None',
        '    if standalone:',
        '        pw = sync_playwright().start()',
        '        browser = pw.chromium.launch(headless=False)',
        '        page = browser.new_page()',
        '',
    ]

    start_url = state.get("url")
    if start_url:
        lines.append(f'    page.goto("{start_url}", wait_until="domcontentloaded")')
        lines.append('')

    prev_timestamp = 0
    for action in actions:
        ts = action.get("timestamp", 0)
        gap = ts - prev_timestamp
        if gap > 1000:
            lines.append(f'    page.wait_for_timeout({min(gap, 5000)})')
        prev_timestamp = ts

        atype = action.get("type")
        selector = action.get("selector", "")
        sel_escaped = selector.replace('"', '\\"')

        if atype == "click":
            lines.append(f'    page.click("{sel_escaped}")')
        elif atype == "fill":
            value = action.get("value", "")
            val_escaped = value.replace('"', '\\"')
            if action.get("inputType") == "password":
                lines.append(f'    page.fill("{sel_escaped}", "***")  # PASSWORD — replace with actual value')
            else:
                lines.append(f'    page.fill("{sel_escaped}", "{val_escaped}")')
        elif atype == "select":
            lines.append(f'    page.select_option("{sel_escaped}", "{action.get("value", "")}")')
        elif atype == "check":
            lines.append(f'    page.check("{sel_escaped}")')
        elif atype == "uncheck":
            lines.append(f'    page.uncheck("{sel_escaped}")')
        elif atype == "key":
            lines.append(f'    page.keyboard.press("{action.get("key", "")}")')
        elif atype == "navigation":
            to_url = action.get("to", "")
            lines.append(f'    # Navigation: {to_url}')
            path = _url_pattern(to_url)
            lines.append(f'    page.wait_for_url("**{path}**", timeout=10000)')

    lines.extend([
        '',
        '    if standalone:',
        '        input("Press Enter to close browser...")',
        '        browser.close()',
        '        pw.stop()',
        '',
        '',
        'if __name__ == "__main__":',
        '    run()',
        '',
    ])

    return '\n'.join(lines)


def _url_pattern(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.path or "/"


def list_recordings():
    recordings = []
    for f in sorted(RECORDINGS_DIR.glob("*.py")):
        recordings.append({
            "name": f.stem,
            "path": str(f.resolve()),
            "size_kb": round(f.stat().st_size / 1024, 1),
        })
    _output({"status": "ok", "action": "record_list", "count": len(recordings), "recordings": recordings})


def play_recording(script_path, slow=0):
    from pc_control.browser.session import browser_connection

    script_file = Path(script_path)
    if not script_file.exists():
        script_file = RECORDINGS_DIR / script_path
        if not script_file.exists():
            _output({"status": "error", "error": f"Script not found: {script_path}"})
            return

    with browser_connection() as (browser, ctx, page):
        if slow > 0:
            page.set_default_timeout(slow * 2)

        import importlib.util
        spec = importlib.util.spec_from_file_location("recording", str(script_file))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.run(page=page)

        _output({"status": "ok", "action": "record_play", "script": str(script_file.resolve())})


def handle_record_command(args):
    cmd = args.record_command
    if cmd == "start":
        start_recording(
            url=getattr(args, "url", None),
            session_name=getattr(args, "session", None),
        )
    elif cmd == "stop":
        stop_recording(output_path=getattr(args, "output", None))
    elif cmd == "list":
        list_recordings()
    elif cmd == "play":
        play_recording(args.script, slow=getattr(args, "slow", 0))
    else:
        print(f"Unknown record command: {cmd}", file=sys.stderr)
        sys.exit(1)
