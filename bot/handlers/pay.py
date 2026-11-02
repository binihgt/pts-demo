from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from app.utils.formatting import format_money
from bot.context import get_bot_app
from app.models.sale import Sale
from app.models.payment import Payment
from app.services.sales_service import SalesService
from bot.auth import get_current_user

SALE_ID, AMOUNT, METHOD = range(3)


async def pay_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiate guided /pay payment recording."""
    telegram_user = update.effective_user
    if not telegram_user or not update.message:
        return ConversationHandler.END

    user = get_current_user(telegram_user.id)
    if not user:
        await update.message.reply_text("⛔ Access denied. Use `/start <CODE>`.", parse_mode="Markdown")
        return ConversationHandler.END

    context.user_data["db_user_id"] = user.id
    context.user_data["db_user_role"] = user.role

    # Check if sale_id was passed directly: /pay 12
    args = context.args
    if args and args[0].strip().isdigit():
        sale_id = int(args[0].strip())
        return await handle_sale_lookup(sale_id, update, context)

    # If no argument passed, query recent unpaid invoices to guide the user
    with get_bot_app().app_context():
        if user.role == "employee":
            recent_sales = Sale.query.filter_by(employee_id=user.id).order_by(Sale.id.desc()).limit(20).all()
        else:
            recent_sales = Sale.query.order_by(Sale.id.desc()).limit(20).all()

        unpaid_sales = [s for s in recent_sales if s.balance > 0][:5]

        if unpaid_sales:
            items_text = "\n".join(
                [f"• *Invoice #{s.id}:* {s.item} — Balance: {format_money(s.balance)}" for s in unpaid_sales]
            )
            prompt = (
                "💳 *Record Payment (Step 1/3)*\n\n"
                "Which invoice number would you like to pay?\n\n"
                f"*Recent Unpaid Invoices:*\n{items_text}\n\n"
                "Please enter the *Invoice ID / Sale #* (e.g. `12`):\n"
                "_(Send /cancel to abort)_"
            )
        else:
            prompt = (
                "💳 *Record Payment (Step 1/3)*\n\n"
                "Which invoice number would you like to pay?\n\n"
                "_(You currently have no pending unpaid invoices)_\n\n"
                "Please enter the *Invoice ID / Sale #* (e.g. `12`):\n"
                "_(Send /cancel to abort)_"
            )

        await update.message.reply_text(prompt, parse_mode="Markdown")
        return SALE_ID


async def pay_sale_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process entered sale ID."""
    text = update.message.text.strip().lstrip("#")
    if not text.isdigit():
        await update.message.reply_text("⚠️ Please enter a numeric Invoice ID (e.g. `15`):")
        return SALE_ID

    sale_id = int(text)
    return await handle_sale_lookup(sale_id, update, context)


