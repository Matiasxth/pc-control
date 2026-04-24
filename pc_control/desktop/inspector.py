"""Desktop UI inspector — read controls directly via pywinauto."""
import io
import json
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    from pywinauto import Application
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _check():
    if not HAS_PYWINAUTO:
        _output({"status": "error", "error": "pywinauto not installed"})
        sys.exit(1)


# App hints for common applications — maps query keyword to connect kwargs
_APP_HINTS = {
    "outlook": {"class_name": "rctrl_renwnd32"},
    "excel": {"class_name": "XLMAIN"},
    "word": {"class_name": "OpusApp"},
    "notepad": {"class_name": "Notepad"},
}

# Apps whose window title changes dynamically (e.g. to current song/document)
# For these, we find the PID first via win32gui and connect by process
_DYNAMIC_TITLE_APPS = {
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "slack": "Slack.exe",
    "vscode": "Code.exe",
    "code": "Code.exe",
    "teams": "ms-teams.exe",
}


def _find_pid_by_process_name(process_name: str) -> list[int]:
    """Find all PIDs of a running process by executable name."""
    pids = []
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                pids.append(proc.info['pid'])
    except Exception:
        pass
    return pids


def _find_pid_by_title(query: str) -> int | None:
    """Find PID by partial window title match using win32gui."""
    try:
        import win32gui
        import win32process
        results = []

        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and query.lower() in title.lower():
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    results.append(pid)
            return True

        win32gui.EnumWindows(callback, None)
        return results[0] if results else None
    except Exception:
        return None


def _connect(app_query: str):
    """Connect to an application. Tries PID-based connection for dynamic-title
    apps, then title-based with UIA, then win32 fallback."""
    _check()
    query_lower = app_query.lower()

    # Strategy 1: dynamic-title apps — connect by PID (try all PIDs)
    for key, exe_name in _DYNAMIC_TITLE_APPS.items():
        if key in query_lower:
            pids = _find_pid_by_process_name(exe_name)
            for pid in pids:
                try:
                    app = Application(backend="uia").connect(process=pid, timeout=3)
                    win = app.top_window()
                    # Verify it has a real window (not a background process)
                    if win.window_text():
                        return app, "uia"
                except Exception:
                    continue
            break

    # Strategy 2: try finding PID via window title (catches renamed windows)
    pid = _find_pid_by_title(app_query)
    if pid:
        try:
            app = Application(backend="uia").connect(process=pid, timeout=5)
            return app, "uia"
        except Exception:
            pass

    # Strategy 3: classic title/class_name match
    hint = None
    for key, val in _APP_HINTS.items():
        if key in query_lower:
            hint = val
            break

    connect_kwargs = {}
    if hint and "class_name" in hint:
        connect_kwargs["class_name"] = hint["class_name"]
    else:
        connect_kwargs["title_re"] = f".*{app_query}.*"

    # Try UIA backend first (modern apps)
    try:
        app = Application(backend="uia").connect(**connect_kwargs, timeout=5)
        return app, "uia"
    except Exception:
        pass

    # Fallback to win32 backend (legacy apps)
    try:
        app = Application(backend="win32").connect(**connect_kwargs, timeout=5)
        return app, "win32"
    except Exception as e:
        _output({"status": "error", "error": f"Cannot connect to '{app_query}': {e}"})
        return None, None


def _control_info(ctrl, include_children=False, depth=0, max_depth=3, path_prefix=""):
    """Extract control information as a dict."""
    try:
        info = {
            "control_type": ctrl.friendly_class_name() if hasattr(ctrl, 'friendly_class_name') else type(ctrl).__name__,
            "title": ctrl.window_text() if hasattr(ctrl, 'window_text') else "",
            "visible": ctrl.is_visible() if hasattr(ctrl, 'is_visible') else True,
            "enabled": ctrl.is_enabled() if hasattr(ctrl, 'is_enabled') else True,
        }

        # Build path
        name = info["title"] or info["control_type"]
        current_path = f"{path_prefix}>{name}" if path_prefix else name
        info["path"] = current_path

        # Get rectangle
        try:
            rect = ctrl.rectangle()
            info["rect"] = {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}
        except Exception:
            pass

        # Get value for specific control types
        try:
            if hasattr(ctrl, 'get_value'):
                info["value"] = ctrl.get_value()
            elif hasattr(ctrl, 'texts'):
                texts = ctrl.texts()
                if texts:
                    info["value"] = texts[0] if len(texts) == 1 else texts
        except Exception:
            pass

        # Get automation ID (UIA)
        try:
            if hasattr(ctrl, 'automation_id'):
                aid = ctrl.automation_id()
                if aid:
                    info["automation_id"] = aid
        except Exception:
            pass

        # Children
        if include_children and depth < max_depth:
            try:
                children = ctrl.children()
                if children:
                    info["children"] = []
                    for child in children[:50]:  # Limit to avoid overwhelming output
                        child_info = _control_info(
                            child,
                            include_children=True,
                            depth=depth + 1,
                            max_depth=max_depth,
                            path_prefix=current_path,
                        )
                        if child_info:
                            info["children"].append(child_info)
            except Exception:
                pass

        return info
    except Exception:
        return None


