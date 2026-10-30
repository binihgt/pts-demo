from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from app.extensions import db
from app.models.user import User
from app.models.customer import Customer
from app.models.sale import Sale
from app.models.payment import Payment
from app.models.audit import AuditLog
from app.utils.formatting import (
    format_money,
    validate_product_name,
    normalize_ethiopian_phone,
)


def ensure_dt(dt: datetime | None) -> datetime | None:
    """Ensure datetime is timezone-aware in UTC for safe comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class SalesService:
    """Service layer encapsulating sales, payments, and financial calculations."""

    @staticmethod
    def create_sale(
        employee_id: int,
        item: str,
        quantity: int,
        unit_price: float,
        customer_name: str | None = None,
        customer_phone: str | None = None,
    ) -> Sale:
        """Create a new sale transaction with customer resolution and audit logging."""
        # 1. Product Name Validation (max 100 chars, no newlines)
        clean_item = validate_product_name(item)

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")
        if unit_price <= 0:
            raise ValueError("Unit price must be greater than zero.")

        total = round(float(quantity) * float(unit_price), 2)

        # 2. Customer Phone Validation & Normalization (+2519... or +2517...)
        clean_phone = normalize_ethiopian_phone(customer_phone)

        # 3. Customer Lookup (Case-insensitive name or normalized phone)
        customer_id = None
        if customer_name and customer_name.strip():
            clean_name = customer_name.strip()
            customer = None

            if clean_phone:
                customer = Customer.query.filter_by(phone=clean_phone).first()

            if not customer:
                customer = Customer.query.filter(
                    func.lower(Customer.name) == clean_name.lower()
                ).first()

            if customer:
                # Update phone if existing customer didn't have one
                if clean_phone and not customer.phone:
                    customer.phone = clean_phone
            else:
                customer = Customer(name=clean_name, phone=clean_phone)
                db.session.add(customer)
                db.session.flush()

            customer_id = customer.id
        elif clean_phone:
            # Phone provided without name
            customer = Customer.query.filter_by(phone=clean_phone).first()
            if not customer:
                customer = Customer(name="Customer", phone=clean_phone)
                db.session.add(customer)
                db.session.flush()
            customer_id = customer.id

        sale = Sale(
            employee_id=employee_id,
            customer_id=customer_id,
            item=clean_item,
            quantity=quantity,
            unit_price=float(unit_price),
            total=total,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(sale)
        db.session.flush()

        AuditLog.log(
            action="SALE_RECORDED",
            user_id=employee_id,
            details=f"Sale #{sale.id} recorded: '{sale.item}' (Qty: {sale.quantity}, Total: {format_money(sale.total)})."
        )
        db.session.commit()
        return sale

    @staticmethod
    def record_payment(
        sale_id: int,
        amount: float,
        method: str,
        user_id: int | None = None,
    ) -> Payment:
        """Record a payment towards a sale balance."""
        sale = db.session.get(Sale, sale_id)
        if not sale:
            raise ValueError(f"Sale #{sale_id} not found.")

        amount = round(float(amount), 2)
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        balance = sale.balance
        if amount > balance:
            raise ValueError(
                f"Payment amount ({format_money(amount)}) exceeds remaining balance ({format_money(balance)})."
            )

        if method not in Payment.VALID_METHODS:
            raise ValueError(f"Invalid payment method '{method}'. Valid options: {', '.join(Payment.VALID_METHODS)}")

        payment = Payment(
            sale_id=sale.id,
            amount=amount,
            method=method,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(payment)
        db.session.flush()

        AuditLog.log(
            action="PAYMENT_RECORDED",
            user_id=user_id,
            details=f"Payment #{payment.id} of {format_money(payment.amount)} recorded for Sale #{sale.id} via {payment.method.title()}."
        )
        db.session.commit()
        return payment

    @staticmethod
    def get_company_totals() -> dict:
        """
        Unified single-source-of-truth calculations for totals across:
        - Telegram /today command
        - Dashboard Overview
        - Excel Report Summary sheet
        """
        now = datetime.now(timezone.utc)
        start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        start_of_week = start_of_today - timedelta(days=now.weekday())
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        all_sales = Sale.query.order_by(Sale.created_at.desc()).all()
        all_payments = Payment.query.order_by(Payment.created_at.desc()).all()

        # Sales today
        today_sales = [s for s in all_sales if ensure_dt(s.created_at) >= start_of_today]
        today_sales_total = round(sum(s.total for s in today_sales), 2)
        today_sales_count = len(today_sales)

        # Collections today across all invoices
        today_payments = [p for p in all_payments if ensure_dt(p.created_at) >= start_of_today]
        today_collected_total = round(sum(p.amount for p in today_payments), 2)

        # Collections breakdown today
        today_telebirr = round(sum(p.amount for p in today_payments if p.method == Payment.METHOD_TELEBIRR), 2)
        today_bank = round(sum(p.amount for p in today_payments if p.method == Payment.METHOD_BANK), 2)
        today_cash = round(sum(p.amount for p in today_payments if p.method == Payment.METHOD_CASH), 2)

        # Week metrics
        week_sales = [s for s in all_sales if ensure_dt(s.created_at) >= start_of_week]
        week_sales_total = round(sum(s.total for s in week_sales), 2)
        week_payments = [p for p in all_payments if ensure_dt(p.created_at) >= start_of_week]
        week_collected_total = round(sum(p.amount for p in week_payments), 2)

        # Month metrics
        month_sales = [s for s in all_sales if ensure_dt(s.created_at) >= start_of_month]
        month_sales_total = round(sum(s.total for s in month_sales), 2)
        month_payments = [p for p in all_payments if ensure_dt(p.created_at) >= start_of_month]
        month_collected_total = round(sum(p.amount for p in month_payments), 2)

        # All-time metrics & Total Outstanding across ALL active invoices
        all_time_sales_total = round(sum(s.total for s in all_sales), 2)
        all_time_collected_total = round(sum(p.amount for p in all_payments), 2)
        unpaid_sales = [s for s in all_sales if s.balance > 0]
        total_outstanding = round(sum(s.balance for s in unpaid_sales), 2)

        return {
            "today_sales_total": today_sales_total,
            "today_sales_count": today_sales_count,
            "today_collected_total": today_collected_total,
            "today_telebirr": today_telebirr,
            "today_bank": today_bank,
            "today_cash": today_cash,
            "week_sales_total": week_sales_total,
            "week_collected_total": week_collected_total,
            "month_sales_total": month_sales_total,
            "month_collected_total": month_collected_total,
            "all_time_sales_total": all_time_sales_total,
            "all_time_collected_total": all_time_collected_total,
            "total_outstanding": total_outstanding,
            "unpaid_count": len(unpaid_sales),
        }

    @staticmethod
    def get_dashboard_metrics(user: User) -> dict:
        """Calculate KPI metrics, sales chart points, top performers, and unpaid debts."""
        now = datetime.now(timezone.utc)
        start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        start_of_week = start_of_today - timedelta(days=now.weekday())
        start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

        # Base queries (filtered by employee if role is employee)
        sales_query = Sale.query
        payments_query = Payment.query.join(Sale)

        if user.is_employee:
            sales_query = sales_query.filter(Sale.employee_id == user.id)
            payments_query = payments_query.filter(Sale.employee_id == user.id)

        all_sales = sales_query.order_by(Sale.created_at.desc()).all()
        all_payments = payments_query.all()

        # Today metrics
        today_sales = [s for s in all_sales if ensure_dt(s.created_at) >= start_of_today]
        today_total = round(sum(s.total for s in today_sales), 2)
        today_count = len(today_sales)
        today_collected = round(
            sum(p.amount for p in all_payments if ensure_dt(p.created_at) >= start_of_today),
            2
        )

        # Week metrics
        week_sales = [s for s in all_sales if ensure_dt(s.created_at) >= start_of_week]
        week_total = round(sum(s.total for s in week_sales), 2)
        week_collected = round(
            sum(p.amount for p in all_payments if ensure_dt(p.created_at) >= start_of_week),
            2
        )

        # Month metrics
        month_sales = [s for s in all_sales if ensure_dt(s.created_at) >= start_of_month]
        month_total = round(sum(s.total for s in month_sales), 2)
        month_collected = round(
            sum(p.amount for p in all_payments if ensure_dt(p.created_at) >= start_of_month),
            2
        )

        # Total outstanding for this user (or company-wide for CEO/Manager)
        unpaid_sales = [s for s in all_sales if s.balance > 0]
        total_unpaid = round(sum(s.balance for s in unpaid_sales), 2)

        # Trend Chart Data (Last 14 days)
        chart_labels = []
        chart_values = []
        for d in range(13, -1, -1):
            day_dt = start_of_today - timedelta(days=d)
            next_day_dt = day_dt + timedelta(days=1)
            day_sum = sum(
                s.total for s in all_sales if day_dt <= ensure_dt(s.created_at) < next_day_dt
            )
            chart_labels.append(day_dt.strftime("%b %d"))
            chart_values.append(round(day_sum, 2))

        # Top Employees (All-time and This Month ranking for CEO & Manager)
        top_employees = []
        if user.can_view_all_sales:
            emp_stats = (
                db.session.query(
                    User.name,
                    func.count(Sale.id).label("sales_count"),
                    func.sum(Sale.total).label("total_revenue")
                )
                .join(Sale, User.id == Sale.employee_id)
                .group_by(User.id)
                .order_by(func.sum(Sale.total).desc())
                .limit(5)
                .all()
            )
            for name, count, rev in emp_stats:
                top_employees.append({
                    "name": name,
                    "count": count,
                    "revenue": round(rev or 0.0, 2)
                })

        return {
            "today_total": today_total,
            "today_count": today_count,
            "today_collected": today_collected,
            "week_total": week_total,
            "week_collected": week_collected,
            "month_total": month_total,
            "month_collected": month_collected,
            "total_unpaid": total_unpaid,
            "unpaid_count": len(unpaid_sales),
            "recent_unpaid": unpaid_sales[:8],
            "recent_sales": all_sales[:8],
            "chart_labels": chart_labels,
            "chart_values": chart_values,
            "top_employees": top_employees,
        }
