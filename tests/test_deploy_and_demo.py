import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.sale import Sale
from bot.webhook_dispatcher import register_webhook_async, dispatch_telegram_update


def test_health_endpoint_healthy(client):
    """Verify /health returns HTTP 200 with JSON details when database is healthy."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "healthy"
    assert "demo_mode" in data


def test_health_endpoint_degraded_on_db_failure(client, monkeypatch):
    """Verify /health returns HTTP 503 when the database ping fails."""
    def broken_execute(*args, **kwargs):
        raise RuntimeError("Simulated DB connection failure")

    monkeypatch.setattr(db.session, "execute", broken_execute)

    response = client.get("/health")
    assert response.status_code == 503
    assert response.is_json
    data = response.get_json()
    assert data["status"] == "degraded"
    assert data["database"] == "unhealthy"


def test_database_url_normalization(monkeypatch):
    """Verify DATABASE_URL converts postgres:// to postgresql:// for SQLAlchemy."""
    raw_url = "postgres://pts_user:secret_pwd@free-render-host.com:5432/pts_demo"
    monkeypatch.setenv("DATABASE_URL", raw_url)
    app = create_app(config_name="development")
    expected_url = "postgresql://pts_user:secret_pwd@free-render-host.com:5432/pts_demo"
    assert app.config["SQLALCHEMY_DATABASE_URI"] == expected_url


def test_telegram_webhook_secret_verification(client, app):
    """Verify Telegram webhook endpoint checks X-Telegram-Bot-Api-Secret-Token."""
    app.config["TELEGRAM_WEBHOOK_SECRET"] = "my-secure-webhook-secret-999"

    # 1. Missing secret token header -> 403 Forbidden
    res = client.post("/webhook/telegram", json={"update_id": 100})
    assert res.status_code == 403

    # 2. Invalid secret token header -> 403 Forbidden
    res = client.post(
        "/webhook/telegram",
        json={"update_id": 100},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"}
    )
    assert res.status_code == 403

    # 3. Valid secret token header but invalid JSON payload -> 400 Bad Request
    res = client.post(
        "/webhook/telegram",
        data="not-a-json",
        content_type="text/plain",
        headers={"X-Telegram-Bot-Api-Secret-Token": "my-secure-webhook-secret-999"}
    )
    assert res.status_code == 400

    # 4. Valid secret token header and valid JSON payload -> 200 OK
    with patch("bot.webhook_dispatcher.dispatch_telegram_update") as mock_dispatch:
        res = client.post(
            "/webhook/telegram",
            json={"update_id": 101, "message": {"text": "/help"}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "my-secure-webhook-secret-999"}
        )
        assert res.status_code == 200
        mock_dispatch.assert_called_once()


def test_demo_mode_banner_rendering(client, app):
    """Verify top banner renders in DEMO_MODE=True and is absent when False."""
    # When DEMO_MODE is True
    app.config["DEMO_MODE"] = True
    res = client.get("/auth/login")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "demo-mode-banner" in html
    assert "Demo environment" in html
    assert "demo_ceo" in html

    # When DEMO_MODE is False
    app.config["DEMO_MODE"] = False
    res2 = client.get("/auth/login")
    html2 = res2.get_data(as_text=True)
    assert "demo-mode-banner" not in html2


def test_demo_ceo_readonly_restrictions(client, app):
    """Verify demo_ceo account can browse but cannot perform mutations (POST)."""
    with app.app_context():
        # Create demo_ceo user
        demo_ceo = User(
            name="Demo CEO",
            username="demo_ceo",
            role=User.ROLE_CEO,
            is_active=True
        )
        demo_ceo.set_password("DemoCEO123!")
        db.session.add(demo_ceo)
        db.session.commit()

    # Log in as demo_ceo
    login_res = client.post(
        "/auth/login",
        data={"username": "demo_ceo", "password": "DemoCEO123!"},
        follow_redirects=True
    )
    assert login_res.status_code == 200
    html = login_res.get_data(as_text=True)
    assert "Demo CEO" in html
    assert "Read-Only" in html

    # 1. GET requests are allowed
    overview_res = client.get("/overview")
    assert overview_res.status_code == 200

    sales_view_res = client.get("/sales/")
    assert sales_view_res.status_code == 200

    # 2. POST mutations are blocked and redirected
    create_emp_res = client.post(
        "/employees/create",
        data={
            "name": "Hacked Employee",
            "username": "hacked_user",
            "role": "employee",
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
        follow_redirects=True
    )
    assert create_emp_res.status_code == 200
    page_text = create_emp_res.get_data(as_text=True)
    assert "read-only account" in page_text

    with app.app_context():
        # Verify employee was NOT created in DB
        assert User.query.filter_by(username="hacked_user").first() is None


def test_demo_mode_auto_seed_on_empty_db(monkeypatch, tmp_path):
    """Verify that starting in DEMO_MODE with an empty DB automatically creates tables and seeds demo data."""
    test_db_path = tmp_path / "autoseed_demo.db"
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db_path}")

    # Launch app in development mode with DEMO_MODE=True
    fresh_app = create_app(config_name="development")

    with fresh_app.app_context():
        # Check that demo CEO and sales data were automatically created
        demo_user = User.query.filter_by(username="demo_ceo").first()
        assert demo_user is not None
        assert demo_user.role == User.ROLE_CEO
        assert demo_user.check_password("DemoCEO123!")

        admin_user = User.query.filter_by(username="admin").first()
        assert admin_user is not None

        sales_count = Sale.query.count()
        assert sales_count >= 50


@pytest.mark.asyncio
async def test_webhook_auto_registration_flow():
    """Verify auto-registration logic contacts Telegram Bot API to set webhook."""
    fake_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567"
    public_url = "https://pts-demo.onrender.com"
    webhook_secret = "generated-secret-xyz"

    mock_bot = MagicMock()
    mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
    mock_bot.__aexit__ = AsyncMock(return_value=None)
    mock_bot.get_webhook_info = AsyncMock(return_value=MagicMock(url="https://old-url.com"))
    mock_bot.set_webhook = AsyncMock()

    with patch("bot.webhook_dispatcher.Bot", return_value=mock_bot):
        # Call registration
        register_webhook_async(
            token=fake_token,
            public_url=public_url,
            webhook_path="/webhook/telegram",
            secret=webhook_secret
        )

        import time
        # Give daemon thread a brief moment to run
        for _ in range(25):
            if mock_bot.set_webhook.called:
                break
            time.sleep(0.05)

        assert mock_bot.set_webhook.called
        call_kwargs = mock_bot.set_webhook.call_args[1]
        assert call_kwargs["url"] == "https://pts-demo.onrender.com/webhook/telegram"
        assert call_kwargs["secret_token"] == webhook_secret