async def handle_sale_lookup(sale_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate sale existence, ownership, and remaining balance."""
    user_id = context.user_data.get("db_user_id")
    user_role = context.user_data.get("db_user_role")

    with get_bot_app().app_context():
        sale = Sale.query.get(sale_id)
        if not sale:
            msg = f"❌ Invoice `#{sale_id}` was not found. Please double check the ID."
            if update.message:
                await update.message.reply_text(msg, parse_mode="Markdown")
            return ConversationHandler.END

        # Employee check: cannot collect for another employee's sale
        if user_role == "employee" and sale.employee_id != user_id:
            msg = "⛔ You are only authorized to record payments for your own sales."
            if update.message:
                await update.message.reply_text(msg)
            return ConversationHandler.END

        if sale.balance <= 0:
            msg = (
                f"✅ *Invoice #{sale.id} is already fully paid!*\n"
                f"• Item: {sale.item}\n"
                f"• Total: {format_money(sale.total)}\n"
                f"• Paid: {format_money(sale.total_paid)}\n"
                f"• Remaining balance: {format_money(0.0)}"
            )
            if update.message:
                await update.message.reply_text(msg, parse_mode="Markdown")
            return ConversationHandler.END

        context.user_data["pay_sale_id"] = sale.id
        context.user_data["pay_sale_balance"] = sale.balance
        context.user_data["pay_sale_item"] = sale.item

        prompt = (
            f"🧾 *Invoice #{sale.id} Found:*\n"
            f"• *Item:* {sale.item}\n"
            f"• *Total Amount:* {format_money(sale.total)}\n"
            f"• *Already Paid:* {format_money(sale.total_paid)}\n"
            f"• *Remaining Balance:* *{format_money(sale.balance)}*\n\n"
            "💰 *Step 2/3: Enter the payment amount in ETB:*\n"
            f"_(Maximum: {format_money(sale.balance)})_"
        )
        if update.message:
            await update.message.reply_text(prompt, parse_mode="Markdown")
        return AMOUNT


async def pay_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate payment amount and show payment method buttons."""
    text = update.message.text.strip().replace(",", "")
    balance = context.user_data.get("pay_sale_balance", 0.0)

    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError()
        if amount > balance:
            await update.message.reply_text(
                f"⚠️ Payment amount ({format_money(amount)}) cannot exceed the remaining balance ({format_money(balance)}).\n"
                "Please enter a valid amount:"
            )
            return AMOUNT
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a positive number for the payment amount:")
        return AMOUNT

    context.user_data["pay_amount"] = amount

    keyboard = [
        [
            InlineKeyboardButton("📱 Telebirr", callback_data="pay_method_telebirr"),
            InlineKeyboardButton("🏦 Bank Transfer / CBE", callback_data="pay_method_bank"),
        ],
        [
            InlineKeyboardButton("💵 Cash", callback_data="pay_method_cash"),
            InlineKeyboardButton("❌ Cancel", callback_data="pay_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Amount: *{format_money(amount)}*\n\n"
        "💳 *Step 3/3: Select the payment method:*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return METHOD


async def pay_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Record payment in database and show final receipt."""
    query = update.callback_query
    await query.answer()

    if query.data == "pay_cancel":
        await query.edit_message_text("❌ Payment cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

    method_map = {
        "pay_method_telebirr": Payment.METHOD_TELEBIRR,
        "pay_method_bank": Payment.METHOD_BANK,
        "pay_method_cash": Payment.METHOD_CASH,
    }
    method = method_map.get(query.data)
    if not method:
        await query.edit_message_text("Invalid selection.")
        context.user_data.clear()
        return ConversationHandler.END

    sale_id = context.user_data.get("pay_sale_id")
    amount = context.user_data.get("pay_amount")
    user_id = context.user_data.get("db_user_id")

    if not sale_id or not amount or not user_id:
        await query.edit_message_text("⚠️ Payment session expired. Please start over with `/pay`.")
        context.user_data.clear()
        return ConversationHandler.END

    with get_bot_app().app_context():
        try:
            payment = SalesService.record_payment(
                sale_id=sale_id,
                amount=amount,
                method=method,
                user_id=user_id
            )
            sale = Sale.query.get(sale_id)
            status_text = "🎉 *FULLY SETTLED*" if sale.balance == 0 else f"Remaining: *{format_money(sale.balance)}*"

            receipt = (
                "✅ *Payment Recorded Successfully!*\n\n"
                f"• *Receipt #:* `PAY-{payment.id}`\n"
                f"• *Invoice #:* `#{sale.id}`\n"
                f"• *Item:* {sale.item}\n"
                f"• *Amount Paid:* *{format_money(payment.amount)}*\n"
                f"• *Method:* {payment.method.title()}\n"
                f"• *Status:* {status_text}\n"
            )
            await query.edit_message_text(receipt, parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"⚠️ Error recording payment: {str(e)}")

    context.user_data.clear()
    return ConversationHandler.END


async def pay_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel payment flow or gracefully switch commands."""
    context.user_data.clear()
    cmd = update.message.text.split()[0] if update.message and update.message.text else "/cancel"
    if cmd in ("/cancel", "/stop"):
        if update.message:
            await update.message.reply_text("Payment recording cancelled.")
    else:
        if update.message:
            await update.message.reply_text(
                f"⚠️ *Payment cancelled.* Switched to `{cmd}`. Please re-send `{cmd}` to continue.",
                parse_mode="Markdown"
            )
    return ConversationHandler.END


def get_pay_conversation_handler() -> ConversationHandler:
    """Construct and return the /pay ConversationHandler."""
    return ConversationHandler(
        entry_points=[CommandHandler("pay", pay_start)],
        states={
            SALE_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_sale_id)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_amount)],
            METHOD: [CallbackQueryHandler(pay_method_callback, pattern="^(pay_method_|pay_cancel)")],
        },
        fallbacks=[
            CommandHandler("cancel", pay_cancel),
            CommandHandler("stop", pay_cancel),
            CommandHandler("start", pay_cancel),
            CommandHandler("sale", pay_cancel),
            CommandHandler("mysales", pay_cancel),
            CommandHandler("today", pay_cancel),
            CommandHandler("report", pay_cancel),
            CommandHandler("logout", pay_cancel),
        ],
        allow_reentry=True,
    )
