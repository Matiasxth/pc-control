"""API connectors command dispatcher."""
import sys


def handle_command(args):
    service = args.api_service

    if service == "telegram":
        from pc_control.api import telegram
        cmd = args.telegram_command
        if cmd == "configure":
            telegram.configure(args.token)
        elif cmd == "me":
            telegram.get_me(token=getattr(args, "token", None))
        elif cmd == "send":
            telegram.send_message(args.chat_id, args.message, token=getattr(args, "token", None))
        elif cmd == "updates":
            telegram.get_updates(token=getattr(args, "token", None), limit=getattr(args, "limit", 20))
        else:
            print(f"Unknown telegram command: {cmd}", file=sys.stderr)
            sys.exit(1)

    elif service == "email":
        from pc_control.api import email_client
        cmd = args.email_command
        if cmd == "configure":
            email_client.configure(
                args.smtp_host, args.smtp_port,
                args.imap_host, args.imap_port,
                args.user, getattr(args, "password", ""),
            )
        elif cmd == "send":
            email_client.send_email(args.to, args.subject, args.body)
        elif cmd == "inbox":
            email_client.read_inbox(
                limit=getattr(args, "limit", 20),
                unread_only=getattr(args, "unread", True),
            )
        else:
            print(f"Unknown email command: {cmd}", file=sys.stderr)
            sys.exit(1)

    elif service == "webhook":
        from pc_control.api import webhooks
        cmd = args.webhook_command
        if cmd == "start":
            webhooks.start_webhook(port=getattr(args, "port", 8765))
        elif cmd == "stop":
            webhooks.stop_webhook()
        elif cmd == "events":
            webhooks.list_events(limit=getattr(args, "limit", 50))
        else:
            print(f"Unknown webhook command: {cmd}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Unknown API service: {service}", file=sys.stderr)
        sys.exit(1)
