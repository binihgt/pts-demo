from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
from bot.context import get_bot_app
from app.models.user import User
from app.models.sale import Sale
from app.models.payment import Payment
from app.services.sales_service import SalesService
from app.utils.formatting import format_money, to_eat_datetime, format_eat_datetime
from bot.auth import telegram_auth_required, get_current_user


def ensure_dt(dt):
    """Ensure datetime is timezone-aware in UTC for safe comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@telegram_auth_required()
async def mysales_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show personal sales recorded today."""
    telegram_user = update.effective_user
    if not telegram_user or not update.message:
        return

    user_id = context.user_data["db_user_id"]
    user_name = context.user_data["db_user_name"]

    now = datetime.now(timezone.utc)
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    eat_today_str = format_eat_datetime(now, "%b %d, %Y")

    with get_bot_app().app_context():
        all_emp_sales = Sale.query.filter_by(employee_id=user_id).order_by(Sale.created_at.desc()).all()
        today_sales = [s for s in all_emp_sales if ensure_dt(s.created_at) >= start_of_today]

        if not today_sales:
            await update.message.reply_text(
                f"📊 *My Sales Today ({eat_today_str} EAT)*\n\n"
                f"👤 Employee: *{user_name}*\n"
                "You haven't recorded any sales yet today.\n\n"
                "💡 Use `/sale` to record your first sale!",
                parse_mode="Markdown"
            )
            return

        total_rev = sum(s.total for s in today_sales)
        total_paid = sum(s.total_paid for s in today_sales)
        total_unpaid = sum(s.balance for s in today_sales)

        msg = (
            f"📊 *My Sales Today ({eat_today_str} EAT)*\n"
            f"👤 Employee: *{user_name}*\n"
            f"📈 Transactions: *{len(today_sales)}*\n"
            f"💰 Total Sold: *{format_money(total_rev)}*\n"
            f"💵 Collected: *{format_money(total_paid)}*\n"
            f"⏳ Unpaid Balance: *{format_money(total_unpaid)}*\n\n"
            "📋 *Recent Invoices Today:*\n"
        )

        for s in today_sales[:8]:
            status_icon = "🟢" if s.payment_status == "paid" else ("🟡" if s.payment_status == "partial" else "🔴")
            msg += (
                f"• `#{s.id}` {status_icon} *{s.item}* (x{s.quantity})\n"
                f"  Total: {format_money(s.total)} | Bal: {format_money(s.balance)}\n"
            )

        if len(today_sales) > 8:
            msg += f"\n_...and {len(today_sales) - 8} more transactions._"

        await update.message.reply_text(msg, parse_mode="Markdown")


@telegram_auth_required(allowed_roles=(User.ROLE_CEO, User.ROLE_MANAGER))
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """CEO / Manager: Show company-wide sales and collections today."""
    if not update.message:
        return

    now = datetime.now(timezone.utc)
    eat_today_str = format_eat_datetime(now, "%b %d, %Y")

    with get_bot_app().app_context():
        # Single source of truth totals matching Dashboard and Excel Summary
        totals = SalesService.get_company_totals()

        msg = (
            f"🏢 *Company Daily Summary - {eat_today_str} (EAT)*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 *Today's sales:* *{format_money(totals['today_sales_total'])}* ({totals['today_sales_count']} transactions)\n"
            f"💳 *Collected today (all invoices):* *{format_money(totals['today_collected_total'])}*\n"
            f"⚠️ *Total outstanding (all invoices):* *{format_money(totals['total_outstanding'])}*\n\n"
            "🏦 *Collections Breakdown (Today):*\n"
            f"• Telebirr: {format_money(totals['today_telebirr'])}\n"
            f"• Bank Transfer / CBE: {format_money(totals['today_bank'])}\n"
            f"• Cash: {format_money(totals['today_cash'])}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 _Send /report to download the detailed Excel sheet._"
        )

        await update.message.reply_text(msg, parse_mode="Markdown")
