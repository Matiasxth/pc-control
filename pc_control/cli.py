"""CLI argument parser and command dispatcher."""
import argparse
import sys


def build_parser():
    parser = argparse.ArgumentParser(
        prog="pc_control",
        description="PC Control System — Full automation toolkit",
    )
    subparsers = parser.add_subparsers(dest="module", required=True)

    # ── Screen ──────────────────────────────────────────────
    screen_parser = subparsers.add_parser("screen", help="Screen capture")
    screen_sub = screen_parser.add_subparsers(dest="screen_command", required=True)

    shot = screen_sub.add_parser("shot", help="Take a screenshot")
    shot.add_argument("--region", help="Capture region: x1,y1,x2,y2")
    shot.add_argument("--window", help="Capture specific window (partial title)")
    shot.add_argument("--output", help="Output file path")
    shot.add_argument("--format", choices=["png", "jpeg"], default=None)
    shot.add_argument("--quality", type=int, default=None, help="JPEG quality (1-100)")

    screen_sub.add_parser("context", help="Text-based screen summary (no screenshot)")

    # ── Input ───────────────────────────────────────────────
    input_parser = subparsers.add_parser("input", help="Mouse and keyboard control")
    input_sub = input_parser.add_subparsers(dest="input_command", required=True)

    # Mouse: click
    click = input_sub.add_parser("click", help="Click at x,y")
    click.add_argument("x", type=int)
    click.add_argument("y", type=int)
    click.add_argument("--button", choices=["left", "right", "middle"], default="left")
    click.add_argument("--double", action="store_true")

    # Mouse: move
    move = input_sub.add_parser("move", help="Move mouse to x,y")
    move.add_argument("x", type=int)
    move.add_argument("y", type=int)
    move.add_argument("--duration", type=float, default=0.2)

    # Mouse: drag
    drag = input_sub.add_parser("drag", help="Drag from x1,y1 to x2,y2")
    drag.add_argument("x1", type=int)
    drag.add_argument("y1", type=int)
    drag.add_argument("x2", type=int)
    drag.add_argument("y2", type=int)
    drag.add_argument("--duration", type=float, default=0.5)
    drag.add_argument("--button", choices=["left", "right", "middle"], default="left")

    # Mouse: scroll
    scroll = input_sub.add_parser("scroll", help="Scroll at current position")
    scroll.add_argument("dx", type=int, help="Horizontal scroll")
    scroll.add_argument("dy", type=int, help="Vertical scroll (negative=down)")

    # Mouse: position
    input_sub.add_parser("position", help="Get current mouse position")

    # Mouse: smooth move
    smooth = input_sub.add_parser("smooth", help="Smooth mouse move with easing")
    smooth.add_argument("x", type=int)
    smooth.add_argument("y", type=int)
    smooth.add_argument("--duration", type=float, default=0.5)
    smooth.add_argument("--curve", choices=["ease", "ease-in", "ease-out", "ease-in-out", "linear"], default="ease")

    # Mouse: draw path
    draw = input_sub.add_parser("draw", help="Draw smooth curve through points")
    draw.add_argument("points", nargs="+", help="Points: x1,y1 x2,y2 x3,y3 ...")
    draw.add_argument("--duration", type=float, default=1.0)
    draw.add_argument("--no-click", action="store_true", help="Move without clicking")

    # Keyboard: type
    type_cmd = input_sub.add_parser("type", help="Type text")
    type_cmd.add_argument("text", help="Text to type")
    type_cmd.add_argument("--interval", type=float, default=0.02, help="Delay between chars")

    # Keyboard: key
    key = input_sub.add_parser("key", help="Press a single key")
    key.add_argument("key_name", help="Key name (enter, tab, escape, etc)")

    # Keyboard: hotkey
    hotkey = input_sub.add_parser("hotkey", help="Press key combination")
    hotkey.add_argument("keys", nargs="+", help="Keys (e.g., ctrl c)")

    # ── Windows ─────────────────────────────────────────────
    win_parser = subparsers.add_parser("windows", help="Window management")
    win_sub = win_parser.add_subparsers(dest="windows_command", required=True)

    wlist = win_sub.add_parser("list", help="List visible windows")
    wlist.add_argument("--filter", help="Filter by title")

    wfocus = win_sub.add_parser("focus", help="Focus a window")
    wfocus.add_argument("query", nargs="?", help="Window title (partial)")
    wfocus.add_argument("--hwnd", type=int, help="Window handle")

    wresize = win_sub.add_parser("resize", help="Resize a window")
    wresize.add_argument("query", help="Window title")
    wresize.add_argument("width", type=int)
    wresize.add_argument("height", type=int)

    wmove = win_sub.add_parser("move", help="Move a window")
    wmove.add_argument("query", help="Window title")
    wmove.add_argument("x", type=int)
    wmove.add_argument("y", type=int)

    wsnap = win_sub.add_parser("snap", help="Snap window (left, right, top-left, etc.)")
    wsnap.add_argument("query", nargs="?", help="Window title")
    wsnap.add_argument("position", choices=["left", "right", "top-left", "top-right", "bottom-left", "bottom-right", "maximize"])
    wsnap.add_argument("--hwnd", type=int, help="Window handle")

    for cmd_name in ["minimize", "maximize", "restore", "close"]:
        wcmd = win_sub.add_parser(cmd_name, help=f"{cmd_name.capitalize()} a window")
        wcmd.add_argument("query", nargs="?", help="Window title")
        wcmd.add_argument("--hwnd", type=int, help="Window handle")

    # Window layouts
    wlayout = win_sub.add_parser("layout", help="Save/restore window layouts")
    layout_sub = wlayout.add_subparsers(dest="layout_command", required=True)
    ls = layout_sub.add_parser("save", help="Save current layout")
    ls.add_argument("name", help="Layout name")
    ll = layout_sub.add_parser("load", help="Restore saved layout")
    ll.add_argument("name", help="Layout name")
    layout_sub.add_parser("list", help="List saved layouts")
    ld = layout_sub.add_parser("delete", help="Delete a layout")
    ld.add_argument("name", help="Layout name")

    # ── Browser ─────────────────────────────────────────────
    browser_parser = subparsers.add_parser("browser", help="Browser automation")
    browser_sub = browser_parser.add_subparsers(dest="browser_command", required=True)

    bstart = browser_sub.add_parser("start", help="Launch persistent browser")
    bstart.add_argument("--headed", action="store_true", help="Visible browser")
    bstart.add_argument("--port", type=int, default=None, help="CDP port")

    browser_sub.add_parser("status", help="Check browser status")
    browser_sub.add_parser("stop", help="Stop persistent browser")

    bgoto = browser_sub.add_parser("goto", help="Navigate to URL")
    bgoto.add_argument("url", help="Target URL")
    bgoto.add_argument("--new-tab", action="store_true")

    browser_sub.add_parser("tabs", help="List open tabs")

    btab = browser_sub.add_parser("tab", help="Switch or close tab")
    btab.add_argument("index", type=int, nargs="?", help="Tab index to switch to")
    btab.add_argument("--close", type=int, help="Close tab by index")

    bclick = browser_sub.add_parser("click", help="Click element")
    bclick.add_argument("selector", help="CSS/text/role selector")

    bfill = browser_sub.add_parser("fill", help="Fill input field")
    bfill.add_argument("selector", help="Input selector")
    bfill.add_argument("value", help="Text to fill")

    bselect = browser_sub.add_parser("select", help="Select dropdown option")
    bselect.add_argument("selector", help="Select element selector")
    bselect.add_argument("value", help="Option value or label")

    bcheck = browser_sub.add_parser("check", help="Check/uncheck checkbox")
    bcheck.add_argument("selector", help="Checkbox selector")

    btext = browser_sub.add_parser("text", help="Extract text from element")
    btext.add_argument("selector", help="Element selector")

    bhtml = browser_sub.add_parser("html", help="Extract innerHTML")
    bhtml.add_argument("selector", help="Element selector")

    battr = browser_sub.add_parser("attr", help="Get element attribute")
    battr.add_argument("selector", help="Element selector")
    battr.add_argument("attribute", help="Attribute name")

    beval = browser_sub.add_parser("eval", help="Execute JavaScript")
    beval.add_argument("js", help="JavaScript expression")

    bss = browser_sub.add_parser("screenshot", help="Screenshot current page")
    bss.add_argument("--selector", help="Screenshot specific element")
    bss.add_argument("--output", help="Output file path")

    bwait = browser_sub.add_parser("wait", help="Wait for element")
    bwait.add_argument("selector", help="Element selector")
    bwait.add_argument("--timeout", type=int, default=10, help="Timeout in seconds")

    bsave = browser_sub.add_parser("save-storage", help="Save cookies/storage")
    bsave.add_argument("path", help="Output JSON file")

    bload = browser_sub.add_parser("load-storage", help="Load cookies/storage")
    bload.add_argument("path", help="Input JSON file")

    # Browser recording
    brecord = browser_sub.add_parser("record", help="Record/replay browser actions")
    record_sub = brecord.add_subparsers(dest="record_command", required=True)

    rstart = record_sub.add_parser("start", help="Start recording")
    rstart.add_argument("url", nargs="?", help="URL to navigate to")
    rstart.add_argument("--session", help="Session name")

    rstop = record_sub.add_parser("stop", help="Stop recording")
    rstop.add_argument("--output", help="Output script path")

    record_sub.add_parser("list", help="List recordings")

    rplay = record_sub.add_parser("play", help="Replay recording")
    rplay.add_argument("script", help="Script file to replay")
    rplay.add_argument("--slow", type=int, default=0, help="Slow motion ms")

    # ── System ──────────────────────────────────────────────
    sys_parser = subparsers.add_parser("system", help="System monitoring")
    sys_sub = sys_parser.add_subparsers(dest="system_command", required=True)

    sys_sub.add_parser("info", help="CPU, RAM, disk overview")

    sprocs = sys_sub.add_parser("processes", help="List processes")
    sprocs.add_argument("--sort", choices=["cpu", "memory"], default="cpu")
    sprocs.add_argument("--filter", help="Filter by process name")
    sprocs.add_argument("--limit", type=int, default=20)

    skill = sys_sub.add_parser("kill", help="Kill a process")
    skill.add_argument("--pid", type=int, help="Process ID")
    skill.add_argument("--name", help="Process name")

    # ── Clipboard ───────────────────────────────────────────
    clip_parser = subparsers.add_parser("clipboard", help="Clipboard operations")
    clip_sub = clip_parser.add_subparsers(dest="clipboard_command", required=True)

    clip_sub.add_parser("get", help="Get clipboard content")

    cset = clip_sub.add_parser("set", help="Set clipboard content")
    cset.add_argument("text", help="Text to copy")

    clip_sub.add_parser("clear", help="Clear clipboard")

    # ── OCR ─────────────────────────────────────────────────
    ocr_parser = subparsers.add_parser("ocr", help="Text extraction from images")
    ocr_sub = ocr_parser.add_subparsers(dest="ocr_command", required=True)

    ocr_file = ocr_sub.add_parser("file", help="OCR an image file")
    ocr_file.add_argument("path", help="Image file path")

    ocr_screen = ocr_sub.add_parser("screen", help="Screenshot + OCR")
    ocr_screen.add_argument("--region", help="Region: x1,y1,x2,y2")
    ocr_screen.add_argument("--window", help="Window title")

    # ── Desktop ──────────────────────────────────────────
    desk_parser = subparsers.add_parser("desktop", help="Desktop UI automation")
    desk_sub = desk_parser.add_subparsers(dest="desktop_command", required=True)

    dinspect = desk_sub.add_parser("inspect", help="Inspect app controls")
    dinspect.add_argument("app", help="App title (partial match)")

    dtree = desk_sub.add_parser("tree", help="Control tree (hierarchical)")
    dtree.add_argument("app", help="App title")
    dtree.add_argument("--depth", type=int, default=3, help="Tree depth")

    dscan = desk_sub.add_parser("scan", help="Scan ALL controls (flat, fast)")
    dscan.add_argument("app", help="App title or keyword (e.g. 'spotify', 'chrome')")
    dscan.add_argument("--type", help="Filter by control type (Button, Edit, etc.)")
    dscan.add_argument("--name", help="Filter by name/text (partial match)")
    dscan.add_argument("--refresh", action="store_true", help="Force cache refresh")

    dplay = desk_sub.add_parser("play", help="Search and play (Spotify)")
    dplay.add_argument("app", help="App (e.g. 'spotify')")
    dplay.add_argument("query", help="Song/artist to search and play")

    # Daemon lifecycle
    ddaemon = desk_sub.add_parser("daemon", help="Persistent daemon for fast interaction")
    daemon_sub = ddaemon.add_subparsers(dest="daemon_command", required=True)
    daemon_sub.add_parser("start", help="Start background daemon")
    daemon_sub.add_parser("stop", help="Stop daemon")
    daemon_sub.add_parser("status", help="Check daemon status")

    dread = desk_sub.add_parser("read", help="Read control text/value")
    dread.add_argument("app", help="App title")
    dread.add_argument("control_path", help="Path to control (Parent>Child>Target)")

    dclick = desk_sub.add_parser("click", help="Click a control by path or name")
    dclick.add_argument("app", help="App title")
    dclick.add_argument("control_path", nargs="?", help="Path to control (legacy)")
    dclick.add_argument("--name", help="Find and click by name/text")
    dclick.add_argument("--type", dest="control_type", help="Filter by control type")

    dtype = desk_sub.add_parser("type", help="Type into a control")
    dtype.add_argument("app", help="App title")
    dtype.add_argument("text", help="Text to type")
    dtype.add_argument("--path", dest="control_path", help="Path to control (legacy)")
    dtype.add_argument("--name", help="Find control by name/text")

    dselect = desk_sub.add_parser("select", help="Select item in list/combo")
    dselect.add_argument("app", help="App title")
    dselect.add_argument("control_path", help="Path to control")
    dselect.add_argument("item", help="Item to select")

    # ── Vision ──────────────────────────────────────────────
    vis_parser = subparsers.add_parser("vision", help="Smart screen analysis")
    vis_sub = vis_parser.add_subparsers(dest="vision_command", required=True)

    vdiff = vis_sub.add_parser("diff", help="Compare two images")
    vdiff.add_argument("path1", help="First image")
    vdiff.add_argument("path2", help="Second image")
    vdiff.add_argument("--threshold", type=int, default=30)

    vds = vis_sub.add_parser("diff-screen", help="Compare current screen to reference")
    vds.add_argument("--reference", help="Reference image path")

    vft = vis_sub.add_parser("find-text", help="Find text on screen with coordinates")
    vft.add_argument("query", help="Text to search for")
    vft.add_argument("--region", help="Region: x1,y1,x2,y2")
    vft.add_argument("--window", help="Window title")

    vfi = vis_sub.add_parser("find-image", help="Find image/icon on screen")
    vfi.add_argument("template", help="Template image path")
    vfi.add_argument("--threshold", type=float, default=0.8)

    vel = vis_sub.add_parser("elements", help="Detect UI elements on screen")
    vel.add_argument("--region", help="Region: x1,y1,x2,y2")
    vel.add_argument("--window", help="Window title")

    # ── Chat ────────────────────────────────────────────────
    chat_parser = subparsers.add_parser("chat", help="Messaging services")
    chat_sub = chat_parser.add_subparsers(dest="chat_service", required=True)

    wa_parser = chat_sub.add_parser("whatsapp", help="WhatsApp Web")
    wa_sub = wa_parser.add_subparsers(dest="whatsapp_command", required=True)

    wa_sub.add_parser("start", help="Open WhatsApp Web")
    wa_sub.add_parser("status", help="Check login and monitor status")

    wa_send = wa_sub.add_parser("send", help="Send a message")
    wa_send.add_argument("contact", help="Contact name")
    wa_send.add_argument("message", help="Message text")

    wa_read = wa_sub.add_parser("read", help="Read messages")
    wa_read.add_argument("--contact", help="Contact name")
    wa_read.add_argument("--limit", type=int, default=20)

    wa_mon = wa_sub.add_parser("monitor", help="Background message monitor")
    wa_mon_sub = wa_mon.add_subparsers(dest="monitor_command", required=True)
    wa_mon_sub.add_parser("start", help="Start monitor daemon")
    wa_mon_sub.add_parser("stop", help="Stop monitor daemon")
    wa_mon_msgs = wa_mon_sub.add_parser("messages", help="Read captured messages")
    wa_mon_msgs.add_argument("--since", help="ISO timestamp filter")

    # ── API ──────────────────────────────────────────────────
    api_parser = subparsers.add_parser("api", help="API connectors")
    api_sub = api_parser.add_subparsers(dest="api_service", required=True)

    # Telegram
    tg_parser = api_sub.add_parser("telegram", help="Telegram Bot API")
    tg_sub = tg_parser.add_subparsers(dest="telegram_command", required=True)

    tg_cfg = tg_sub.add_parser("configure", help="Save bot token")
    tg_cfg.add_argument("token", help="Bot token")

    tg_me = tg_sub.add_parser("me", help="Get bot info")
    tg_me.add_argument("--token", help="Override token")

    tg_send = tg_sub.add_parser("send", help="Send message")
    tg_send.add_argument("chat_id", help="Chat ID")
    tg_send.add_argument("message", help="Message text")
    tg_send.add_argument("--token", help="Override token")

    tg_updates = tg_sub.add_parser("updates", help="Get updates")
    tg_updates.add_argument("--limit", type=int, default=20)
    tg_updates.add_argument("--token", help="Override token")

    # Email
    em_parser = api_sub.add_parser("email", help="Email SMTP/IMAP")
    em_sub = em_parser.add_subparsers(dest="email_command", required=True)

    em_cfg = em_sub.add_parser("configure", help="Configure email")
    em_cfg.add_argument("--smtp-host", dest="smtp_host", required=True)
    em_cfg.add_argument("--smtp-port", dest="smtp_port", type=int, required=True)
    em_cfg.add_argument("--imap-host", dest="imap_host", required=True)
    em_cfg.add_argument("--imap-port", dest="imap_port", type=int, required=True)
    em_cfg.add_argument("--user", required=True)
    em_cfg.add_argument("--password", required=True)

    em_send = em_sub.add_parser("send", help="Send email")
    em_send.add_argument("to", help="Recipient")
    em_send.add_argument("subject", help="Subject")
    em_send.add_argument("body", help="Body text")

    em_inbox = em_sub.add_parser("inbox", help="Read inbox")
    em_inbox.add_argument("--limit", type=int, default=20)
    em_inbox.add_argument("--unread", action="store_true", default=True)

    # Webhook
    wh_parser = api_sub.add_parser("webhook", help="HTTP webhook receiver")
    wh_sub = wh_parser.add_subparsers(dest="webhook_command", required=True)

    wh_start = wh_sub.add_parser("start", help="Start webhook server")
    wh_start.add_argument("--port", type=int, default=8765)

    wh_sub.add_parser("stop", help="Stop webhook server")

    wh_events = wh_sub.add_parser("events", help="List received events")
    wh_events.add_argument("--limit", type=int, default=50)

    # ── Audio ──────────────────────────────────────────────
    audio_parser = subparsers.add_parser("audio", help="Volume and mute control")
    audio_sub = audio_parser.add_subparsers(dest="audio_command", required=True)

    avol = audio_sub.add_parser("volume", help="Get or set volume (0-100)")
    avol.add_argument("level", type=int, nargs="?", help="Volume level 0-100")

    audio_sub.add_parser("mute", help="Mute audio")
    audio_sub.add_parser("unmute", help="Unmute audio")
    audio_sub.add_parser("toggle", help="Toggle mute")

    # ── App ────────────────────────────────────────────────
    app_parser = subparsers.add_parser("app", help="Application launcher")
    app_sub = app_parser.add_subparsers(dest="app_command", required=True)

    aopen = app_sub.add_parser("open", help="Open an application")
    aopen.add_argument("name", help="App name (chrome, spotify, notepad, etc.)")
    aopen.add_argument("target", nargs="?", help="URL, file, or path to open with the app")

    app_sub.add_parser("list", help="List available apps")

    # ── Workflow ───────────────────────────────────────────
    wf_parser = subparsers.add_parser("workflow", help="Predefined action sequences")
    wf_sub = wf_parser.add_subparsers(dest="workflow_command", required=True)

    wfrun = wf_sub.add_parser("run", help="Run a workflow")
    wfrun.add_argument("name", help="Workflow name")

    wf_sub.add_parser("list", help="List available workflows")

    return parser


