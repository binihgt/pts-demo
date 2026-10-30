from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from bot.context import get_bot_app
from app.models.user import User


def get_current_user(telegram_id: int) -> User | None:
    """Lookup user by Telegram ID within application context."""
    bot_app = get_bot_app()
    with bot_app.app_context():
        return User.query.filter_by(telegram_id=telegram_id, is_active=True).first()


def telegram_auth_required(allowed_roles: tuple[str, ...] | None = None):
    """
    Decorator for bot command handlers to enforce pre-registration and role permissions.
    If the Telegram account is not linked, politely refuses access.
    """
    def decorator(handler_func):
        @wraps(handler_func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            telegram_user = update.effective_user
            if not telegram_user:
                return

            user = get_current_user(telegram_user.id)
            if not user:
                refusal_message = (
                    "⛔ *Access Denied: Unregistered Account*\n\n"
                    "Your Telegram account is not authorized to access PTS Demo.\n\n"
                    "💡 *How to link your account:*\n"
                    "1. Ask your CEO to generate a link code in the dashboard.\n"
                    "2. Send: `/start <YOUR_CODE>` to link your account.\n\n"
                    "Example: `/start A1B2C3D4`"
                )
                if update.message:
                    await update.message.reply_text(refusal_message, parse_mode="Markdown")
                elif update.callback_query:
                    await update.callback_query.answer("Account not registered.", show_alert=True)
                return

            if allowed_roles and user.role not in allowed_roles:
                roles_str = " or ".join(r.title() for r in allowed_roles)
                denied_message = (
                    f"🔒 *Permission Denied*\n\n"
                    f"This command is restricted to *{roles_str}* only.\n"
                    f"Your current role: *{user.role.title()}*."
                )
                if update.message:
                    await update.message.reply_text(denied_message, parse_mode="Markdown")
                elif update.callback_query:
                    await update.callback_query.answer("Permission denied.", show_alert=True)
                return

            # Pass the authenticated User model instance to context.user_data
            context.user_data["db_user_id"] = user.id
            context.user_data["db_user_role"] = user.role
            context.user_data["db_user_name"] = user.name

            return await handler_func(update, context, *args, **kwargs)
        return wrapper
    return decorator
