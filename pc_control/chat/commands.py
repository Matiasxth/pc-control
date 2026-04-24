"""Chat module command dispatcher."""
import sys


def handle_command(args):
    if args.chat_service != "whatsapp":
        print(f"Unknown chat service: {args.chat_service}", file=sys.stderr)
        sys.exit(1)

    cmd = args.whatsapp_command
    from pc_control.chat import whatsapp

    if cmd == "start":
        whatsapp.start_whatsapp()
    elif cmd == "status":
        whatsapp.status()
    elif cmd == "send":
        whatsapp.send_message(args.contact, args.message)
    elif cmd == "read":
        whatsapp.read_messages(
            contact=getattr(args, "contact", None),
            limit=getattr(args, "limit", 20),
        )
    elif cmd == "monitor":
        mcmd = args.monitor_command
        if mcmd == "start":
            whatsapp.monitor_start()
        elif mcmd == "stop":
            whatsapp.monitor_stop()
        elif mcmd == "messages":
            whatsapp.monitor_messages(since=getattr(args, "since", None))
        else:
            print(f"Unknown monitor command: {mcmd}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown whatsapp command: {cmd}", file=sys.stderr)
        sys.exit(1)
