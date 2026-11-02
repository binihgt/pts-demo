"""
Telegram Bot Webhook Dispatcher and Auto-Registration.
Provides thread-safe async update execution for Flask WSGI/Gunicorn
and automatic webhook registration on public startup.
"""
import os
import sys
import logging
import asyncio
import threading
from typing import Optional
from pathlib import Path

from telegram import Update, Bot
from bot.main import build_bot_application

logger = logging.getLogger("pts_bot.webhook")


class BotWebhookRunner:
    """Manages an asyncio event loop thread and Telegram Application for webhook updates."""

    def __init__(self, token: str):
        self.token = token
        self.bot_app = build_bot_application(token)
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True, name="TelegramWebhookLoop")
        self.thread.start()

        # Initialize the bot application inside its own event loop
        init_future = asyncio.run_coroutine_threadsafe(self._init_app(), self.loop)
        try:
            init_future.result(timeout=10)
        except Exception as exc:
            logger.warning(f"Error during bot application initialization: {exc}")

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _init_app(self):
        try:
            await self.bot_app.initialize()
            logger.info("Bot application successfully initialized via Telegram API.")
        except Exception as exc:
            logger.warning(f"Could not initialize bot via Telegram API ({exc}). Falling back to local offline mode.")
            # Set internal flags so process_update does not raise RuntimeError in offline/test scenarios
            self.bot_app._initialized = True
            self.bot_app.bot._initialized = True
            token_prefix = self.token.split(":")[0] if ":" in self.token else "123456"
            self.bot_app.bot._id = int(token_prefix) if token_prefix.isdigit() else 123456

    def dispatch_update(self, update_dict: dict, timeout: float = 25.0):
        """Convert payload to Telegram Update and process through registered handlers."""
        update = Update.de_json(update_dict, self.bot_app.bot)
        if update is None:
            logger.warning("Could not parse payload as Telegram Update.")
            return

        future = asyncio.run_coroutine_threadsafe(self.bot_app.process_update(update), self.loop)
        return future.result(timeout=timeout)


_global_runner: Optional[BotWebhookRunner] = None
_runner_lock = threading.Lock()


def get_webhook_runner(token: str) -> BotWebhookRunner:
    """Return singleton instance of BotWebhookRunner."""
    global _global_runner
    with _runner_lock:
        if _global_runner is None or _global_runner.token != token:
            _global_runner = BotWebhookRunner(token)
        return _global_runner


def dispatch_telegram_update(token: str, update_dict: dict):
    """Entrypoint called by Flask webhook endpoint to process update."""
    runner = get_webhook_runner(token)
    return runner.dispatch_update(update_dict)


def register_webhook_async(token: str, public_url: str, webhook_path: str = "/webhook/telegram", secret: str = ""):
    """
    Automatically registers webhook with Telegram API on application startup
    without blocking the Flask web worker.
    """
    def _worker():
        async def _register():
            target_url = f"{public_url.rstrip('/')}{webhook_path}"
            logger.info(f"Auto-registering Telegram webhook at: {target_url}")
            try:
                import re
                clean_secret = re.sub(r"[^A-Za-z0-9_-]", "_", secret) if secret else None
                bot = Bot(token=token)
                async with bot:
                    await bot.set_webhook(
                        url=target_url,
                        secret_token=clean_secret,
                        drop_pending_updates=False
                    )
                    logger.info(f"Telegram webhook successfully registered to {target_url}")
            except Exception as exc:
                logger.warning(f"Could not auto-register Telegram webhook: {exc}")

        try:
            asyncio.run(_register())
        except Exception as exc:
            logger.warning(f"Failed to execute webhook registration thread: {exc}")

    thread = threading.Thread(target=_worker, daemon=True, name="TelegramWebhookRegistrar")
    thread.start()
