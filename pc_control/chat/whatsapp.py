"""WhatsApp Web control — open, send, read messages via Playwright."""
import io
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

from pc_control.browser.daemon import _is_alive
from pc_control.browser.daemon import _load_state as load_browser_state
from pc_control.browser.session import browser_connection
from pc_control.config import SCREENSHOTS_DIR

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CHAT_DIR = Path(__file__).parent.parent.parent / ".chat"
CHAT_DIR.mkdir(exist_ok=True)
MONITOR_STATE = CHAT_DIR / "whatsapp_monitor.json"
DAEMON_SCRIPT = Path(__file__).parent / "whatsapp_daemon.py"

# WhatsApp Web selectors (most stable ones)
SEL_SEARCH = 'div[contenteditable="true"][data-tab="3"]'
SEL_MSG_INPUT = 'div[contenteditable="true"][data-tab="10"]'
SEL_MSG_IN = "#main div.message-in"
SEL_MSG_OUT = "#main div.message-out"
SEL_QR = 'canvas[aria-label*="QR"], div[data-ref] canvas'


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def start_whatsapp():
    """Open WhatsApp Web in the persistent browser."""
    browser_state = load_browser_state()
    if not browser_state or not _is_alive(browser_state["pid"]):
        _output({"status": "error", "error": "Browser not running. Run 'browser start --headed' first."})
        return

    with browser_connection() as (browser, ctx, page):
        # Check if WhatsApp tab already exists
        wa_page = None
        for p in ctx.pages:
            if "web.whatsapp.com" in p.url:
                wa_page = p
                break

        if not wa_page:
            wa_page = ctx.new_page()
            wa_page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=30000)

        wa_page.bring_to_front()

        # Wait for either QR code or logged-in state
        try:
            wa_page.wait_for_selector(f'{SEL_SEARCH}, {SEL_QR}', timeout=15000)
        except Exception:
            pass

        # Check if QR is showing (needs scan)
        qr = wa_page.query_selector(SEL_QR)
        if qr:
            # Take screenshot of QR
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            qr_path = SCREENSHOTS_DIR / f"whatsapp_qr_{ts}.png"
            wa_page.screenshot(path=str(qr_path))
            _output({
                "status": "ok",
                "action": "whatsapp_start",
                "logged_in": False,
                "qr_screenshot": str(qr_path.resolve()),
                "message": "Scan the QR code with your phone. Then run 'chat whatsapp status' to verify.",
            })
            return

        # Already logged in
        _output({
            "status": "ok",
            "action": "whatsapp_start",
            "logged_in": True,
            "url": wa_page.url,
        })


def status():
    """Check WhatsApp Web status."""
    # Check browser
    browser_state = load_browser_state()
    browser_running = browser_state and _is_alive(browser_state.get("pid", 0))

    # Check monitor daemon
    monitor_state = _load_monitor_state()
    daemon_running = False
    if monitor_state:
        daemon_running = psutil.pid_exists(monitor_state.get("daemon_pid", 0))

    # Check if logged in
    logged_in = False
    if browser_running:
        try:
            with browser_connection() as (browser, ctx, page):
                for p in ctx.pages:
                    if "web.whatsapp.com" in p.url:
                        logged_in = p.query_selector(SEL_SEARCH) is not None
                        break
        except Exception:
            pass

    _output({
        "status": "ok",
        "action": "whatsapp_status",
        "browser_running": browser_running,
        "logged_in": logged_in,
        "monitor_daemon": daemon_running,
        "monitor_pid": monitor_state.get("daemon_pid") if monitor_state else None,
    })


def send_message(contact: str, message: str):
    """Send a message to a contact."""
    with browser_connection() as (browser, ctx, page):
        wa_page = _find_wa_page(ctx)
        if not wa_page:
            _output({"status": "error", "error": "WhatsApp Web not open. Run 'chat whatsapp start' first."})
            return

        wa_page.bring_to_front()

        # Click search and type contact name
        search = wa_page.wait_for_selector(SEL_SEARCH, timeout=5000)
        search.click()
        search.fill(contact)
        time.sleep(1)

        # Click on the first matching contact
        try:
            wa_page.click(f'span[title*="{contact}"]', timeout=5000)
        except Exception:
            # Try clicking the first result in the search list
            try:
                wa_page.click('#pane-side div[role="listitem"]:first-child', timeout=3000)
            except Exception:
                _output({"status": "error", "error": f"Contact not found: {contact}"})
                return

        time.sleep(0.5)

        # Type and send message
        msg_input = wa_page.wait_for_selector(SEL_MSG_INPUT, timeout=5000)
        msg_input.click()
        wa_page.keyboard.type(message)
        wa_page.keyboard.press("Enter")

        _output({
            "status": "ok",
            "action": "whatsapp_send",
            "contact": contact,
            "message_length": len(message),
        })


