"""HTTP webhook receiver — daemon that logs incoming POST requests."""
import io
import json
import subprocess
import sys
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import psutil

from pc_control.config import PROJECT_ROOT

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API_CONFIG = PROJECT_ROOT / ".api"
API_CONFIG.mkdir(exist_ok=True)
WEBHOOK_STATE = API_CONFIG / "webhook_state.json"
WEBHOOK_LOG = API_CONFIG / "webhook_log.json"


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode(errors="replace") if length else ""

        event = {
            "timestamp": datetime.now().isoformat(),
            "method": "POST",
            "path": self.path,
            "headers": dict(self.headers),
            "body": body,
        }

        # Append to log
        log = []
        if WEBHOOK_LOG.exists():
            try:
                log = json.loads(WEBHOOK_LOG.read_text(encoding="utf-8"))
            except Exception:
                log = []
        log.append(event)
        # Keep last 500 events
        log = log[-500:]
        WEBHOOK_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "webhook active"}).encode())

    def log_message(self, format, *args):
        pass  # Suppress default logging


def _run_server(port):
    """Run webhook server (called as subprocess)."""
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    print(f"WEBHOOK_READY:{port}", flush=True)
    server.serve_forever()


def start_webhook(port=8765):
    """Start webhook server as background daemon."""
    state = _load_state()
    if state and psutil.pid_exists(state.get("pid", 0)):
        _output({"status": "ok", "action": "webhook_start", "message": "Already running",
                 "port": state["port"], "pid": state["pid"]})
        return

    CREATE_NEW_PROCESS_GROUP = 0x00000200
    DETACHED_PROCESS = 0x00000008
    proc = subprocess.Popen(
        [sys.executable, "-c",
         f"from pc_control.api.webhooks import _run_server; _run_server({port})"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
    )

    # Wait for ready
    try:
        for _ in range(20):
            if proc.poll() is not None:
                _output({"status": "error", "error": "Webhook server exited"})
                return
            line = proc.stdout.readline().decode(errors="replace").strip()
            if line.startswith("WEBHOOK_READY:"):
                break
            time.sleep(0.5)
        else:
            proc.kill()
            _output({"status": "error", "error": "Server did not start"})
            return
    except Exception as e:
        proc.kill()
        _output({"status": "error", "error": str(e)})
        return

    _save_state({"pid": proc.pid, "port": port, "started_at": datetime.now().isoformat()})
    _output({"status": "ok", "action": "webhook_start", "port": port, "pid": proc.pid})


def stop_webhook():
    """Stop the webhook server."""
    state = _load_state()
    if not state:
        _output({"status": "ok", "action": "webhook_stop", "message": "Not running"})
        return

    pid = state.get("pid")
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

    _clear_state()
    _output({"status": "ok", "action": "webhook_stop", "killed_pid": pid})


def list_events(limit=50):
    """Read webhook events."""
    if not WEBHOOK_LOG.exists():
        _output({"status": "ok", "action": "webhook_events", "count": 0, "events": []})
        return

    events = json.loads(WEBHOOK_LOG.read_text(encoding="utf-8"))
    events = events[-limit:]
    _output({"status": "ok", "action": "webhook_events", "count": len(events), "events": events})


def _save_state(state):
    WEBHOOK_STATE.write_text(json.dumps(state, indent=2))

def _load_state():
    if WEBHOOK_STATE.exists():
        return json.loads(WEBHOOK_STATE.read_text())
    return None

def _clear_state():
    if WEBHOOK_STATE.exists():
        WEBHOOK_STATE.unlink()
