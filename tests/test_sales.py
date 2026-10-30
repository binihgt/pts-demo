import pytest
from app.models.user import User
from app.models.customer import Customer
from app.models.sale import Sale
from app.models.payment import Payment
from app.services.sales_service import SalesService
from app.extensions import db


def test_create_sale_and_total_calculation(app):
    """Test sale calculation and database persistence."""
    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()
        sale = SalesService.create_sale(
            employee_id=emp.id,
            item="HP LaserJet Pro M404dn",
            quantity=3,
            unit_price=28000.0,
            customer_name="Ato Girma",
            customer_phone="+251911001122"
        )
        assert sale.id is not None
        assert sale.total == 84000.0
        assert sale.balance == 84000.0
        assert sale.payment_status == "unpaid"
        assert sale.customer.name == "Ato Girma"


def test_record_partial_and_full_payment(app):
    """Test payment balance reduction and status transitions."""
    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()
        sale = SalesService.create_sale(
            employee_id=emp.id,
            item="Samsung 24\" IPS Monitor",
            quantity=2,
            unit_price=12500.0
        )
        assert sale.total == 25000.0

        # 1. Record Partial Payment (10,000 ETB via Telebirr)
        p1 = SalesService.record_payment(
            sale_id=sale.id,
            amount=10000.0,
            method="telebirr",
            user_id=emp.id
        )
        assert p1.id is not None
        assert sale.total_paid == 10000.0
        assert sale.balance == 15000.0
        assert sale.payment_status == "partial"

        # 2. Record Remaining Payment (15,000 ETB via Bank)
        p2 = SalesService.record_payment(
            sale_id=sale.id,
            amount=15000.0,
            method="bank",
            user_id=emp.id
        )
        assert sale.total_paid == 25000.0
        assert sale.balance == 0.0
        assert sale.payment_status == "paid"


def test_payment_exceeding_balance_raises_error(app):
    """Test that payments exceeding the outstanding balance are rejected."""
    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()
        sale = SalesService.create_sale(
            employee_id=emp.id,
            item="Logitech Mouse",
            quantity=1,
            unit_price=1000.0
        )

        with pytest.raises(ValueError, match="exceeds remaining balance"):
            SalesService.record_payment(
                sale_id=sale.id,
                amount=1500.0,
                method="cash",
                user_id=emp.id
            )


def test_invalid_sale_inputs(app):
    """Test validation errors on negative quantity or unit price."""
    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()

        with pytest.raises(ValueError, match="Quantity must be greater than zero"):
            SalesService.create_sale(
                employee_id=emp.id,
                item="Invalid Item",
                quantity=0,
                unit_price=500.0
            )

        with pytest.raises(ValueError, match="Unit price must be greater than zero"):
            SalesService.create_sale(
                employee_id=emp.id,
                item="Invalid Item",
                quantity=1,
                unit_price=-10.0
            )
