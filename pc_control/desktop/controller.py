"""Desktop UI controller — interact with controls via pywinauto."""
import io
import json
import sys
import time

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pc_control.desktop.inspector import _connect, _navigate_to_control, find_control


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _ensure_foreground(app):
    """Ensure the app window is restored, visible, and in the foreground."""
    try:
        win = app.top_window()
        # Restore if minimized
        if win.is_minimized():
            win.restore()
            time.sleep(0.3)
        # Bring to front
        win.set_focus()
        time.sleep(0.2)
    except Exception:
        pass


def _resolve_control(app_query, control_path=None, name=None, control_type=None):
    """Resolve a control either by path (legacy) or by name/type (new).

    Returns (app, ctrl, info_dict) or outputs error and returns (None, None, None).
    """
    if name or (control_type and not control_path):
        # New: find by name/type using descendants()
        app, ctrl, backend = find_control(app_query, name=name, control_type=control_type)
        if not app:
            return None, None, None
        if ctrl is None:
            search = name or control_type
            _output({"status": "error", "error": f"Control not found: {search}"})
            return None, None, None
        return app, ctrl, {"name": name or "", "type": control_type or ""}
    elif control_path:
        # Legacy: path-based navigation
        app, backend = _connect(app_query)
        if not app:
            return None, None, None
        try:
            win = app.top_window()
            ctrl = _navigate_to_control(win, control_path)
            if ctrl is None:
                _output({"status": "error", "error": f"Control not found: {control_path}"})
                return None, None, None
            return app, ctrl, {"path": control_path}
        except Exception as e:
            _output({"status": "error", "error": str(e)})
            return None, None, None
    else:
        _output({"status": "error", "error": "Must specify --name or control_path"})
        return None, None, None


def click_control(app_query: str, control_path: str = None, name: str = None, control_type: str = None):
    """Click a control by path, name, or type."""
    app, ctrl, info = _resolve_control(app_query, control_path, name, control_type)
    if not ctrl:
        return

    try:
        _ensure_foreground(app)
        ctrl.click_input()
        result = {
            "status": "ok",
            "action": "desktop_click",
            "app": app_query,
            "control_type": ctrl.friendly_class_name() if hasattr(ctrl, 'friendly_class_name') else "unknown",
            "control_name": ctrl.window_text() if hasattr(ctrl, 'window_text') else "",
        }
        try:
            rect = ctrl.rectangle()
            result["clicked_at"] = {"x": (rect.left + rect.right) // 2, "y": (rect.top + rect.bottom) // 2}
        except Exception:
            pass
        _output(result)
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def type_in_control(app_query: str, control_path: str = None, text: str = "", name: str = None):
    """Type text into a control found by path or name."""
    app, ctrl, info = _resolve_control(app_query, control_path, name)
    if not ctrl:
        return

    try:
        _ensure_foreground(app)
        # Try set_edit_text first (for Edit controls)
        try:
            ctrl.set_edit_text(text)
        except Exception:
            # Fallback to type_keys (simulates keyboard)
            ctrl.click_input()
            ctrl.type_keys(text, with_spaces=True, pause=0.02)

        _output({
            "status": "ok",
            "action": "desktop_type",
            "app": app_query,
            "control_name": ctrl.window_text() if hasattr(ctrl, 'window_text') else "",
            "length": len(text),
        })
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def select_item(app_query: str, control_path: str, item: str):
    """Select an item in a list, combo box, or tree view."""
    app, backend = _connect(app_query)
    if not app:
        return

    try:
        _ensure_foreground(app)
        win = app.top_window()
        ctrl = _navigate_to_control(win, control_path)
        if ctrl is None:
            _output({"status": "error", "error": f"Control not found: {control_path}"})
            return

        ctrl.select(item)
        _output({
            "status": "ok",
            "action": "desktop_select",
            "app": app_query,
            "control_path": control_path,
            "item": item,
        })
    except Exception as e:
        _output({"status": "error", "error": str(e)})
