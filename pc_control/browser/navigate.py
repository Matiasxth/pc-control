"""Browser navigation — goto, click, fill, text, eval, screenshot, etc."""

import json
from datetime import datetime
from pathlib import Path

from pc_control.browser.session import browser_connection
from pc_control.config import SCREENSHOTS_DIR


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def goto(url, new_tab=False):
    with browser_connection() as (browser, ctx, page):
        if new_tab:
            page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        _output({"status": "ok", "action": "goto", "url": page.url, "title": page.title()})


def tabs():
    with browser_connection() as (browser, ctx, page):
        tab_list = []
        for i, p in enumerate(ctx.pages):
            tab_list.append({"index": i, "url": p.url, "title": p.title()})
        _output({"status": "ok", "action": "tabs", "count": len(tab_list), "tabs": tab_list})


def switch_tab(index):
    with browser_connection() as (browser, ctx, page):
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


def close_tab(index):
    with browser_connection() as (browser, ctx, page):
        if index < 0 or index >= len(ctx.pages):
            _output({"status": "error", "error": f"Tab index {index} out of range"})
            return
        target = ctx.pages[index]
        url = target.url
        target.close()
        _output({"status": "ok", "action": "close_tab", "index": index, "url": url})


def click(selector):
    with browser_connection() as (browser, ctx, page):
        page.click(selector, timeout=10000)
        _output({"status": "ok", "action": "click", "selector": selector})


def fill(selector, value):
    with browser_connection() as (browser, ctx, page):
        page.fill(selector, value, timeout=10000)
        _output({"status": "ok", "action": "fill", "selector": selector, "length": len(value)})


def select_option(selector, value):
    with browser_connection() as (browser, ctx, page):
        page.select_option(selector, value, timeout=10000)
        _output({"status": "ok", "action": "select", "selector": selector, "value": value})


def check(selector):
    with browser_connection() as (browser, ctx, page):
        page.check(selector, timeout=10000)
        _output({"status": "ok", "action": "check", "selector": selector})


def text(selector):
    with browser_connection() as (browser, ctx, page):
        content = page.inner_text(selector, timeout=10000)
        _output({"status": "ok", "action": "text", "selector": selector, "text": content})


def html(selector):
    with browser_connection() as (browser, ctx, page):
        content = page.inner_html(selector, timeout=10000)
        _output({"status": "ok", "action": "html", "selector": selector, "html": content})


def attr(selector, attribute):
    with browser_connection() as (browser, ctx, page):
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


def evaluate(js):
    with browser_connection() as (browser, ctx, page):
        result = page.evaluate(js)
        _output({"status": "ok", "action": "eval", "result": result})


def screenshot(selector=None, output=None):
    with browser_connection() as (browser, ctx, page):
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


def wait_for(selector, timeout=10):
    with browser_connection() as (browser, ctx, page):
        page.wait_for_selector(selector, timeout=timeout * 1000)
        _output({"status": "ok", "action": "wait", "selector": selector})


def save_storage(path):
    with browser_connection() as (browser, ctx, page):
        ctx.storage_state(path=path)
        _output({"status": "ok", "action": "save_storage", "path": path})


def load_storage(path):
    with browser_connection() as (browser, ctx, page):
        # Load cookies from storage state file
        import json as json_mod

        storage = json_mod.loads(Path(path).read_text())
        if "cookies" in storage:
            ctx.add_cookies(storage["cookies"])
        _output({"status": "ok", "action": "load_storage", "path": path})
