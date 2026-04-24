"""WhatsApp Web monitor daemon — keeps Playwright alive to capture messages."""
import json
import signal
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

MONITOR_JS = (Path(__file__).parent.parent / "scripts" / "whatsapp_monitor.js").read_text(encoding="utf-8")


def main():
    if len(sys.argv) < 3:
        print("Usage: whatsapp_daemon.py <port> <events_file>", file=sys.stderr)
        sys.exit(1)

    port = int(sys.argv[1])
    events_file = Path(sys.argv[2])

    events = []
    running = True

    def on_signal(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def save_events():
        events_file.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")

    def on_message(msg_data):
        """Called from browser JS via expose_function."""
        events.append(msg_data)
        save_events()

    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp(f"http://localhost:{port}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()

        # Find WhatsApp Web tab
        wa_page = None
        for page in ctx.pages:
            if "web.whatsapp.com" in page.url:
                wa_page = page
                break

        if not wa_page:
            print("MONITOR_ERROR:WhatsApp Web tab not found", flush=True)
            sys.exit(1)

        # Expose callback function
        wa_page.expose_function("__pcWhatsAppMsg", on_message)

        # Inject monitor JS
        wa_page.evaluate(MONITOR_JS)
        ctx.add_init_script(MONITOR_JS)

        print(f"MONITOR_READY:{events_file}", flush=True)

        # Keep alive
        while running:
            try:
                wa_page.wait_for_timeout(500)
                if not browser.is_connected():
                    break
            except Exception:
                break

        save_events()

    except Exception as e:
        print(f"MONITOR_ERROR:{e}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        try:
            browser.close()
        except Exception:
            pass
        pw.stop()


if __name__ == "__main__":
    main()
