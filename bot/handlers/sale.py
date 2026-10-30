from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from bot.context import get_bot_app
from app.services.sales_service import SalesService
from app.utils.formatting import (
    format_money,
    validate_product_name,
    normalize_ethiopian_phone,
)
from bot.auth import get_current_user

# Conversation states
ITEM, QUANTITY, PRICE, CUSTOMER, CONFIRM = range(5)


async def sale_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Initiate guided /sale conversation."""
    telegram_user = update.effective_user
    if not telegram_user or not update.message:
        return ConversationHandler.END

    user = get_current_user(telegram_user.id)
    if not user:
        await update.message.reply_text(
            "⛔ *Access Denied*\nYour Telegram account is not registered. Please use `/start <CODE>`.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    context.user_data["db_user_id"] = user.id
    context.user_data["db_user_name"] = user.name

    await update.message.reply_text(
        "🛍️ *Record New Sale (Step 1/4)*\n\n"
        "What product or service was sold?\n"
        "Example: `Samsung 24\" IPS Monitor`\n\n"
        "_(Send /cancel at any time to abort)_",
        parse_mode="Markdown"
    )
    return ITEM


async def sale_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate item name (max 100 chars, no newlines) and request quantity."""
    raw_text = update.message.text
    try:
        clean_item = validate_product_name(raw_text)
    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ {str(e)}\n\nPlease enter a valid single-line product name (max 100 characters):"
        )
        return ITEM

    context.user_data["sale_item"] = clean_item
    await update.message.reply_text(
        f"Item: *{clean_item}*\n\n"
        "🔢 *Step 2/4: How many units were sold?*\n"
        "Please enter a whole number (e.g. `1`, `2`, `5`):",
        parse_mode="Markdown"
    )
    return QUANTITY


async def sale_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store quantity and request unit price."""
    text = update.message.text.strip()
    try:
        qty = int(text)
        if qty <= 0 or qty > 10000:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid quantity between 1 and 10,000:")
        return QUANTITY

    context.user_data["sale_qty"] = qty
    await update.message.reply_text(
        f"Quantity: *{qty}*\n\n"
        "💰 *Step 3/4: What is the unit price in ETB?*\n"
        "Example: `12500` or `12500.50`:",
        parse_mode="Markdown"
    )
    return PRICE


async def sale_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store unit price and request customer information."""
    text = update.message.text.strip().replace(",", "")
    try:
        price = float(text)
        if price <= 0:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a positive number for the unit price (e.g. `1500.00`):")
        return PRICE

    context.user_data["sale_price"] = price
    qty = context.user_data["sale_qty"]
    total = round(qty * price, 2)
    context.user_data["sale_total"] = total

    await update.message.reply_text(
        f"Unit Price: *{format_money(price)}*\n"
        f"Estimated Total: *{format_money(total)}*\n\n"
        "👤 *Step 4/4: Who is the customer?*\n"
        "Enter customer name (and optional phone), or send `/skip` for a walk-in customer:\n\n"
        "Example: `Desta Haile, 0911223344` or `Desta Haile, +251911223344`",
        parse_mode="Markdown"
    )
    return CUSTOMER


async def sale_customer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate customer phone and prompt for final confirmation."""
    text = update.message.text.strip()
    if text.lower() == "/skip":
        context.user_data["customer_name"] = None
        context.user_data["customer_phone"] = None
        cust_display = "Direct Walk-in"
    else:
        # Check if user passed name and phone separated by comma
        parts = [p.strip() for p in text.split(",", 1)]
        raw_name = parts[0]
        raw_phone = parts[1] if len(parts) > 1 else None

        clean_phone = None
        if raw_phone:
            try:
                clean_phone = normalize_ethiopian_phone(raw_phone)
            except ValueError as e:
                await update.message.reply_text(
                    f"⚠️ {str(e)}\n\n"
                    "Please re-enter the customer info as: `Name, Phone` (e.g. `Desta Haile, 0911223344`) or send `/skip`:"
                )
                return CUSTOMER

        context.user_data["customer_name"] = raw_name
        context.user_data["customer_phone"] = clean_phone
        cust_display = f"{raw_name} ({clean_phone})" if clean_phone else raw_name

    item = context.user_data["sale_item"]
    qty = context.user_data["sale_qty"]
    price = context.user_data["sale_price"]
    total = context.user_data["sale_total"]

    confirmation_text = (
        "📋 *Please Confirm This Sale:*\n\n"
        f"• *Product:* {item}\n"
        f"• *Quantity:* {qty}\n"
        f"• *Unit Price:* {format_money(price)}\n"
        f"• *Total Amount:* *{format_money(total)}*\n"
        f"• *Customer:* {cust_display}\n\n"
        "Do you want to save this sale?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm & Save", callback_data="confirm_sale"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_sale"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(confirmation_text, reply_markup=reply_markup, parse_mode="Markdown")
    return CONFIRM


async def sale_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation callback."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_sale":
        await query.edit_message_text("❌ *Sale Cancelled.* No changes were saved.", parse_mode="Markdown")
        context.user_data.clear()
        return ConversationHandler.END

    # Proceed to save sale
    user_id = context.user_data.get("db_user_id")
    item = context.user_data.get("sale_item")
    qty = context.user_data.get("sale_qty")
    price = context.user_data.get("sale_price")
    c_name = context.user_data.get("customer_name")
    c_phone = context.user_data.get("customer_phone")

    with get_bot_app().app_context():
        try:
            sale = SalesService.create_sale(
                employee_id=user_id,
                item=item,
                quantity=qty,
                unit_price=price,
                customer_name=c_name,
                customer_phone=c_phone
            )
            success_msg = (
                "🧾 *Sale Saved Successfully!*\n\n"
                f"• *Invoice ID:* `#{sale.id}`\n"
                f"• *Item:* {sale.item} (x{sale.quantity})\n"
                f"• *Total:* *{format_money(sale.total)}*\n"
                f"• *Status:* Unpaid\n\n"
                f"💡 _To record a payment for this invoice, type:_ `/pay {sale.id}`"
            )
            await query.edit_message_text(success_msg, parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(f"⚠️ Error saving sale: {str(e)}")

    context.user_data.clear()
    return ConversationHandler.END


async def sale_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel guided sale conversation."""
    context.user_data.clear()
    if update.message:
        await update.message.reply_text("Sale operation cancelled.")
    return ConversationHandler.END


def get_sale_conversation_handler() -> ConversationHandler:
    """Construct and return the /sale ConversationHandler."""
    return ConversationHandler(
        entry_points=[CommandHandler("sale", sale_start)],
        states={
            ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, sale_item)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, sale_quantity)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sale_price)],
            CUSTOMER: [
                CommandHandler("skip", sale_customer),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sale_customer),
            ],
            CONFIRM: [CallbackQueryHandler(sale_confirm_callback, pattern="^(confirm_sale|cancel_sale)$")],
        },
        fallbacks=[CommandHandler("cancel", sale_cancel)],
        allow_reentry=True,
    )
