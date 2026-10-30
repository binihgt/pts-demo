import pytest
from app import create_app
from app.utils.formatting import (
    format_money,
    normalize_ethiopian_phone,
    validate_product_name,
    to_eat_datetime,
    format_eat_datetime,
)
from app.models.user import User
from app.models.customer import Customer
from app.services.sales_service import SalesService
from app.extensions import db


def test_format_money():
    """Verify that format_money formats strictly as '225,000.00 ETB'."""
    assert format_money(225000) == "225,000.00 ETB"
    assert format_money(0) == "0.00 ETB"
    assert format_money(1916000.5) == "1,916,000.50 ETB"
    assert format_money(440747.00) == "440,747.00 ETB"
    assert format_money(None) == "0.00 ETB"


def test_normalize_ethiopian_phone():
    """Verify Ethiopian phone number normalization and validation."""
    # Ethio Telecom prefixes (09, 9, 2519, +2519)
    assert normalize_ethiopian_phone("0911223344") == "+251911223344"
    assert normalize_ethiopian_phone("911223344") == "+251911223344"
    assert normalize_ethiopian_phone("+251911223344") == "+251911223344"
    assert normalize_ethiopian_phone("251911223344") == "+251911223344"

    # Safaricom Ethiopia prefixes (07, 7, 2517, +2517)
    assert normalize_ethiopian_phone("0711223344") == "+251711223344"
    assert normalize_ethiopian_phone("711223344") == "+251711223344"
    assert normalize_ethiopian_phone("+251711223344") == "+251711223344"

    # Whitespace and formatting characters stripped
    assert normalize_ethiopian_phone(" 0911-22 33 44 ") == "+251911223344"
    assert normalize_ethiopian_phone(None) is None
    assert normalize_ethiopian_phone("") is None

    # Invalid numbers rejected with clear ValueError
    with pytest.raises(ValueError, match="Invalid phone number"):
        normalize_ethiopian_phone("011234567")

    with pytest.raises(ValueError, match="Invalid phone number"):
        normalize_ethiopian_phone("12345")


def test_validate_product_name():
    """Verify product name length constraint (100) and multi-line rejection."""
    # Valid product name
    valid = validate_product_name("Samsung 24\" IPS Monitor")
    assert valid == "Samsung 24\" IPS Monitor"

    # Multi-line pasted text rejected
    with pytest.raises(ValueError, match="multiple lines"):
        validate_product_name("Line 1\nLine 2")

    with pytest.raises(ValueError, match="multiple lines"):
        validate_product_name("Line 1\r\nLine 2")

    # Over 100 characters rejected
    with pytest.raises(ValueError, match="too long"):
        validate_product_name("A" * 101)

    # Empty product name rejected
    with pytest.raises(ValueError, match="required"):
        validate_product_name("   ")


def test_customer_deduplication_case_insensitive_and_phone(app):
    """Test customer deduplication by case-insensitive name and normalized phone."""
    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()

        # 1. Create first sale with customer 'Desta Haile'
        s1 = SalesService.create_sale(
            employee_id=emp.id,
            item="Item 1",
            quantity=1,
            unit_price=100.0,
            customer_name="Desta Haile",
            customer_phone="0911223344"
        )
        c1_id = s1.customer_id
        assert s1.customer.phone == "+251911223344"

        # 2. Create second sale with lowercase 'desta haile'
        s2 = SalesService.create_sale(
            employee_id=emp.id,
            item="Item 2",
            quantity=1,
            unit_price=200.0,
            customer_name="desta haile",
            customer_phone="+251911223344"
        )
        assert s2.customer_id == c1_id

        # 3. Create third sale with matching phone without name
        s3 = SalesService.create_sale(
            employee_id=emp.id,
            item="Item 3",
            quantity=1,
            unit_price=300.0,
            customer_name=None,
            customer_phone="0911223344"
        )
        assert s3.customer_id == c1_id

        # Verify only 1 customer was created
        assert Customer.query.filter(Customer.phone == "+251911223344").count() == 1


def test_production_environment_security_refusal(monkeypatch):
    """Confirm production mode refuses to start with default secret key or demo passwords."""
    # Test 1: Insecure SECRET_KEY refusal
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "fallback-secret-key-change-me")

    with pytest.raises(RuntimeError, match="insecure or default SECRET_KEY"):
        create_app("production")

    # Test 2: Insecure demo passwords refusal
    monkeypatch.setenv("SECRET_KEY", "a-very-strong-production-secret-key-32chars-minimum!!")
    # create_app will check database users for demo passwords like Password123!
    with pytest.raises(RuntimeError, match="configured with default demo credentials"):
        create_app("production")
