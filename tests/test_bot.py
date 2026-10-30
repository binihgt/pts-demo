import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, User as TgUser, Message, Chat
from bot.main import build_bot_application
from bot.handlers.start import start_command
from bot.handlers.sales_query import today_command, mysales_command
from app.models.user import User
from app.models.sale import Sale
from app.extensions import db


def test_bot_application_builder_registers_all_handlers():
    """Verify that ApplicationBuilder mounts all required commands and conversation handlers."""
    dummy_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567"
    app = build_bot_application(dummy_token)
    assert app is not None
    # Verify handlers registered in group 0
    handlers = app.handlers[0]
    assert len(handlers) >= 7  # start, help, sale, pay, mysales, today, report


@pytest.mark.asyncio
async def test_bot_start_linking_flow(app):
    """Test linking an employee account via one-time code in Telegram /start."""
    with app.app_context():
        # Setup an employee with a link code
        emp = User.query.filter_by(username="emp_test").first()
        code = emp.generate_telegram_link_code()
        db.session.commit()

        # Mock Telegram Update and Context
        tg_user_id = 1122334455
        tg_user = TgUser(id=tg_user_id, is_bot=False, first_name="Alemu", username="alemu_tg")

        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.effective_user = tg_user
        update.message = message

        context = MagicMock()
        context.args = [code]

        # Call /start <CODE>
        await start_command(update, context)

        # Assert reply text indicates successful linking
        message.reply_text.assert_called_once()
        reply_content = message.reply_text.call_args[0][0]
        assert "Account Linked Successfully" in reply_content

        # Verify DB state
        updated_emp = User.query.filter_by(username="emp_test").first()
        assert updated_emp.telegram_id == tg_user_id
        assert updated_emp.telegram_link_code is None


@pytest.mark.asyncio
async def test_bot_unknown_user_polite_refusal(app):
    """Unknown telegram users without a code must be politely refused."""
    with app.app_context():
        unknown_tg_id = 999999999
        tg_user = TgUser(id=unknown_tg_id, is_bot=False, first_name="Stranger")

        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.effective_user = tg_user
        update.message = message

        context = MagicMock()
        context.args = []

        await start_command(update, context)

        message.reply_text.assert_called_once()
        reply = message.reply_text.call_args[0][0]
        assert "Welcome to PTS Demo Business Bot" in reply
        assert "/start <CODE>" in reply


@pytest.mark.asyncio
async def test_bot_role_guard_on_today_command(app):
    """Employees should be denied access to /today; CEOs should be granted."""
    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()
        emp.telegram_id = 5544332211
        db.session.commit()

        # 1. Test as Employee
        tg_user = TgUser(id=5544332211, is_bot=False, first_name="Employee")
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.effective_user = tg_user
        update.message = message
        context = MagicMock()
        context.user_data = {}

        await today_command(update, context)

        message.reply_text.assert_called_once()
        denied_msg = message.reply_text.call_args[0][0]
        assert "Permission Denied" in denied_msg
        assert "Ceo or Manager" in denied_msg

        # 2. Test as CEO
        ceo = User.query.filter_by(username="ceo_test").first()
        ceo.telegram_id = 9988776655
        db.session.commit()

        tg_ceo = TgUser(id=9988776655, is_bot=False, first_name="CEO")
        message_ceo = MagicMock(spec=Message)
        message_ceo.reply_text = AsyncMock()

        update_ceo = MagicMock(spec=Update)
        update_ceo.effective_user = tg_ceo
        update_ceo.message = message_ceo
        context_ceo = MagicMock()
        context_ceo.user_data = {}

        await today_command(update_ceo, context_ceo)

        message_ceo.reply_text.assert_called_once()
        ceo_msg = message_ceo.reply_text.call_args[0][0]
        assert "Company Daily Summary" in ceo_msg
        assert "Today's sales:" in ceo_msg
        assert "Collected today (all invoices):" in ceo_msg
        assert "Total outstanding (all invoices):" in ceo_msg


@pytest.mark.asyncio
async def test_bot_start_duplicate_link_refusal_does_not_consume_code(app):
    """When a Telegram ID is already linked to another user, refuse politely without consuming code."""
    with app.app_context():
        # Setup existing linked user
        ceo = User.query.filter_by(username="ceo_test").first()
        ceo.telegram_id = 7788990011
        db.session.commit()

        # Setup an employee with a fresh link code
        emp = User.query.filter_by(username="emp_test").first()
        code = emp.generate_telegram_link_code()
        db.session.commit()

        # Telegram user is CEO's telegram_id, but attempts to link emp's code
        tg_user = TgUser(id=7788990011, is_bot=False, first_name="DuplicateUser")
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.effective_user = tg_user
        update.message = message

        context = MagicMock()
        context.args = [code]

        await start_command(update, context)

        # Must reply with polite refusal
        message.reply_text.assert_called_once()
        reply = message.reply_text.call_args[0][0]
        assert "already linked to another user" in reply.lower()
        assert "unlink" in reply.lower()

        # Crucial check: The link code must NOT be consumed
        emp_refresh = User.query.filter_by(username="emp_test").first()
        assert emp_refresh.telegram_link_code == code
        assert emp_refresh.telegram_id is None


@pytest.mark.asyncio
async def test_bot_pay_start_without_args_prompts_unpaid_invoices(app):
    """Calling /pay without arguments prompts 'Which invoice number?' and lists unpaid invoices."""
    from bot.handlers.pay import pay_start
    from app.services.sales_service import SalesService

    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()
        emp.telegram_id = 4455667788
        db.session.commit()

        # Create an unpaid sale for this employee
        sale = SalesService.create_sale(
            employee_id=emp.id,
            item="Test Unpaid Laptop",
            quantity=1,
            unit_price=25000.0
        )

        tg_user = TgUser(id=4455667788, is_bot=False, first_name="EmployeeTester")
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.effective_user = tg_user
        update.message = message

        context = MagicMock()
        context.args = []
        context.user_data = {}

        state = await pay_start(update, context)

        message.reply_text.assert_called_once()
        prompt = message.reply_text.call_args[0][0]
        assert "Which invoice number would you like to pay?" in prompt
        assert f"Invoice #{sale.id}" in prompt
        assert "25,000.00 ETB" in prompt

