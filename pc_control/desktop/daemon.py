"""Desktop daemon — persistent pywinauto connections with cached control trees.

Runs as a background process, accepts commands via local TCP socket.
Eliminates cold-start overhead: connect once, interact instantly.
"""
import io
import json
import os
import signal
import socket
import sys
import threading
import time

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path

# Daemon config
DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 19222
DAEMON_PID_FILE = Path(__file__).parent.parent.parent / ".desktop" / "daemon.pid"
DAEMON_PID_FILE.parent.mkdir(parents=True, exist_ok=True)

# Cache TTL
CACHE_TTL = 5.0  # seconds before control tree is considered stale


class AppConnection:
    """Cached connection to an application."""

    def __init__(self, app, backend, pid, window_title):
        self.app = app
        self.backend = backend
        self.pid = pid
        self.window_title = window_title
        self._controls_cache = None
        self._cache_time = 0

    def get_window(self):
        return self.app.top_window()

    def get_descendants(self, force_refresh=False):
        """Get cached descendants or refresh if stale."""
        now = time.time()
        if not force_refresh and self._controls_cache and (now - self._cache_time) < CACHE_TTL:
            return self._controls_cache
        win = self.get_window()
        self._controls_cache = win.descendants()
        self._cache_time = now
        # Update window title (it may change, e.g. Spotify)
        try:
            self.window_title = win.window_text()
        except Exception:
            pass
        return self._controls_cache

    def ensure_foreground(self):
        """Restore and focus the window."""
        try:
            win = self.get_window()
            if win.is_minimized():
                win.restore()
                time.sleep(0.3)
            win.set_focus()
            time.sleep(0.15)
        except Exception:
            pass

    def is_alive(self):
        """Check if the app process is still running."""
        try:
            import psutil
            return psutil.pid_exists(self.pid)
        except Exception:
            return True  # assume alive if can't check


