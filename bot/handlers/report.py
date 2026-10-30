from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
from bot.context import get_bot_app
from app.extensions import db
from app.models.user import User
from app.models.audit import AuditLog
from app.services.report_service import ReportService
from bot.auth import telegram_auth_required


@telegram_auth_required(allowed_roles=(User.ROLE_CEO, User.ROLE_MANAGER))
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """CEO / Manager: Generate and send Excel report in chat."""
    if not update.message:
        return

    user_id = context.user_data["db_user_id"]
    user_name = context.user_data["db_user_name"]

    status_msg = await update.message.reply_text("⏳ Generating Excel report, please wait...")

    with get_bot_app().app_context():
        try:
            buffer, filename = ReportService.generate_excel_report()

            AuditLog.log(
                action="REPORT_DOWNLOADED_TELEGRAM",
                user_id=user_id,
                details=f"User '{user_name}' downloaded Excel report via Telegram bot."
            )
            db.session.commit()

            caption = (
                f"📊 *PTS Demo Business Report*\n"
                f"Generated for: *{user_name}*\n"
                f"Date: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`"
            )

            await update.message.reply_document(
                document=buffer,
                filename=filename,
                caption=caption,
                parse_mode="Markdown"
            )
            await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ Failed to generate report: {str(e)}")
