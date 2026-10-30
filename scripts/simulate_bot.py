#!/usr/bin/env python3
"""
Interactive Telegram Bot Simulator for PTS Demo.
Allows testing all Telegram Bot commands (/start, /sale, /pay, /mysales, /today, /report)
interactively in the terminal without needing a live Telegram API token.
"""
import sys
import asyncio
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from telegram import Update, User as TgUser, Message
from bot.handlers.start import start_command, help_command
from bot.handlers.sales_query import mysales_command, today_command
from bot.handlers.report import report_command
from app import create_app
from app.models.user import User
from app.models.sale import Sale
from app.services.sales_service import SalesService

app = create_app()


def print_bot_reply(text: str):
    print("\n" + "─" * 55)
    print("🤖 [BOT REPLY]:")
    print(text)
    print("─" * 55 + "\n")


async def simulate():
    print("=" * 65)
    print("       PTS Demo - Interactive Telegram Bot Simulator")
    print("=" * 65)
    print("Test bot flows directly from your terminal.\n")

    # Pick a simulated Telegram user ID
    tg_id = 9876543210
    print(f"[*] Your Simulated Telegram User ID is: {tg_id}")

    context = MagicMock()
    context.user_data = {}
    context.args = []

    def make_update(msg_text: str):
        user = TgUser(id=tg_id, is_bot=False, first_name="Tester", username="tester_tg")
        msg = MagicMock(spec=Message)
        msg.text = msg_text
        
        async def reply(t, parse_mode=None, reply_markup=None):
            print_bot_reply(t)

        async def reply_doc(document, filename, caption=None, parse_mode=None):
            size = len(document.getvalue())
            print_bot_reply(f"📎 [DOCUMENT SENT]: {filename} ({size:,} bytes)\nCaption: {caption}")

        msg.reply_text = AsyncMock(side_effect=reply)
        msg.reply_document = AsyncMock(side_effect=reply_doc)

        up = MagicMock(spec=Update)
        up.effective_user = user
        up.message = msg
        return up

    with app.app_context():
        # Check current link status
        db_user = User.query.filter_by(telegram_id=tg_id).first()
        if db_user:
            print(f"[+] You are currently linked as: {db_user.name} ({db_user.role.title()})")
        else:
            print("[-] Your Telegram ID is currently UNLINKED.")
            # Find an employee link code
            emp = User.query.filter(User.role == User.ROLE_EMPLOYEE, User.telegram_link_code.isnot(None)).first()
            if emp:
                print(f"💡 Tip: Try linking using employee {emp.name}'s code: {emp.telegram_link_code}")

    print("\nCommands to test:")
    print("  /start <code>   - Link your account (e.g. /start <CODE>)")
    print("  /mysales        - View your sales today")
    print("  /today          - View company totals today (Manager/CEO)")
    print("  /report         - Download Excel report in chat (Manager/CEO)")
    print("  /sale_quick     - Simulate recording a complete sale")
    print("  /pay_quick      - Simulate recording a payment")
    print("  /help           - View commands")
    print("  exit            - Quit simulator\n")

    while True:
        try:
            cmd = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting simulator.")
            break

        if not cmd:
            continue
        if cmd.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        parts = cmd.split()
        base_cmd = parts[0].lower()
        context.args = parts[1:]

        up = make_update(cmd)

        if base_cmd == "/start":
            await start_command(up, context)

        elif base_cmd == "/help":
            await help_command(up, context)

        elif base_cmd == "/mysales":
            await mysales_command(up, context)

        elif base_cmd == "/today":
            await today_command(up, context)

        elif base_cmd == "/report":
            await report_command(up, context)

        elif base_cmd == "/sale_quick":
            with app.app_context():
                user = User.query.filter_by(telegram_id=tg_id).first()
                if not user:
                    print_bot_reply("⛔ Access Denied: You must link your account first using `/start <CODE>`.")
                    continue

                item = input("  Enter product name [Dell Latitude 5420]: ").strip() or "Dell Latitude 5420"
                qty_s = input("  Enter quantity [2]: ").strip() or "2"
                price_s = input("  Enter unit price [45000]: ").strip() or "45000"
                cust = input("  Enter customer name [Ato Desta]: ").strip() or "Ato Desta"

                try:
                    qty = int(qty_s)
                    price = float(price_s)
                    sale = SalesService.create_sale(
                        employee_id=user.id,
                        item=item,
                        quantity=qty,
                        unit_price=price,
                        customer_name=cust
                    )
                    receipt = (
                        "🧾 *Sale Saved Successfully!*\n\n"
                        f"• *Invoice ID:* `#{sale.id}`\n"
                        f"• *Item:* {sale.item} (x{sale.quantity})\n"
                        f"• *Total Amount:* *{sale.total:,.2f} ETB*\n"
                        f"• *Customer:* {sale.customer.name if sale.customer else '-'}\n"
                        f"• *Status:* Unpaid\n\n"
                        f"💡 _To pay against this invoice:_ `/pay_quick {sale.id}`"
                    )
                    print_bot_reply(receipt)
                except Exception as e:
                    print_bot_reply(f"⚠️ Error creating sale: {e}")

        elif base_cmd == "/pay_quick":
            with app.app_context():
                user = User.query.filter_by(telegram_id=tg_id).first()
                if not user:
                    print_bot_reply("⛔ Access Denied: You must link your account first using `/start <CODE>`.")
                    continue

                sale_id_s = parts[1] if len(parts) > 1 else input("  Enter Invoice ID: ").strip()
                if not sale_id_s.isdigit():
                    print("Invalid ID.")
                    continue
                sale_id = int(sale_id_s)
                sale = Sale.query.get(sale_id)
                if not sale:
                    print_bot_reply(f"❌ Invoice #{sale_id} not found.")
                    continue
                if sale.balance <= 0:
                    print_bot_reply(f"✅ Invoice #{sale.id} is already fully paid!")
                    continue

                amt_s = input(f"  Enter amount to pay (Balance: {sale.balance:,.2f} ETB): ").strip()
                method = input("  Enter payment method (telebirr / bank / cash) [telebirr]: ").strip().lower() or "telebirr"

                try:
                    amt = float(amt_s)
                    pay = SalesService.record_payment(
                        sale_id=sale.id,
                        amount=amt,
                        method=method,
                        user_id=user.id
                    )
                    status_text = "🎉 FULLY SETTLED" if sale.balance == 0 else f"Remaining: {sale.balance:,.2f} ETB"
                    print_bot_reply(
                        f"✅ Payment of {pay.amount:,.2f} ETB via {pay.method.title()} recorded for Invoice #{sale.id}!\n"
                        f"Status: {status_text}"
                    )
                except Exception as e:
                    print_bot_reply(f"⚠️ Error recording payment: {e}")
        else:
            print(f"Unknown command '{base_cmd}'. Type /help for options.")


if __name__ == "__main__":
    asyncio.run(simulate())
