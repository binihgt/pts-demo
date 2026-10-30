from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.services.sales_service import SalesService
from app.forms.sales_forms import PaymentForm

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Root redirect to overview or login."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/overview")
@login_required
def overview():
    """Executive KPI overview tailored by role."""
    metrics = SalesService.get_dashboard_metrics(current_user)
    payment_form = PaymentForm()
    return render_template(
        "dashboard/overview.html",
        metrics=metrics,
        payment_form=payment_form
    )
