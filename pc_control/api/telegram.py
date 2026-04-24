"""Telegram Bot API integration."""
import json
import io
import sys
from pathlib import Path

import requests

from pc_control.config import PROJECT_ROOT

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API_CONFIG = PROJECT_ROOT / ".api"
API_CONFIG.mkdir(exist_ok=True)
TG_CONFIG = API_CONFIG / "telegram.json"
TG_API = "https://api.telegram.org/bot{token}"


def _output(data: dict):
    print(json.dumps(data, ensure_ascii=False))


def _get_token(token=None):
    if token:
        return token
    if TG_CONFIG.exists():
        cfg = json.loads(TG_CONFIG.read_text())
        return cfg.get("token")
    import os
    return os.environ.get("TELEGRAM_BOT_TOKEN")


def configure(token: str):
    """Save Telegram bot token."""
    cfg = {"token": token}
    TG_CONFIG.write_text(json.dumps(cfg, indent=2))
    # Verify token
    try:
        resp = requests.get(f"{TG_API.format(token=token)}/getMe", timeout=10)
        data = resp.json()
        if data.get("ok"):
            bot = data["result"]
            cfg["bot_username"] = bot.get("username")
            cfg["bot_name"] = bot.get("first_name")
            TG_CONFIG.write_text(json.dumps(cfg, indent=2))
            _output({"status": "ok", "action": "telegram_configure", "bot": bot.get("username"),
                      "name": bot.get("first_name")})
        else:
            _output({"status": "error", "error": f"Invalid token: {data.get('description')}"})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def get_me(token=None):
    """Get bot info."""
    token = _get_token(token)
    if not token:
        _output({"status": "error", "error": "No token. Run 'api telegram configure <token>'"})
        return
    try:
        resp = requests.get(f"{TG_API.format(token=token)}/getMe", timeout=10)
        data = resp.json()
        _output({"status": "ok", "action": "telegram_me", "bot": data.get("result", {})})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def send_message(chat_id: str, text: str, token=None):
    """Send a message to a chat."""
    token = _get_token(token)
    if not token:
        _output({"status": "error", "error": "No token configured"})
        return
    try:
        resp = requests.post(
            f"{TG_API.format(token=token)}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            msg = data["result"]
            _output({"status": "ok", "action": "telegram_send", "chat_id": chat_id,
                      "message_id": msg.get("message_id")})
        else:
            _output({"status": "error", "error": data.get("description", "Send failed")})
    except Exception as e:
        _output({"status": "error", "error": str(e)})


def get_updates(token=None, limit=20):
    """Get recent updates (messages sent to the bot)."""
    token = _get_token(token)
    if not token:
        _output({"status": "error", "error": "No token configured"})
        return
    try:
        # Get last offset
        last_offset = None
        if TG_CONFIG.exists():
            cfg = json.loads(TG_CONFIG.read_text())
            last_offset = cfg.get("last_update_id")

        params = {"limit": limit, "timeout": 5}
        if last_offset:
            params["offset"] = last_offset + 1

        resp = requests.get(f"{TG_API.format(token=token)}/getUpdates", params=params, timeout=15)
        data = resp.json()

        if data.get("ok"):
            updates = data["result"]
            # Save last offset
            if updates:
                cfg = json.loads(TG_CONFIG.read_text()) if TG_CONFIG.exists() else {}
                cfg["last_update_id"] = updates[-1]["update_id"]
                TG_CONFIG.write_text(json.dumps(cfg, indent=2))

            messages = []
            for u in updates:
                msg = u.get("message", {})
                messages.append({
                    "update_id": u["update_id"],
                    "from": msg.get("from", {}).get("first_name", ""),
                    "chat_id": msg.get("chat", {}).get("id"),
                    "text": msg.get("text", ""),
                    "date": msg.get("date"),
                })

            _output({"status": "ok", "action": "telegram_updates", "count": len(messages),
                      "messages": messages})
        else:
            _output({"status": "error", "error": data.get("description", "Failed")})
    except Exception as e:
        _output({"status": "error", "error": str(e)})
