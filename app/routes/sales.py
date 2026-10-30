from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.sale import Sale
from app.models.user import User
from app.models.customer import Customer
from app.forms.sales_forms import SaleForm, PaymentForm
from app.services.sales_service import SalesService

sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


@sales_bp.route("/")
@login_required
def index():
    """List sales with date, status, employee, and search filters."""
    query = Sale.query.join(User, Sale.employee_id == User.id).outerjoin(Customer, Sale.customer_id == Customer.id)

    # Role constraint: Employees only view their own sales
    if current_user.is_employee:
        query = query.filter(Sale.employee_id == current_user.id)
    else:
        # CEO / Manager can filter by specific employee
        selected_employee_id = request.args.get("employee_id", type=int)
        if selected_employee_id:
            query = query.filter(Sale.employee_id == selected_employee_id)

    # Search filter (item name or customer name)
    search_term = request.args.get("q", "").strip()
    if search_term:
        query = query.filter(
            (Sale.item.ilike(f"%{search_term}%")) | (Customer.name.ilike(f"%{search_term}%"))
        )

    # Date range filters
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()
    if start_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(Sale.created_at >= start_dt)
        except ValueError:
            pass
    if end_date_str:
        try:
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            query = query.filter(Sale.created_at <= end_dt)
        except ValueError:
            pass

    # Order newest first
    sales = query.order_by(Sale.created_at.desc()).all()

    # In-memory filter for computed payment status
    status_filter = request.args.get("status", "all").lower()
    if status_filter in ("paid", "partial", "unpaid"):
        sales = [s for s in sales if s.payment_status == status_filter]

    # Available employees for dropdown (CEOs/Managers)
    all_employees = User.query.filter(User.role.in_([User.ROLE_EMPLOYEE, User.ROLE_MANAGER])).all() if current_user.can_view_all_sales else []

    sale_form = SaleForm()
    payment_form = PaymentForm()

    return render_template(
        "sales/index.html",
        sales=sales,
        sale_form=sale_form,
        payment_form=payment_form,
        all_employees=all_employees,
        current_status=status_filter,
        search_term=search_term,
        start_date=start_date_str,
        end_date=end_date_str,
        selected_employee_id=request.args.get("employee_id", type=int)
    )


@sales_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    """Create a new sale."""
    form = SaleForm()
    if form.validate_on_submit():
        try:
            from app.utils.formatting import format_money
            sale = SalesService.create_sale(
                employee_id=current_user.id,
                item=form.item.data,
                quantity=form.quantity.data,
                unit_price=float(form.unit_price.data),
                customer_name=form.customer_name.data,
                customer_phone=form.customer_phone.data
            )
            flash(f"Sale #{sale.id} for '{sale.item}' ({format_money(sale.total)}) recorded successfully!", "success")
            return redirect(url_for("sales.index"))
        except ValueError as e:
            flash(str(e), "danger")

    return render_template("sales/create.html", form=form)
