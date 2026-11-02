import logging
from flask import Blueprint, request, jsonify, current_app
from app.extensions import csrf

import re

webhook_bp = Blueprint("webhook", __name__)
logger = logging.getLogger("pts_bot.webhook_route")


def sanitize_telegram_secret(secret: str) -> str:
    """Ensure secret matches Telegram's allowed character set [A-Za-z0-9_-]."""
    if not secret:
        return ""
    return re.sub(r"[^A-Za-z0-9_-]", "_", secret)


@webhook_bp.route("/webhook/telegram", methods=["POST"])
@csrf.exempt
def telegram_webhook():
    """
    Receives incoming updates pushed by Telegram Bot API via webhook.
    Enforces secret token verification via X-Telegram-Bot-Api-Secret-Token.
    """
    # 1. Enforce Telegram's secret-token header verification
    expected_secret = current_app.config.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if expected_secret:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "").strip()
        clean_expected = sanitize_telegram_secret(expected_secret)
        if header_secret != expected_secret and header_secret != clean_expected:
            logger.warning("Rejected Telegram webhook request: secret token mismatch.")
            return jsonify({"status": "error", "message": "Invalid webhook secret"}), 403

    # 2. Extract and validate JSON payload
    payload = request.get_json(force=True, silent=True)
    if not payload or not isinstance(payload, dict):
        logger.warning("Rejected Telegram webhook request: missing or invalid JSON.")
        return jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

    # 3. Check configured token
    token = current_app.config.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token == "your_telegram_bot_token_here":
        return jsonify({"status": "ignored", "message": "Bot token not configured"}), 200

    # 4. Dispatch update to Telegram Application runner
    try:
        from bot.context import set_bot_app
        set_bot_app(current_app._get_current_object())
        from bot.webhook_dispatcher import dispatch_telegram_update
        dispatch_telegram_update(token, payload)
    except Exception as exc:
        logger.error(f"Error processing Telegram webhook update: {exc}", exc_info=True)
        import sys, traceback
        traceback.print_exc(file=sys.stderr)
        # Always return 200 to acknowledge receipt and prevent Telegram retry freeze loops
        return jsonify({"status": "ok", "error": str(exc)}), 200

    return jsonify({"status": "ok"}), 200