class DesktopDaemon:
    """Persistent daemon managing app connections and control caches."""

    def __init__(self):
        self._connections: dict[str, AppConnection] = {}  # key -> AppConnection
        self._lock = threading.Lock()
        self._running = False

    def _get_or_connect(self, app_query: str) -> AppConnection:
        """Get existing connection or create new one."""
        key = app_query.lower().strip()

        with self._lock:
            # Check existing connection
            if key in self._connections:
                conn = self._connections[key]
                if conn.is_alive():
                    return conn
                else:
                    del self._connections[key]

            # Create new connection using inspector's _connect
            from pc_control.desktop.inspector import _connect
            app, backend = _connect(app_query)
            if not app:
                raise ConnectionError(f"Cannot connect to '{app_query}'")

            win = app.top_window()
            pid = 0
            try:
                pid = win.process_id()
            except Exception:
                pass

            conn = AppConnection(app, backend, pid, win.window_text())
            self._connections[key] = conn
            return conn

    def handle_command(self, cmd: dict) -> dict:
        """Process a command and return result."""
        action = cmd.get("action", "")
        app_query = cmd.get("app", "")

        try:
            if action == "ping":
                return {"status": "ok", "action": "pong", "connections": list(self._connections.keys())}

            if action == "play":
                return self._handle_play(app_query, cmd)

            if action == "disconnect":
                key = app_query.lower().strip()
                with self._lock:
                    self._connections.pop(key, None)
                return {"status": "ok", "action": "disconnected", "app": app_query}

            if action == "scan":
                return self._handle_scan(app_query, cmd)
            elif action == "click":
                return self._handle_click(app_query, cmd)
            elif action == "type":
                return self._handle_type(app_query, cmd)
            elif action == "focus":
                return self._handle_focus(app_query)
            elif action == "info":
                return self._handle_info(app_query)
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}

        except ConnectionError as e:
            return {"status": "error", "error": str(e)}
        except Exception as e:
            # Connection might be stale, remove it
            key = app_query.lower().strip()
            with self._lock:
                self._connections.pop(key, None)
            return {"status": "error", "error": str(e)}

    def _handle_play(self, app_query: str, cmd: dict) -> dict:
        """Compound play: search via URI + click first result. For Spotify."""
        query = cmd.get("query", "")
        if not query:
            return {"status": "error", "error": "Missing 'query' field"}

        import os

        # 1. Ensure Spotify is visible (Electron doesn't render when minimized)
        try:
            conn = self._get_or_connect(app_query)
            conn.ensure_foreground()
        except Exception:
            pass

        # 2. Open search via URI (instant, works for Spotify)
        uri = f"spotify:search:{query}"
        try:
            os.startfile(uri)
        except Exception as e:
            return {"status": "error", "error": f"Failed to open URI: {e}"}

        # 3. Wait for results to render
        time.sleep(3.0)

        # 3. Connect and find play button
        conn = self._get_or_connect(app_query)
        descs = conn.get_descendants(force_refresh=True)

        # Find best matching "Reproducir ..." button
        query_words = [w.lower() for w in query.lower().split() if len(w) > 1]
        play_ctrl = None
        best_score = 0

        for d in descs:
            try:
                d_name = d.window_text() if hasattr(d, 'window_text') else ""
                d_type = d.friendly_class_name() if hasattr(d, 'friendly_class_name') else ""
                if "Button" not in d_type or "Reproducir" not in d_name:
                    continue
                name_lower = d_name.lower()
                # Score: count how many query words match
                word_matches = sum(1 for w in query_words if w in name_lower)
                if word_matches == 0:
                    continue
                # Prefer more word matches; break ties by shorter name (original > remix/cover)
                score = (word_matches * 1000) - len(d_name)
                if score > best_score:
                    best_score = score
                    play_ctrl = d
            except Exception:
                continue

        if not play_ctrl:
            return {
                "status": "error",
                "error": f"No play button found for '{query}'",
                "hint": "Try a more specific search query",
            }

        # 4. Click play (invoke first, fallback click_input)
        click_method = "invoke"
        try:
            play_ctrl.invoke()
        except Exception:
            click_method = "click_input"
            conn.ensure_foreground()
            play_ctrl.click_input()

        conn._controls_cache = None

        return {
            "status": "ok",
            "action": "play",
            "app": app_query,
            "query": query,
            "track": play_ctrl.window_text() if hasattr(play_ctrl, 'window_text') else "",
            "method": click_method,
        }

    def _handle_info(self, app_query: str) -> dict:
        """Get window info without full scan."""
        conn = self._get_or_connect(app_query)
        return {
            "status": "ok",
            "action": "info",
            "app": app_query,
            "window_title": conn.window_title,
            "backend": conn.backend,
            "pid": conn.pid,
        }

    def _handle_focus(self, app_query: str) -> dict:
        """Focus an app window."""
        conn = self._get_or_connect(app_query)
        conn.ensure_foreground()
        return {
            "status": "ok",
            "action": "focus",
            "app": app_query,
            "window_title": conn.window_title,
        }

    def _handle_scan(self, app_query: str, cmd: dict) -> dict:
        """Scan controls using cached tree."""
        conn = self._get_or_connect(app_query)
        filter_type = cmd.get("filter_type")
        filter_name = cmd.get("filter_name")
        refresh = cmd.get("refresh", False)

        descs = conn.get_descendants(force_refresh=refresh)

        from pc_control.desktop.inspector import _INTERACTIVE_TYPES

        controls = []
        for d in descs:
            info = self._desc_info(d)
            if not info:
                continue
            if filter_type and filter_type.lower() not in info["type"].lower():
                continue
            if filter_name and filter_name.lower() not in info.get("name", "").lower():
                continue
            if not filter_type and info["type"] not in _INTERACTIVE_TYPES:
                continue
            controls.append(info)

        return {
            "status": "ok",
            "action": "scan",
            "app": app_query,
            "window_title": conn.window_title,
            "backend": conn.backend,
            "count": len(controls),
            "controls": controls,
        }

    def _handle_click(self, app_query: str, cmd: dict) -> dict:
        """Find and click a control."""
        conn = self._get_or_connect(app_query)
        name = cmd.get("name")
        control_type = cmd.get("control_type")
        control_path = cmd.get("control_path")

        foreground = cmd.get("foreground", False)

        if control_path:
            # Legacy path-based
            from pc_control.desktop.inspector import _navigate_to_control
            if foreground:
                conn.ensure_foreground()
            win = conn.get_window()
            ctrl = _navigate_to_control(win, control_path)
            if not ctrl:
                return {"status": "error", "error": f"Control not found: {control_path}"}
        elif name or control_type:
            ctrl = self._find_control(conn, name, control_type)
            if not ctrl:
                search = name or control_type
                return {"status": "error", "error": f"Control not found: {search}"}
        else:
            return {"status": "error", "error": "Must specify name, control_type, or control_path"}

        # Try invoke() first (works in background, no mouse movement)
        click_method = "invoke"
        try:
            ctrl.invoke()
        except Exception:
            # Fallback to click_input (needs foreground)
            click_method = "click_input"
            conn.ensure_foreground()
            ctrl.click_input()

        result = {
            "status": "ok",
            "action": "desktop_click",
            "app": app_query,
            "method": click_method,
            "control_type": ctrl.friendly_class_name() if hasattr(ctrl, 'friendly_class_name') else "unknown",
            "control_name": ctrl.window_text() if hasattr(ctrl, 'window_text') else "",
        }
        try:
            rect = ctrl.rectangle()
            result["clicked_at"] = {"x": (rect.left + rect.right) // 2, "y": (rect.top + rect.bottom) // 2}
        except Exception:
            pass

        # Invalidate cache after interaction (UI may have changed)
        conn._controls_cache = None

        return result

    def _handle_type(self, app_query: str, cmd: dict) -> dict:
        """Find a control and type text into it."""
        conn = self._get_or_connect(app_query)
        text = cmd.get("text", "")
        name = cmd.get("name")
        control_type = cmd.get("control_type")
        control_path = cmd.get("control_path")

        foreground = cmd.get("foreground", False)

        if control_path:
            from pc_control.desktop.inspector import _navigate_to_control
            if foreground:
                conn.ensure_foreground()
            win = conn.get_window()
            ctrl = _navigate_to_control(win, control_path)
            if not ctrl:
                return {"status": "error", "error": f"Control not found: {control_path}"}
        elif name or control_type:
            ctrl = self._find_control(conn, name, control_type)
            if not ctrl:
                return {"status": "error", "error": f"Control not found: {name or control_type}"}
        else:
            return {"status": "error", "error": "Must specify name, control_type, or control_path"}

        # Try set_edit_text / ValuePattern first (works in background)
        try:
            ctrl.set_edit_text(text)
        except Exception:
            try:
                # Try UIA ValuePattern
                ctrl.iface_value.SetValue(text)
            except Exception:
                # Fallback: need foreground for keyboard simulation
                was_minimized = False
                try:
                    was_minimized = conn.get_window().is_minimized()
                except Exception:
                    pass
                conn.ensure_foreground()
                ctrl.click_input()
                time.sleep(0.1)
                # Select all and clear before typing
                import pyautogui
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.05)
                pyautogui.press('delete')
                time.sleep(0.05)
                pyautogui.write(text, interval=0.02)
                # Restore previous state if was minimized
                if was_minimized:
                    time.sleep(0.3)
                    try:
                        conn.get_window().minimize()
                    except Exception:
                        pass

        conn._controls_cache = None

        return {
            "status": "ok",
            "action": "desktop_type",
            "app": app_query,
            "control_name": ctrl.window_text() if hasattr(ctrl, 'window_text') else "",
            "length": len(text),
        }

    def _find_control(self, conn: AppConnection, name: str = None, control_type: str = None):
        """Find a control in cached descendants."""
        descs = conn.get_descendants()
        for d in descs:
            try:
                d_name = d.window_text() if hasattr(d, 'window_text') else ""
                d_type = d.friendly_class_name() if hasattr(d, 'friendly_class_name') else ""

                match = True
                if name and name.lower() not in d_name.lower():
                    match = False
                if control_type and control_type.lower() not in d_type.lower():
                    match = False
                if match and (name or control_type):
                    return d
            except Exception:
                continue
        return None

    @staticmethod
    def _desc_info(ctrl) -> dict | None:
        """Extract compact info from a control."""
        try:
            ct = ctrl.friendly_class_name() if hasattr(ctrl, 'friendly_class_name') else type(ctrl).__name__
            title = ctrl.window_text() if hasattr(ctrl, 'window_text') else ""
            aid = ""
            try:
                if hasattr(ctrl, 'automation_id'):
                    aid = ctrl.automation_id() or ""
            except Exception:
                pass

            if not title and not aid:
                return None

            info = {"type": ct, "name": title}
            if aid:
                info["id"] = aid

            try:
                rect = ctrl.rectangle()
                info["rect"] = {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}
                info["center"] = {"x": (rect.left + rect.right) // 2, "y": (rect.top + rect.bottom) // 2}
            except Exception:
                pass

            return info
        except Exception:
            return None

    # ── Server ─────────────────────────────────────────────

    def start_server(self):
        """Start the TCP server."""
        self._running = True
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(1.0)
        server.bind((DAEMON_HOST, DAEMON_PORT))
        server.listen(5)

        # Write PID file
        DAEMON_PID_FILE.write_text(str(os.getpid()))

        print(json.dumps({
            "status": "ok",
            "action": "daemon_started",
            "pid": os.getpid(),
            "host": DAEMON_HOST,
            "port": DAEMON_PORT,
        }))
        sys.stdout.flush()

        try:
            while self._running:
                try:
                    client, addr = server.accept()
                    t = threading.Thread(target=self._handle_client, args=(client,), daemon=True)
                    t.start()
                except TimeoutError:
                    continue
        except KeyboardInterrupt:
            pass
        finally:
            server.close()
            if DAEMON_PID_FILE.exists():
                DAEMON_PID_FILE.unlink()

    def _handle_client(self, client: socket.socket):
        """Handle a single client connection."""
        try:
            client.settimeout(30.0)
            data = b""
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                data += chunk
                # Check for complete JSON
                try:
                    cmd = json.loads(data.decode("utf-8"))
                    break
                except json.JSONDecodeError:
                    continue

            if data:
                cmd = json.loads(data.decode("utf-8"))
                if cmd.get("action") == "shutdown":
                    result = {"status": "ok", "action": "shutdown"}
                    client.sendall(json.dumps(result, ensure_ascii=False).encode("utf-8"))
                    self._running = False
                else:
                    result = self.handle_command(cmd)
                    client.sendall(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            try:
                error = json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)
                client.sendall(error.encode("utf-8"))
            except Exception:
                pass
        finally:
            client.close()

    def stop(self):
        self._running = False


# ── Client ─────────────────────────────────────────────

def send_command(cmd: dict, timeout: float = 30.0) -> dict:
    """Send a command to the daemon and return the result."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((DAEMON_HOST, DAEMON_PORT))
        sock.sendall(json.dumps(cmd, ensure_ascii=False).encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)

        data = b""
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            data += chunk

        return json.loads(data.decode("utf-8"))
    finally:
        sock.close()


def is_daemon_running() -> bool:
    """Check if the daemon is running."""
    try:
        result = send_command({"action": "ping"}, timeout=2.0)
        return result.get("status") == "ok"
    except Exception:
        return False


def start_daemon():
    """Start the daemon (called in the background process)."""
    daemon = DesktopDaemon()
    daemon.start_server()


def stop_daemon() -> dict:
    """Send shutdown command to running daemon."""
    try:
        return send_command({"action": "shutdown"}, timeout=5.0)
    except Exception as e:
        # Try killing by PID file
        if DAEMON_PID_FILE.exists():
            pid = int(DAEMON_PID_FILE.read_text().strip())
            try:
                os.kill(pid, signal.SIGTERM)
                DAEMON_PID_FILE.unlink()
                return {"status": "ok", "action": "killed", "pid": pid}
            except Exception:
                DAEMON_PID_FILE.unlink()
        return {"status": "error", "error": str(e)}


def daemon_status() -> dict:
    """Get daemon status."""
    if is_daemon_running():
        result = send_command({"action": "ping"})
        result["daemon"] = "running"
        if DAEMON_PID_FILE.exists():
            result["pid"] = int(DAEMON_PID_FILE.read_text().strip())
        return result
    else:
        return {"status": "ok", "daemon": "stopped"}
