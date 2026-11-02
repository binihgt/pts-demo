#!/usr/bin/env python3
"""
Telegram Webhook Setup and Diagnosis Utility for PTS Demo.
Use this script to:
1. Inspect bot connection and pending updates
2. Register Telegram webhook with your Render URL
3. Delete webhook if you want to switch to local polling (python bot/main.py)
"""
import os
import sys
import argparse
import urllib.request
import urllib.parse
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="PTS Demo Telegram Webhook Manager")
    parser.add_argument("--url", default="https://pts-demo.onrender.com", help="Public HTTPS URL of your Render service")
    parser.add_argument("--secret", default=None, help="Telegram Webhook Secret Token (optional)")
    parser.add_argument("--delete", action="store_true", help="Delete webhook and switch to polling mode")
    parser.add_argument("--token", default=None, help="Override bot token (defaults to .env TELEGRAM_BOT_TOKEN)")
    args = parser.parse_args()

    token = args.token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "your_telegram_bot_token_here":
        print("❌ Error: TELEGRAM_BOT_TOKEN is missing. Please set it in .env or pass --token <TOKEN>")
        sys.exit(1)

    base_api = f"https://api.telegram.org/bot{token}"

    # 1. Test Bot Authentication
    try:
        req = urllib.request.urlopen(f"{base_api}/getMe", timeout=10)
        bot_info = json.loads(req.read().decode())["result"]
        print(f"🤖 Bot Name: {bot_info.get('first_name')} (@{bot_info.get('username')})")
        print(f"🆔 Bot ID:   {bot_info.get('id')}")
    except Exception as e:
        print(f"❌ Failed to reach Telegram API: {e}")
        sys.exit(1)

    # 2. If --delete, remove webhook
    if args.delete:
        try:
            req = urllib.request.urlopen(f"{base_api}/deleteWebhook?drop_pending_updates=False", timeout=10)
            res = json.loads(req.read().decode())
            print(f"✅ Webhook deleted: {res.get('description', 'OK')}")
            print("🚀 You can now run local polling with: python bot/main.py")
        except Exception as e:
            print(f"❌ Failed to delete webhook: {e}")
        return

    # 3. Register Webhook
    target_webhook = f"{args.url.rstrip('/')}/webhook/telegram"
    params = {"url": target_webhook}
    if args.secret:
        params["secret_token"] = args.secret

    encoded = urllib.parse.urlencode(params).encode("utf-8")
    try:
        req = urllib.request.Request(f"{base_api}/setWebhook", data=encoded, method="POST")
        res = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        print(f"📡 Webhook Registration: {res.get('description', 'OK')}")
        print(f"🔗 Target Webhook URL:    {target_webhook}")
    except Exception as e:
        print(f"❌ Error registering webhook: {e}")

    # 4. Check Current Webhook Status
    try:
        req = urllib.request.urlopen(f"{base_api}/getWebhookInfo", timeout=10)
        info = json.loads(req.read().decode())["result"]
        print("-" * 55)
        print(f"📍 Active Webhook URL:      {info.get('url') or '(None - Polling Mode)'}")
        print(f"📦 Pending Messages:        {info.get('pending_update_count', 0)}")
        if info.get("last_error_message"):
            print(f"⚠️ Last Delivery Error:     {info.get('last_error_message')}")
            print(f"⏱️ Last Error Timestamp:   {info.get('last_error_date')}")
        else:
            print("✨ Webhook Status:          Healthy & Ready")
        print("-" * 55)
    except Exception as e:
        print(f"⚠️ Could not query webhook info: {e}")


if __name__ == "__main__":
    main()
