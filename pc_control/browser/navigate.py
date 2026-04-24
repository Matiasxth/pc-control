"""Browser page actions — one connect/disconnect per command.

Every function here opens a fresh Playwright CDP connection to the persistent
Chromium, performs its action, and emits a single JSON object on stdout.
Keeping each command self-contained (instead of batching inside one session)
is what lets the CLI stay stateless from the caller's perspective.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pc_control.browser.session import browser_connection
from pc_control.config import SCREENSHOTS_DIR


def _output(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False))


def goto(url: str, new_tab: bool = False) -> None:
    """Navigate the active page (or a new tab) to `url` and wait for DOMContentLoaded."""
    with browser_connection() as (_browser, ctx, page):
        if new_tab:
            page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        _output({"status": "ok", "action": "goto", "url": page.url, "title": page.title()})


def tabs() -> None:
    """List open tabs in the default context with their index, URL, and title."""
    with browser_connection() as (_browser, ctx, _page):
        tab_list = [{"index": i, "url": p.url, "title": p.title()} for i, p in enumerate(ctx.pages)]
        _output({"status": "ok", "action": "tabs", "count": len(tab_list), "tabs": tab_list})


def switch_tab(index: int) -> None:
    """Bring tab `index` to the front. No-op if the index is out of range."""
    with browser_connection() as (_browser, ctx, _page):
        if index < 0 or index >= len(ctx.pages):
            _output(
                {
                    "status": "error",
                    "error": f"Tab index {index} out of range (0-{len(ctx.pages) - 1})",
                }
            )
            return
        target = ctx.pages[index]
        target.bring_to_front()
        _output(
            {
                "status": "ok",
                "action": "switch_tab",
                "index": index,
                "url": target.url,
                "title": target.title(),
            }
        )


def close_tab(index: int) -> None:
    """Close tab `index`."""
    with browser_connection() as (_browser, ctx, _page):
        if index < 0 or index >= len(ctx.pages):
            _output({"status": "error", "error": f"Tab index {index} out of range"})
            return
        target = ctx.pages[index]
        url = target.url
        target.close()
        _output({"status": "ok", "action": "close_tab", "index": index, "url": url})


def click(selector: str) -> None:
    """Click the element matched by `selector` (10 s timeout)."""
    with browser_connection() as (_browser, _ctx, page):
        page.click(selector, timeout=10000)
        _output({"status": "ok", "action": "click", "selector": selector})


def fill(selector: str, value: str) -> None:
    """Set the value of an input/textarea/contenteditable (10 s timeout)."""
    with browser_connection() as (_browser, _ctx, page):
        page.fill(selector, value, timeout=10000)
        _output({"status": "ok", "action": "fill", "selector": selector, "length": len(value)})


def select_option(selector: str, value: str) -> None:
    """Select option `value` in a `<select>` element (matched by value or label)."""
    with browser_connection() as (_browser, _ctx, page):
        page.select_option(selector, value, timeout=10000)
        _output({"status": "ok", "action": "select", "selector": selector, "value": value})


def check(selector: str) -> None:
    """Check a checkbox / radio."""
    with browser_connection() as (_browser, _ctx, page):
        page.check(selector, timeout=10000)
        _output({"status": "ok", "action": "check", "selector": selector})


def text(selector: str) -> None:
    """Emit `innerText` of the matched element."""
    with browser_connection() as (_browser, _ctx, page):
        content = page.inner_text(selector, timeout=10000)
        _output({"status": "ok", "action": "text", "selector": selector, "text": content})


def html(selector: str) -> None:
    """Emit `innerHTML` of the matched element."""
    with browser_connection() as (_browser, _ctx, page):
        content = page.inner_html(selector, timeout=10000)
        _output({"status": "ok", "action": "html", "selector": selector, "html": content})


def attr(selector: str, attribute: str) -> None:
    """Emit the value of `attribute` on the matched element (may be null)."""
    with browser_connection() as (_browser, _ctx, page):
        value = page.get_attribute(selector, attribute, timeout=10000)
        _output(
            {
                "status": "ok",
                "action": "attr",
                "selector": selector,
                "attribute": attribute,
                "value": value,
            }
        )


def evaluate(js: str) -> None:
    """Run `js` in the page and emit its serializable return value."""
    with browser_connection() as (_browser, _ctx, page):
        result = page.evaluate(js)
        _output({"status": "ok", "action": "eval", "result": result})


def screenshot(selector: str | None = None, output: str | None = None) -> None:
    """Capture the page (or a specific element) to `output` or a timestamped file."""
    with browser_connection() as (_browser, _ctx, page):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output) if output else SCREENSHOTS_DIR / f"browser_{ts}.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if selector:
            el = page.query_selector(selector)
            if el:
                el.screenshot(path=str(output_path))
            else:
                _output({"status": "error", "error": f"Element not found: {selector}"})
                return
        else:
            page.screenshot(path=str(output_path), full_page=False)

        _output(
            {
                "status": "ok",
                "action": "browser_screenshot",
                "path": str(output_path.resolve()),
                "url": page.url,
                "title": page.title(),
            }
        )


def wait_for(selector: str, timeout: int = 10) -> None:
    """Block until the first element matching `selector` is attached, or time out."""
    with browser_connection() as (_browser, _ctx, page):
        page.wait_for_selector(selector, timeout=timeout * 1000)
        _output({"status": "ok", "action": "wait", "selector": selector})


def save_storage(path: str) -> None:
    """Dump the active context's cookies and localStorage to a JSON file."""
    with browser_connection() as (_browser, ctx, _page):
        ctx.storage_state(path=path)
        _output({"status": "ok", "action": "save_storage", "path": path})


def load_storage(path: str) -> None:
    """Load cookies from a previously saved storage-state JSON file."""
    with browser_connection() as (_browser, ctx, _page):
        storage = json.loads(Path(path).read_text())
        if "cookies" in storage:
            ctx.add_cookies(storage["cookies"])
        _output({"status": "ok", "action": "load_storage", "path": path})
