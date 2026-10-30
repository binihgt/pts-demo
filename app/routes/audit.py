from flask import Blueprint, render_template, request
from app.models.audit import AuditLog
from app.utils.decorators import ceo_required

audit_bp = Blueprint("audit", __name__, url_prefix="/audit")


@audit_bp.route("/")
@ceo_required
def index():
    """CEO-only: Audit trail of business and security events."""
    query = AuditLog.query

    action_filter = request.args.get("action", "").strip()
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))

    logs = query.order_by(AuditLog.created_at.desc()).limit(150).all()
    actions = [r[0] for r in AuditLog.query.with_entities(AuditLog.action).distinct()]

    return render_template(
        "audit/index.html",
        logs=logs,
        actions=actions,
        selected_action=action_filter
    )