def _desc_info(ctrl) -> dict | None:
    """Extract compact info from a single control (for scan)."""
    try:
        ct = ctrl.friendly_class_name() if hasattr(ctrl, 'friendly_class_name') else type(ctrl).__name__
        title = ctrl.window_text() if hasattr(ctrl, 'window_text') else ""
        aid = ""
        try:
            if hasattr(ctrl, 'automation_id'):
                aid = ctrl.automation_id() or ""
        except Exception:
            pass

        # Skip empty, invisible, or pure layout controls
        if not title and not aid:
            return None

        info = {"type": ct, "name": title}
        if aid:
            info["id"] = aid

        # Rectangle for click targeting
        try:
            rect = ctrl.rectangle()
            info["rect"] = {"left": rect.left, "top": rect.top, "right": rect.right, "bottom": rect.bottom}
            # Center point for easy clicking
            info["center"] = {"x": (rect.left + rect.right) // 2, "y": (rect.top + rect.bottom) // 2}
        except Exception:
            pass

        return info
    except Exception:
        return None


# Control types that represent interactive or informative elements
_INTERACTIVE_TYPES = {
    'Button', 'Edit', 'ComboBox', 'CheckBox', 'RadioButton',
    'MenuItem', 'ListItem', 'DataItem', 'TabItem', 'TreeItem',
    'Hyperlink', 'Slider', 'Spinner', 'Static', 'Text',
    'Document', 'Image', 'ListView', 'Menu', 'MenuBar',
    'ToolBar', 'Toolbar', 'StatusBar',
}


def scan_app(app_query: str, filter_type: str = None, filter_name: str = None):
    """Scan ALL controls of an app using descendants() — fast flat list.

    This is the primary way to discover what's in an app.
    Returns interactive controls with their center coordinates for clicking.
    """
    app, backend = _connect(app_query)
    if not app:
        return

    try:
        win = app.top_window()
        title = win.window_text()
        descs = win.descendants()

        controls = []
        for d in descs:
            info = _desc_info(d)
            if not info:
                continue

            # Filter by type if specified
            if filter_type and filter_type.lower() not in info["type"].lower():
                continue

            # Filter by name if specified
            if filter_name and filter_name.lower() not in info.get("name", "").lower():
                continue

            # By default, only show interactive types (skip layout containers)
            if not filter_type and info["type"] not in _INTERACTIVE_TYPES:
                continue

            controls.append(info)

        _output({
            "status": "ok",
            "action": "scan",
            "app": app_query,
            "window_title": title,
            "backend": backend,
            "count": len(controls),
            "controls": controls,
        })
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def find_control(app_query: str, name: str = None, control_type: str = None, automation_id: str = None):
    """Find a specific control by name, type, or automation_id using descendants().

    Returns the first matching control with its coordinates.
    Much more reliable than path-based navigation for Electron/web apps.
    """
    app, backend = _connect(app_query)
    if not app:
        return None, None, None

    try:
        win = app.top_window()
        descs = win.descendants()

        for d in descs:
            try:
                d_name = d.window_text() if hasattr(d, 'window_text') else ""
                d_type = d.friendly_class_name() if hasattr(d, 'friendly_class_name') else ""
                d_aid = ""
                try:
                    d_aid = d.automation_id() or ""
                except Exception:
                    pass

                match = True
                if name and name.lower() not in d_name.lower():
                    match = False
                if control_type and control_type.lower() not in d_type.lower():
                    match = False
                if automation_id and automation_id != d_aid:
                    match = False

                if match and (name or control_type or automation_id):
                    return app, d, backend
            except Exception:
                continue

        return app, None, backend
    except Exception:
        return None, None, None


def inspect_app(app_query: str):
    """Get top-level window info and immediate children."""
    app, backend = _connect(app_query)
    if not app:
        return

    try:
        win = app.top_window()
        info = _control_info(win, include_children=True, max_depth=1)
        info["backend"] = backend
        _output({"status": "ok", "action": "inspect", "app": app_query, "window": info})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def get_tree(app_query: str, depth: int = 3):
    """Get full control tree with paths."""
    app, backend = _connect(app_query)
    if not app:
        return

    try:
        win = app.top_window()
        info = _control_info(win, include_children=True, max_depth=depth)
        info["backend"] = backend
        _output({"status": "ok", "action": "tree", "app": app_query, "depth": depth, "window": info})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def read_control(app_query: str, control_path: str):
    """Read text/value from a specific control using path notation."""
    app, backend = _connect(app_query)
    if not app:
        return

    try:
        win = app.top_window()
        ctrl = _navigate_to_control(win, control_path)
        if ctrl is None:
            _output({"status": "error", "error": f"Control not found: {control_path}"})
            return

        # Try multiple ways to get text
        text = None
        try:
            text = ctrl.window_text()
        except Exception:
            pass

        if not text:
            try:
                texts = ctrl.texts()
                text = "\n".join(t for t in texts if t)
            except Exception:
                pass

        if not text:
            try:
                text = ctrl.get_value()
            except Exception:
                pass

        info = _control_info(ctrl)
        info["text"] = text or ""
        _output({"status": "ok", "action": "read", "control_path": control_path, "control": info})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def _navigate_to_control(win, control_path: str):
    """Navigate to a control using path notation: 'Parent>Child>Target'."""
    segments = [s.strip() for s in control_path.split(">") if s.strip()]
    current = win

    for segment in segments:
        try:
            current = current.child_window(best_match=segment)
            # Force resolution
            current.wrapper_object()
        except Exception:
            return None

    return current
