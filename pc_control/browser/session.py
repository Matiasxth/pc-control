"""Browser session — connect/disconnect Playwright to persistent CDP browser."""

import json
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from pc_control.browser.daemon import _is_alive, _is_cdp_responsive, _load_state
from pc_control.browser.daemon import start as start_daemon
from pc_control.config import DEFAULT_CDP_PORT


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _ensure_browser():
    """Ensure browser is running, start if not."""
    state = _load_state()
    if state and _is_alive(state["pid"]) and _is_cdp_responsive(state["port"]):
        return state
    # Auto-start headless
    start_daemon(headed=False, port=DEFAULT_CDP_PORT)
    return _load_state()


@contextmanager
def browser_connection():
    """Context manager that yields (browser, default_context, active_page).

    Connects to the persistent CDP browser, yields the connection,
    then disconnects cleanly (browser stays alive).
    """
    state = _ensure_browser()
    if not state:
        raise RuntimeError("Could not start browser")

    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp(f"http://localhost:{state['port']}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.pages[-1] if ctx.pages else ctx.new_page()
        yield browser, ctx, page
    finally:
        try:
            browser.close()  # Disconnects Playwright, browser stays alive
        except Exception:
            pass
        pw.stop()
