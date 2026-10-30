from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from app.extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for cloud hosting (Render, health monitors).
    Returns 200 OK when application and database are operational.
    Returns 503 Service Unavailable when database connection fails.
    """
    db_status = "healthy"
    status_code = 200

    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:
        current_app.logger.error(f"Health check DB ping failed: {exc}")
        db_status = "unhealthy"
        status_code = 503

    return jsonify({
        "status": "ok" if status_code == 200 else "degraded",
        "database": db_status,
        "demo_mode": bool(current_app.config.get("DEMO_MODE", False)),
    }), status_code
