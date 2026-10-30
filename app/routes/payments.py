from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.payment import Payment
from app.models.sale import Sale
from app.forms.sales_forms import PaymentForm
from app.services.sales_service import SalesService

payments_bp = Blueprint("payments", __name__, url_prefix="/payments")


@payments_bp.route("/")
@login_required
def index():
    """List recorded payments."""
    query = Payment.query.join(Sale, Payment.sale_id == Sale.id)

    if current_user.is_employee:
        query = query.filter(Sale.employee_id == current_user.id)

    # Filter by payment method
    method_filter = request.args.get("method", "").strip().lower()
    if method_filter in Payment.VALID_METHODS:
        query = query.filter(Payment.method == method_filter)

    # Date range filters
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()
    date_str = request.args.get("date", "").strip()

    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(Payment.created_at >= start_dt)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            query = query.filter(Payment.created_at <= end_dt)
        except ValueError:
            pass
    if date_str and not start_date_str and not end_date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter(
                Payment.created_at >= datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc),
                Payment.created_at < datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)
            )
            start_date_str = date_str
            end_date_str = date_str
        except ValueError:
            pass

    payments = query.order_by(Payment.created_at.desc()).all()
    total_amount = round(sum(p.amount for p in payments), 2)

    return render_template(
        "payments/index.html",
        payments=payments,
        total_amount=total_amount,
        selected_method=method_filter,
        start_date=start_date_str,
        end_date=end_date_str,
        selected_date=date_str
    )


@payments_bp.route("/record/<int:sale_id>", methods=["POST"])
@login_required
def record(sale_id: int):
    """Record a payment towards a sale."""
    form = PaymentForm()
    if form.validate_on_submit():
        try:
            from app.utils.formatting import format_money
            sale = Sale.query.get_or_404(sale_id)
            if current_user.is_employee and sale.employee_id != current_user.id:
                flash("You are not authorized to record payments for another employee's sale.", "danger")
                return redirect(url_for("sales.index"))

            payment = SalesService.record_payment(
                sale_id=sale.id,
                amount=float(form.amount.data),
                method=form.method.data,
                user_id=current_user.id
            )
            flash(
                f"Payment of {format_money(payment.amount)} via {payment.method.title()} recorded for Sale #{sale.id}!",
                "success"
            )
        except ValueError as e:
            flash(str(e), "danger")
    else:
        for err_list in form.errors.values():
            for err in err_list:
                flash(err, "danger")

    return redirect(request.referrer or url_for("sales.index"))
