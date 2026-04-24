"""Desktop UI controller — interact with controls via pywinauto."""

from __future__ import annotations

import io
import json
import sys
import time
from typing import Any

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pc_control.desktop.inspector import _connect, _navigate_to_control, find_control


def _output(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def _ensure_foreground(app: Any) -> None:
    """Restore, focus, and bring the app's top window to the front.

    Errors are swallowed: this is a best-effort preflight before interaction.
    Some apps reject `set_focus` from a background process and we still want
    the subsequent click/type to attempt the action anyway.
    """
    try:
        win = app.top_window()
        if win.is_minimized():
            win.restore()
            time.sleep(0.3)
        win.set_focus()
        time.sleep(0.2)
    except Exception:
        pass


def _resolve_control(
    app_query: str,
    control_path: str | None = None,
    name: str | None = None,
    control_type: str | None = None,
) -> tuple[Any, Any, dict | None]:
    """Resolve a control via the new name/type API or the legacy path API.

    Exactly one lookup strategy is used:
      - `name` or (`control_type` without `control_path`) → uses
        `inspector.find_control()` to search the flattened descendant list.
      - `control_path` → uses `_navigate_to_control()` for
        "Parent>Child>Target" path traversal.

    Returns `(app, ctrl, info_dict)` on success, or `(None, None, None)` after
    emitting a JSON error on stdout when the control cannot be found or
    arguments are missing.
    """
    if name or (control_type and not control_path):
        app, ctrl, _backend = find_control(app_query, name=name, control_type=control_type)
        if not app:
            return None, None, None
        if ctrl is None:
            search = name or control_type
            _output({"status": "error", "error": f"Control not found: {search}"})
            return None, None, None
        return app, ctrl, {"name": name or "", "type": control_type or ""}
    elif control_path:
        app, _backend = _connect(app_query)
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


def click_control(
    app_query: str,
    control_path: str | None = None,
    name: str | None = None,
    control_type: str | None = None,
) -> None:
    """Click a control identified by path, name, or control type.

    The click is a real input event (`click_input`) — pywinauto drives the
    OS cursor, so the target window is forced to the foreground first. The
    JSON result includes `clicked_at` (screen coords of the control's center)
    when `rectangle()` is available.
    """
    app, ctrl, _info = _resolve_control(app_query, control_path, name, control_type)
    if not ctrl:
        return

    try:
        _ensure_foreground(app)
        ctrl.click_input()
        result: dict = {
            "status": "ok",
            "action": "desktop_click",
            "app": app_query,
            "control_type": (
                ctrl.friendly_class_name() if hasattr(ctrl, "friendly_class_name") else "unknown"
            ),
            "control_name": ctrl.window_text() if hasattr(ctrl, "window_text") else "",
        }
        try:
            rect = ctrl.rectangle()
            result["clicked_at"] = {
                "x": (rect.left + rect.right) // 2,
                "y": (rect.top + rect.bottom) // 2,
            }
        except Exception:
            pass
        _output(result)
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def type_in_control(
    app_query: str,
    control_path: str | None = None,
    text: str = "",
    name: str | None = None,
) -> None:
    """Type `text` into a control resolved by path or name.

    Tries `set_edit_text` first (works silently on pure Edit controls, even
    when the app is backgrounded). Falls back to a foreground `click_input`
    + `type_keys` sequence for controls that don't implement the value
    pattern.
    """
    app, ctrl, _info = _resolve_control(app_query, control_path, name)
    if not ctrl:
        return

    try:
        _ensure_foreground(app)
        try:
            ctrl.set_edit_text(text)
        except Exception:
            ctrl.click_input()
            ctrl.type_keys(text, with_spaces=True, pause=0.02)

        _output(
            {
                "status": "ok",
                "action": "desktop_type",
                "app": app_query,
                "control_name": ctrl.window_text() if hasattr(ctrl, "window_text") else "",
                "length": len(text),
            }
        )
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def select_item(app_query: str, control_path: str, item: str) -> None:
    """Select `item` in a list, combo box, or tree view reached by `control_path`.

    Delegates to pywinauto's `select(item)` which handles ComboBox, ListBox,
    and TreeView transparently.
    """
    app, _backend = _connect(app_query)
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
        _output(
            {
                "status": "ok",
                "action": "desktop_select",
                "app": app_query,
                "control_path": control_path,
                "item": item,
            }
        )
    except Exception as e:
        _output({"status": "error", "error": str(e)})
