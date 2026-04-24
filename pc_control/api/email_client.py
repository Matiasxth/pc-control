"""Email client — send via SMTP, read via IMAP."""

import email
import imaplib
import io
import json
import smtplib
import sys
from email.mime.text import MIMEText

from pc_control.config import PROJECT_ROOT

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API_CONFIG = PROJECT_ROOT / ".api"
API_CONFIG.mkdir(exist_ok=True)
EMAIL_CONFIG = API_CONFIG / "email.json"


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _load_config():
    if EMAIL_CONFIG.exists():
        return json.loads(EMAIL_CONFIG.read_text())
    return None


def configure(smtp_host, smtp_port, imap_host, imap_port, username, password, use_tls=True):
    """Save email configuration."""
    cfg = {
        "smtp_host": smtp_host,
        "smtp_port": int(smtp_port),
        "imap_host": imap_host,
        "imap_port": int(imap_port),
        "username": username,
        "password": password,
        "use_tls": use_tls,
    }
    EMAIL_CONFIG.write_text(json.dumps(cfg, indent=2))
    _output(
        {
            "status": "ok",
            "action": "email_configure",
            "username": username,
            "warning": "Credentials stored in plaintext at " + str(EMAIL_CONFIG),
        }
    )


def send_email(to: str, subject: str, body: str):
    """Send an email."""
    cfg = _load_config()
    if not cfg:
        _output({"status": "error", "error": "Not configured. Run 'api email configure'"})
        return

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = cfg["username"]
        msg["To"] = to
        msg["Subject"] = subject

        if cfg.get("use_tls", True):
            server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"])
            server.starttls()
        else:
            server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"])

        server.login(cfg["username"], cfg["password"])
        server.send_message(msg)
        server.quit()

        _output({"status": "ok", "action": "email_send", "to": to, "subject": subject})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def read_inbox(limit=20, unread_only=True):
    """Read emails from inbox."""
    cfg = _load_config()
    if not cfg:
        _output({"status": "error", "error": "Not configured"})
        return

    try:
        if cfg.get("use_tls", True):
            mail = imaplib.IMAP4_SSL(cfg["imap_host"], cfg.get("imap_port", 993))
        else:
            mail = imaplib.IMAP4(cfg["imap_host"], cfg.get("imap_port", 143))

        mail.login(cfg["username"], cfg["password"])
        mail.select("INBOX")

        criteria = "UNSEEN" if unread_only else "ALL"
        _, data = mail.search(None, criteria)
        ids = data[0].split()

        # Get last N messages
        ids = ids[-limit:]
        messages = []

        for mid in reversed(ids):
            _, msg_data = mail.fetch(mid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            body_preview = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body_preview = part.get_payload(decode=True).decode(errors="replace")[:200]
                        break
            else:
                body_preview = msg.get_payload(decode=True).decode(errors="replace")[:200]

            messages.append(
                {
                    "id": mid.decode(),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "subject": msg.get("Subject", ""),
                    "date": msg.get("Date", ""),
                    "body_preview": body_preview.strip(),
                }
            )

        mail.logout()
        _output(
            {"status": "ok", "action": "email_inbox", "count": len(messages), "messages": messages}
        )
    except Exception as e:
        _output({"status": "error", "error": str(e)})