def read_messages(contact: str = None, limit: int = 20):
    """Read recent messages from the active chat or a specific contact."""
    with browser_connection() as (browser, ctx, page):
        wa_page = _find_wa_page(ctx)
        if not wa_page:
            _output({"status": "error", "error": "WhatsApp Web not open"})
            return

        # If contact specified, search and open their chat
        if contact:
            search = wa_page.wait_for_selector(SEL_SEARCH, timeout=5000)
            search.click()
            search.fill(contact)
            time.sleep(1)
            try:
                wa_page.click(f'span[title*="{contact}"]', timeout=5000)
            except Exception:
                try:
                    wa_page.click('#pane-side div[role="listitem"]:first-child', timeout=3000)
                except Exception:
                    _output({"status": "error", "error": f"Contact not found: {contact}"})
                    return
            time.sleep(1)

        # Extract messages from DOM
        messages = wa_page.evaluate(f"""(() => {{
            const msgs = document.querySelectorAll('{SEL_MSG_IN}, {SEL_MSG_OUT}');
            const result = [];
            const arr = Array.from(msgs).slice(-{limit});
            arr.forEach(msg => {{
                const textEl = msg.querySelector('.copyable-text span.selectable-text');
                const metaEl = msg.querySelector('.copyable-text');
                const pre = metaEl?.getAttribute('data-pre-plain-text') || '';
                const direction = msg.classList.contains('message-in') ? 'incoming' : 'outgoing';
                const text = textEl?.innerText || '';
                if (text) {{
                    result.push({{
                        direction: direction,
                        text: text,
                        meta: pre,
                    }});
                }}
            }});
            return result;
        }})()""")

        _output({
            "status": "ok",
            "action": "whatsapp_read",
            "contact": contact,
            "count": len(messages),
            "messages": messages,
        })


def monitor_start():
    """Start the background message monitor daemon."""
    browser_state = load_browser_state()
    if not browser_state or not _is_alive(browser_state["pid"]):
        _output({"status": "error", "error": "Browser not running"})
        return

    # Check if already monitoring
    state = _load_monitor_state()
    if state and psutil.pid_exists(state.get("daemon_pid", 0)):
        _output({"status": "ok", "action": "monitor_start", "message": "Already monitoring",
                 "pid": state["daemon_pid"]})
        return

    port = browser_state["port"]
    events_file = CHAT_DIR / f"messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    cmd = [sys.executable, str(DAEMON_SCRIPT), str(port), str(events_file)]
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=CREATE_NEW_PROCESS_GROUP,
    )

    # Wait for ready signal
    try:
        for _ in range(30):
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode(errors="replace")
                _output({"status": "error", "error": f"Daemon exited: {stderr}"})
                return
            line = proc.stdout.readline().decode(errors="replace").strip()
            if line.startswith("MONITOR_READY:"):
                break
            time.sleep(0.5)
        else:
            proc.kill()
            _output({"status": "error", "error": "Daemon did not become ready"})
            return
    except Exception as e:
        proc.kill()
        _output({"status": "error", "error": f"Error starting daemon: {e}"})
        return

    _save_monitor_state({
        "daemon_pid": proc.pid,
        "events_file": str(events_file),
        "started_at": datetime.now().isoformat(),
    })

    _output({
        "status": "ok",
        "action": "monitor_start",
        "daemon_pid": proc.pid,
        "events_file": str(events_file),
    })


def monitor_stop():
    """Stop the monitor daemon."""
    state = _load_monitor_state()
    if not state:
        _output({"status": "ok", "action": "monitor_stop", "message": "Not monitoring"})
        return

    pid = state.get("daemon_pid")
    if pid and psutil.pid_exists(pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    _clear_monitor_state()
    _output({"status": "ok", "action": "monitor_stop", "killed_pid": pid})


def monitor_messages(since: str = None):
    """Read messages captured by the monitor daemon."""
    state = _load_monitor_state()
    if not state:
        _output({"status": "error", "error": "No monitor active. Run 'chat whatsapp monitor start'"})
        return

    events_file = Path(state["events_file"])
    if not events_file.exists():
        _output({"status": "ok", "action": "monitor_messages", "count": 0, "messages": []})
        return

    messages = json.loads(events_file.read_text(encoding="utf-8"))

    if since:
        messages = [m for m in messages if m.get("timestamp", "") >= since]

    _output({
        "status": "ok",
        "action": "monitor_messages",
        "count": len(messages),
        "messages": messages,
    })


def _find_wa_page(ctx):
    for p in ctx.pages:
        if "web.whatsapp.com" in p.url:
            return p
    return None


def _save_monitor_state(state):
    MONITOR_STATE.write_text(json.dumps(state, indent=2))


def _load_monitor_state():
    if MONITOR_STATE.exists():
        return json.loads(MONITOR_STATE.read_text())
    return None


def _clear_monitor_state():
    if MONITOR_STATE.exists():
        MONITOR_STATE.unlink()
