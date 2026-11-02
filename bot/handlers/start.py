from telegram import Update
from telegram.ext import ContextTypes
from bot.context import get_bot_app
from app.extensions import db
from app.models.user import User
from app.models.audit import AuditLog


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with link code validation and account switching."""
    telegram_user = update.effective_user
    if not telegram_user or not update.message:
        return

    # Check if a link code was passed as an argument: /start <CODE>
    args = context.args
    link_code = args[0].strip().upper() if args else None

    with get_bot_app().app_context():
        # 1. If a link code is provided, attempt to verify and pair (even if switching accounts)
        if link_code:
            target_user = User.query.filter_by(telegram_link_code=link_code, is_active=True).first()
            if not target_user:
                await update.message.reply_text(
                    "❌ *Invalid or Expired Link Code*\n\n"
                    "The code you entered does not match any pending registration. "
                    "Please ask your CEO to generate a fresh link code from the dashboard.",
                    parse_mode="Markdown"
                )
                return

            # Check if this Telegram account is already linked to another user
            currently_linked = User.query.filter_by(telegram_id=telegram_user.id, is_active=True).first()
            if currently_linked and currently_linked.id != target_user.id:
                # Do NOT consume the code! Guide the user to /logout first
                await update.message.reply_text(
                    f"⛔ *Account Already Linked*\n\n"
                    f"This Telegram account is already linked to another user ({currently_linked.name}).\n\n"
                    "💡 *To switch to this account:*\n"
                    "1. Send `/logout` to unlink your current account.\n"
                    f"2. Then send `/start {link_code}` to log in with your CEO code.",
                    parse_mode="Markdown"
                )
                return

            # Wrap pairing in a safe transaction with rollback
            try:
                target_user.telegram_id = telegram_user.id
                target_user.clear_telegram_link_code()

                AuditLog.log(
                    action="TELEGRAM_LINKED",
                    user_id=target_user.id,
                    details=f"User '{target_user.username}' linked Telegram ID {telegram_user.id} (@{telegram_user.username or 'no_handle'})."
                )
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                import logging
                logging.getLogger("pts_bot").exception("Database error while linking Telegram user: %s", e)
                await update.message.reply_text(
                    "⚠️ An error occurred while linking your account. Please try again or contact your administrator."
                )
                return

            context.user_data.clear()

            title_msg = (
                f"🎉 *Account Linked Successfully!*\n\n"
                f"Hello, *{target_user.name}*!\n"
                f"Your Telegram account has been linked with role: *{target_user.role.title()}*."
            )

            success_msg = (
                f"{title_msg}\n\n"
                "🚀 *You can now use the following commands:*\n"
                "• /sale - Record a sale\n"
                "• /pay - Record a payment\n"
                "• /mysales - See your sales today\n"
            )
            if target_user.can_view_all_sales:
                success_msg += (
                    "• /today - Today's company total\n"
                    "• /report - Receive Excel report\n"
                )
            success_msg += "• /logout - Log out or switch to another user\n"
            await update.message.reply_text(success_msg, parse_mode="Markdown")
            return

        # 2. Check if user is already linked (without args)
        existing_user = User.query.filter_by(telegram_id=telegram_user.id, is_active=True).first()
        if existing_user:
            commands_help = (
                f"👋 *Welcome back, {existing_user.name}!*\n"
                f"Role: *{existing_user.role.title()}*\n\n"
                "📌 *Available Commands:*\n"
                "• /sale - Guided sale recording\n"
                "• /pay - Record a payment against an invoice\n"
                "• /mysales - View your personal sales today\n"
            )
            if existing_user.can_view_all_sales:
                commands_help += (
                    "• /today - Company-wide sales summary for today\n"
                    "• /report - Download today's Excel report in chat\n"
                )
            commands_help += (
                "• /logout - Log out from this account\n"
                "• /help - Command instructions\n"
            )
            await update.message.reply_text(commands_help, parse_mode="Markdown")
            return

        # 3. No link code provided and account is not yet registered
        unregistered_msg = (
            "👋 *Welcome to PTS Demo Business Bot!*\n\n"
            "This bot is private and restricted to authorized employees.\n\n"
            "🔑 *To link your account:*\n"
            "1. Ask your CEO to generate your one-time link code in the dashboard.\n"
            "2. Send: `/start <CODE>`\n\n"
            "Example: `/start A1B2C3D4`"
        )
        await update.message.reply_text(unregistered_msg, parse_mode="Markdown")


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /logout command to unlink Telegram account."""
    telegram_user = update.effective_user
    if not telegram_user or not update.message:
        return

    with get_bot_app().app_context():
        user = User.query.filter_by(telegram_id=telegram_user.id, is_active=True).first()
        if not user:
            await update.message.reply_text(
                "ℹ️ *Not Logged In*\n\n"
                "Your Telegram account is not currently linked to any user in PTS Demo.\n\n"
                "💡 To log in, ask your CEO for a link code and send:\n`/start <CODE>`",
                parse_mode="Markdown"
            )
            return

        user_name = user.name
        user_role = user.role.title()

        try:
            user.telegram_id = None
            AuditLog.log(
                action="TELEGRAM_UNLINKED",
                user_id=user.id,
                details=f"User '{user.username}' logged out and unlinked Telegram ID {telegram_user.id} (@{telegram_user.username or 'no_handle'})."
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            import logging
            logging.getLogger("pts_bot").exception("Error during logout: %s", e)
            await update.message.reply_text("⚠️ An error occurred during logout. Please try again.")
            return

        context.user_data.clear()

        logout_msg = (
            f"👋 *Logged Out Successfully*\n\n"
            f"You have logged out of *{user_name}* ({user_role}).\n\n"
            "🔑 *To log in again or switch accounts:*\n"
            "Ask your CEO for a link code from the dashboard and send:\n"
            "`/start <CODE>`"
        )
        await update.message.reply_text(logout_msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available commands according to role."""
    telegram_user = update.effective_user
    if not telegram_user or not update.message:
        return

    with get_bot_app().app_context():
        user = User.query.filter_by(telegram_id=telegram_user.id, is_active=True).first()
        if not user:
            await update.message.reply_text(
                "⛔ *Access Denied*\nUse `/start <CODE>` to link your account first.",
                parse_mode="Markdown"
            )
            return

        msg = (
            f"📋 *PTS Demo Bot - Command Reference*\n"
            f"User: *{user.name}* ({user.role.title()})\n\n"
            "• `/sale` - Start a guided prompt to record a sale\n"
            "• `/pay` - Record a payment towards an outstanding invoice\n"
            "• `/mysales` - Show your personal sales recorded today\n"
        )
        if user.can_view_all_sales:
            msg += (
                "• `/today` - Executive summary of company sales today\n"
                "• `/report` - Receive an Excel report directly in this chat\n"
            )
        msg += (
            "• `/logout` - Log out or unlink this account\n"
            "• `/cancel` - Cancel any active multi-step conversation\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
