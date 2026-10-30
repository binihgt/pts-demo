from datetime import datetime, timedelta, timezone
import io
import openpyxl
from app.services.report_service import ReportService
from app.models.user import User
from app.models.customer import Customer
from app.models.sale import Sale
from app.models.payment import Payment
from app.extensions import db


def test_generate_excel_report_structure_and_sheets(app):
    """Test that openpyxl generates Summary, Sales, and Payments sheets with correct data."""
    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()
        cust = Customer(name="Yonas Girma", phone="+251911998877")
        db.session.add(cust)
        db.session.flush()

        sale = Sale(
            employee_id=emp.id,
            customer_id=cust.id,
            item="Cisco 24-Port Gigabit Switch",
            quantity=2,
            unit_price=19500.0,
            total=39000.0,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(sale)
        db.session.flush()

        payment = Payment(
            sale_id=sale.id,
            amount=39000.0,
            method="telebirr",
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(payment)
        db.session.commit()

        # Generate report
        buffer, filename = ReportService.generate_excel_report()
        assert filename.startswith("pts_report_")
        assert filename.endswith(".xlsx")

        # Load and inspect with openpyxl
        wb = openpyxl.load_workbook(buffer)
        sheet_names = wb.sheetnames
        assert "Summary" in sheet_names
        assert "Sales" in sheet_names
        assert "Payments" in sheet_names

        # Inspect Summary
        ws_summary = wb["Summary"]
        assert ws_summary["A1"].value == "PTS Demo - Business Executive Report"

        # Inspect Sales
        ws_sales = wb["Sales"]
        assert ws_sales["A1"].value == "Invoice #"
        assert ws_sales["F1"].value == "Item Description"
        assert ws_sales["I1"].value == "Total (ETB)"

        # Check that our sale item is in the rows
        items_found = [ws_sales.cell(row=r, column=6).value for r in range(2, ws_sales.max_row + 1)]
        assert "Cisco 24-Port Gigabit Switch" in items_found

        # Inspect Payments
        ws_payments = wb["Payments"]
        assert ws_payments["A1"].value == "Receipt #"
        assert ws_payments["F1"].value == "Amount (ETB)"
        assert ws_payments["G1"].value == "Payment Method"

        methods_found = [ws_payments.cell(row=r, column=7).value for r in range(2, ws_payments.max_row + 1)]
        assert "Telebirr" in methods_found


def test_generate_excel_report_date_filtering(app):
    """Test date range filtering in Excel generation."""
    with app.app_context():
        emp = User.query.filter_by(username="emp_test").first()
        now = datetime.now(timezone.utc)

        # Old sale (30 days ago)
        old_sale = Sale(
            employee_id=emp.id,
            item="Old Item 30 Days Ago",
            quantity=1,
            unit_price=100.0,
            total=100.0,
            created_at=now - timedelta(days=30)
        )
        # Recent sale (Today)
        recent_sale = Sale(
            employee_id=emp.id,
            item="Recent Item Today",
            quantity=1,
            unit_price=500.0,
            total=500.0,
            created_at=now
        )
        db.session.add_all([old_sale, recent_sale])
        db.session.commit()

        # Filter strictly for today
        today_str = now.strftime("%Y-%m-%d")
        buffer, _ = ReportService.generate_excel_report(start_date=today_str, end_date=today_str)

        wb = openpyxl.load_workbook(buffer)
        ws_sales = wb["Sales"]

        items = [ws_sales.cell(row=r, column=6).value for r in range(2, ws_sales.max_row + 1)]
        assert "Recent Item Today" in items
        assert "Old Item 30 Days Ago" not in items


def test_reports_web_download_endpoint(client, auth_client):
    """Test web endpoint /reports/download with authorization guards."""
    # 1. Unauthenticated -> 302 redirect to login
    res = client.get("/reports/download")
    assert res.status_code == 302

    # 2. Employee -> 403 Forbidden
    auth_client.login("emp_test", "EmpPassword123!")
    res_emp = client.get("/reports/download")
    assert res_emp.status_code == 403
    auth_client.logout()

    # 3. Manager -> 200 OK with excel content-type
    auth_client.login("mgr_test", "MgrPassword123!")
    res_mgr = client.get("/reports/download")
    assert res_mgr.status_code == 200
    assert "spreadsheetml.sheet" in res_mgr.content_type
    assert "pts_report_" in res_mgr.headers.get("Content-Disposition", "")
    auth_client.logout()

    # 4. CEO -> 200 OK
    auth_client.login("ceo_test", "CeoPassword123!")
    res_ceo = client.get("/reports/download")
    assert res_ceo.status_code == 200
    assert "spreadsheetml.sheet" in res_ceo.content_type
    auth_client.logout()
