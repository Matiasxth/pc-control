"""Playwright ↔ persistent Chromium (CDP) connection helper."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from pc_control.browser.daemon import _is_alive, _is_cdp_responsive, _load_state
from pc_control.browser.daemon import start as start_daemon
from pc_control.config import DEFAULT_CDP_PORT


def _output(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def _ensure_browser() -> dict | None:
    """Return current browser state, auto-starting the daemon if needed.

    A headless browser is spun up if no live CDP endpoint is already there.
    """
    state = _load_state()
    if state and _is_alive(state["pid"]) and _is_cdp_responsive(state["port"]):
        return state
    start_daemon(headed=False, port=DEFAULT_CDP_PORT)
    return _load_state()


@contextmanager
def browser_connection() -> Iterator[tuple[Browser, BrowserContext, Page]]:
    """Yield `(browser, default_context, active_page)` for the persistent browser.

    The Playwright client disconnects on exit but the underlying Chromium
    keeps running — that is the whole point of the CDP daemon model. The
    "active page" is the last tab in the default context, or a freshly
    created one if no tabs exist.

    Raises:
        RuntimeError: when the browser daemon could not be started.
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
            browser.close()  # disconnects Playwright; browser stays alive
        except Exception:
            pass
        pw.stop()