def dispatch(args):
    """Dispatch to the appropriate module handler."""
    module = args.module

    if module == "screen":
        from pc_control.screen.capture import handle_command
        handle_command(args)

    elif module == "input":
        from pc_control.input.controller import handle_command
        handle_command(args)

    elif module == "windows":
        from pc_control.windows.manager import handle_command
        handle_command(args)

    elif module == "browser":
        from pc_control.browser.commands import handle_command
        handle_command(args)

    elif module == "system":
        from pc_control.system.monitor import handle_command
        handle_command(args)

    elif module == "clipboard":
        from pc_control.system.clipboard import handle_command
        handle_command(args)

    elif module == "ocr":
        from pc_control.ocr.windows_ocr import handle_command
        handle_command(args)

    elif module == "desktop":
        from pc_control.desktop.commands import handle_command
        handle_command(args)

    elif module == "vision":
        from pc_control.vision.commands import handle_command
        handle_command(args)

    elif module == "chat":
        from pc_control.chat.commands import handle_command
        handle_command(args)

    elif module == "api":
        from pc_control.api.commands import handle_command
        handle_command(args)

    elif module == "audio":
        from pc_control.audio.controller import handle_command
        handle_command(args)

    elif module == "app":
        from pc_control.app.launcher import handle_command
        handle_command(args)

    elif module == "workflow":
        from pc_control.workflow.engine import handle_command
        handle_command(args)

    else:
        print(f"Unknown module: {module}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        dispatch(args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        import json
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)
