import os
from flask import Flask, render_template
from app.config import config_by_name
from app.extensions import db, login_manager, csrf, limiter


def create_app(config_name: str | None = None) -> Flask:
    """Application factory for PTS Demo."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development").lower()

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    if "SECRET_KEY" in os.environ:
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

    # Dynamic environment variable overrides
    if "DATABASE_URL" in os.environ and config_name != "testing":
        env_db = os.environ["DATABASE_URL"]
        if env_db.startswith("postgres://"):
            env_db = env_db.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = env_db

    if "DEMO_MODE" in os.environ:
        app.config["DEMO_MODE"] = os.environ["DEMO_MODE"].lower() in ("true", "1", "yes")

    if "TELEGRAM_WEBHOOK_SECRET" in os.environ:
        app.config["TELEGRAM_WEBHOOK_SECRET"] = os.environ["TELEGRAM_WEBHOOK_SECRET"]

    if "TELEGRAM_BOT_TOKEN" in os.environ:
        app.config["TELEGRAM_BOT_TOKEN"] = os.environ["TELEGRAM_BOT_TOKEN"].strip()

    if "PUBLIC_URL" in os.environ and os.environ["PUBLIC_URL"].strip():
        app.config["PUBLIC_URL"] = os.environ["PUBLIC_URL"].strip()
    elif "RENDER_EXTERNAL_URL" in os.environ and os.environ["RENDER_EXTERNAL_URL"].strip():
        app.config["PUBLIC_URL"] = os.environ["RENDER_EXTERNAL_URL"].strip()
    elif "RENDER_EXTERNAL_HOSTNAME" in os.environ and os.environ["RENDER_EXTERNAL_HOSTNAME"].strip():
        app.config["PUBLIC_URL"] = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME'].strip()}"
    elif config_name == "production":
        app.config["PUBLIC_URL"] = "https://pts-demo.onrender.com"

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Register active app with bot context
    from bot.context import set_bot_app
    set_bot_app(app)

    # Configure user loader for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.sales import sales_bp
    from app.routes.payments import payments_bp
    from app.routes.employees import employees_bp
    from app.routes.audit import audit_bp
    from app.routes.reports import reports_bp
    from app.routes.health import health_bp
    from app.routes.webhook import webhook_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(webhook_bp)

    # Security headers on every response
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Content Security Policy (allows Bootstrap 5 CDN, Chart.js CDN, inline styles used by Bootstrap)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp
        return response

    # Template filters for clean currency & datetime display
    @app.template_filter("currency")
    def currency_filter(value):
        from app.utils.formatting import format_money
        return format_money(value)

    @app.template_filter("date_fmt")
    def date_filter(dt, fmt="%Y-%m-%d %H:%M"):
        from app.utils.formatting import format_eat_datetime
        return format_eat_datetime(dt, fmt=fmt)

    # Favicon route to prevent 404
    @app.route("/favicon.ico")
    def favicon():
        return app.send_static_file("favicon.svg")

    # Read-only enforcement for demo_ceo in Demo Mode
    @app.before_request
    def enforce_demo_readonly():
        from flask import request, flash, redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated and getattr(current_user, "username", "") == "demo_ceo":
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                if request.endpoint in ("auth.logout",):
                    return None
                flash("Demo environment notice: 'demo_ceo' is a read-only account. Data modifications are disabled.", "warning")
                return redirect(request.referrer or url_for("dashboard.overview"))

    # Production environment security assertions
    if config_name == "production":
        app.config["DEBUG"] = False
        app.config["TESTING"] = False

        # Refuse to start with default or weak secret key
        secret = app.config.get("SECRET_KEY", "")
        insecure_keys = {
            "fallback-secret-key-change-me",
            "dev-secret-key-pts-2026",
            "secret",
            "password",
            "your_secret_key_here",
            "default",
        }
        if not secret or secret in insecure_keys or "change-me" in secret or len(secret) < 16:
            raise RuntimeError(
                "CRITICAL SECURITY FAILURE: Application refuses to start in production with an insecure or default SECRET_KEY. "
                "Please configure a strong, random SECRET_KEY in your production environment."
            )

        # Refuse to start if active users have default demo passwords (unless in DEMO_MODE)
        if not app.config.get("DEMO_MODE", False):
            with app.app_context():
                try:
                    from app.models.user import User
                    demo_passwords = ["Password123!", "admin", "password"]
                    for u in User.query.filter_by(is_active=True).all():
                        for dp in demo_passwords:
                            if u.check_password(dp):
                                raise RuntimeError(
                                    f"CRITICAL SECURITY FAILURE: Application refuses to start in production because user '{u.username}' "
                                    f"is still configured with default demo credentials. Change all demo passwords before running in production."
                                )
                except Exception as e:
                    if isinstance(e, RuntimeError):
                        raise
                    # If database tables are not yet initialized, allow setup to proceed
                    pass

    # In DEMO_MODE, automatically create database tables and seed demo data on startup if empty
    if app.config.get("DEMO_MODE", False):
        with app.app_context():
            try:
                db.create_all()
                from app.models.user import User
                if User.query.first() is None:
                    from scripts.seed_data import seed_database
                    seed_database(app=app, recreate=False)
            except Exception as exc:
                app.logger.warning(f"Could not auto-seed database on startup: {exc}")
            finally:
                db.session.remove()
                try:
                    db.engine.dispose()
                except Exception:
                    pass

    # Auto-register Telegram webhook on startup if public URL and bot token are configured
    public_url = app.config.get("PUBLIC_URL", "").strip()
    bot_token = app.config.get("TELEGRAM_BOT_TOKEN", "").strip()
    secret_token = app.config.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    webhook_path = app.config.get("TELEGRAM_WEBHOOK_PATH", "/webhook/telegram").strip()

    if public_url and bot_token and not bot_token.startswith("mock_") and bot_token != "your_telegram_bot_token_here":
        try:
            from bot.webhook_dispatcher import register_webhook_async
            register_webhook_async(bot_token, public_url, webhook_path, secret_token)
        except Exception as exc:
            app.logger.warning(f"Could not initialize webhook registration: {exc}")

    # Global context processor
    @app.context_processor
    def inject_app_globals():
        return {
            "app_name": "PTS Demo",
            "demo_mode": bool(app.config.get("DEMO_MODE", False)),
        }

    # Error Handlers
    @app.errorhandler(400)
    def bad_request_error(e):
        return render_template("errors/400.html", error=e), 400

    @app.errorhandler(403)
    def forbidden_error(e):
        return render_template("errors/403.html", error=e), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template("errors/404.html", error=e), 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template("errors/429.html", error=e), 429

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html", error=e), 500

    return app
