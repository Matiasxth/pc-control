"""Background recorder daemon — keeps Playwright connection alive to capture events."""
import json
import signal
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    if len(sys.argv) < 3:
        print("Usage: recorder_daemon.py <port> <events_file> [url]", file=sys.stderr)
        sys.exit(1)

    port = int(sys.argv[1])
    events_file = Path(sys.argv[2])
    url = sys.argv[3] if len(sys.argv) > 3 else None

    events = []
    running = True

    def on_signal(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def save_events():
        events_file.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")

    def on_record(event_data):
        """Called from browser JS via expose_function."""
        events.append(event_data)
        save_events()

    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp(f"http://localhost:{port}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.pages[-1] if ctx.pages else ctx.new_page()

        # Expose Python function to JS — callable as window.__pcRecord(data)
        page.expose_function("__pcRecord", on_record)

        # Recorder JS that calls __pcRecord for each action
        recorder_js = RECORDER_JS_WITH_CALLBACK

        # Inject into current page
        page.evaluate(recorder_js)

        # Inject into all future navigations (persists because connection stays alive)
        ctx.add_init_script(recorder_js)

        # Navigate if URL provided
        if url:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Re-inject after navigation since goto happened after init_script
            page.evaluate(recorder_js)

        # Re-expose and re-inject when new pages are created
        def on_page(new_page):
            try:
                new_page.expose_function("__pcRecord", on_record)
            except Exception:
                pass  # Already exposed in this context

        ctx.on("page", on_page)

        # Write PID so the stop command can find us
        print(f"RECORDER_READY:{events_file}", flush=True)

        # Keep alive — use page.wait_for_timeout to keep Playwright event loop active
        # (time.sleep would block event processing and prevent expose_function callbacks)
        while running:
            try:
                page.wait_for_timeout(500)
                if not browser.is_connected():
                    break
            except Exception:
                break

        # Final save
        save_events()

    except Exception as e:
        print(f"RECORDER_ERROR:{e}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        try:
            browser.close()
        except Exception:
            pass
        pw.stop()


RECORDER_JS_WITH_CALLBACK = """
(function () {
  if (window.__pcRecorderActive) return;
  window.__pcRecorderActive = true;

  const startTime = Date.now();

  function getSelector(el) {
    if (!el || el === document.body || el === document.documentElement) return "body";
    if (el.dataset && el.dataset.testid) return '[data-testid="' + el.dataset.testid + '"]';
    if (el.id && el.id.length < 50 && !/^\\d|^:/.test(el.id)) return '#' + CSS.escape(el.id);
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return '[aria-label="' + ariaLabel + '"]';
    if (el.name && ["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName)) {
      return el.tagName.toLowerCase() + '[name="' + el.name + '"]';
    }
    if (["BUTTON", "A"].includes(el.tagName) || el.getAttribute("role") === "button") {
      const text = el.innerText?.trim();
      if (text && text.length < 80 && !text.includes("\\n")) return 'text=' + text;
    }
    if (el.placeholder) return '[placeholder="' + el.placeholder + '"]';
    return buildCssPath(el);
  }

  function buildCssPath(el) {
    const parts = [];
    let current = el;
    while (current && current !== document.body) {
      let sel = current.tagName.toLowerCase();
      if (current.className && typeof current.className === "string") {
        const classes = current.className.trim().split(/\\s+/)
          .filter(c => c.length < 30 && !/^[0-9]/.test(c)).slice(0, 2);
        if (classes.length) sel += "." + classes.map(CSS.escape).join(".");
      }
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(s => s.tagName === current.tagName);
        if (siblings.length > 1) sel += ':nth-child(' + (siblings.indexOf(current) + 1) + ')';
      }
      parts.unshift(sel);
      current = current.parentElement;
      if (parts.length >= 3) break;
    }
    return parts.join(" > ");
  }

  function record(action) {
    action.timestamp = Date.now() - startTime;
    action.url = window.location.href;
    if (typeof window.__pcRecord === 'function') {
      window.__pcRecord(action);
    }
  }

  // Click
  document.addEventListener("click", e => {
    const el = e.target;
    record({
      type: "click", selector: getSelector(el), tagName: el.tagName,
      text: (el.innerText || "").trim().slice(0, 100), x: e.clientX, y: e.clientY,
    });
  }, true);

  // Input (debounced)
  let inputTimer = null;
  let lastInputEl = null;
  document.addEventListener("input", e => {
    const el = e.target;
    if (!["INPUT", "TEXTAREA"].includes(el.tagName)) return;
    lastInputEl = el;
    clearTimeout(inputTimer);
    inputTimer = setTimeout(() => {
      record({
        type: "fill", selector: getSelector(el),
        value: el.type === "password" ? "***" : el.value,
        inputType: el.type || "text",
      });
    }, 300);
  }, true);

  // Select / Checkbox
  document.addEventListener("change", e => {
    const el = e.target;
    if (el.tagName === "SELECT") {
      record({ type: "select", selector: getSelector(el), value: el.value,
        text: el.options[el.selectedIndex]?.text || "" });
    } else if (el.type === "checkbox" || el.type === "radio") {
      record({ type: el.checked ? "check" : "uncheck", selector: getSelector(el) });
    }
  }, true);

  // Key presses
  document.addEventListener("keydown", e => {
    if (["Enter", "Tab", "Escape"].includes(e.key)) {
      record({ type: "key", key: e.key, selector: getSelector(e.target) });
    }
  }, true);

  // Navigation detection
  let lastUrl = window.location.href;
  const checkNav = () => {
    if (window.location.href !== lastUrl) {
      record({ type: "navigation", from: lastUrl, to: window.location.href });
      lastUrl = window.location.href;
    }
  };
  window.addEventListener("popstate", checkNav);
  window.addEventListener("hashchange", checkNav);
  setInterval(checkNav, 500);

  console.log("[PC Control] Recorder active (callback mode)");
})();
"""

if __name__ == "__main__":
    main()
