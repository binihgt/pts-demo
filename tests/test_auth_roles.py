from app.models.user import User
from app.models.sale import Sale
from app.extensions import db


def test_login_page_renders(client):
    """Ensure the login page loads with HTTP 200."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"PTS Demo" in response.data
    assert b"Sign In to Dashboard" in response.data


def test_login_success_and_logout(client, auth_client):
    """Test successful authentication and subsequent logout."""
    res = auth_client.login("ceo_test", "CeoPassword123!")
    assert res.status_code == 200
    assert b"Welcome back, Test CEO!" in res.data

    logout_res = auth_client.logout()
    assert logout_res.status_code == 200
    assert b"You have been signed out safely." in logout_res.data


def test_login_invalid_credentials(client, auth_client):
    """Test rejection on bad password."""
    res = auth_client.login("ceo_test", "WrongPassword!")
    assert res.status_code == 200
    assert b"Invalid username or password" in res.data


def test_login_deactivated_user_blocked(client, auth_client):
    """Test that deactivated accounts cannot log in."""
    res = auth_client.login("disabled_test", "DisabledPassword123!")
    assert res.status_code == 200
    assert b"Your account is currently disabled" in res.data


def test_role_permissions_employees_management(client, auth_client):
    """
    CEO can access /employees/
    Manager and Employee must be denied (403 Forbidden).
    """
    # 1. Unauthenticated -> Redirect to login
    res = client.get("/employees/")
    assert res.status_code == 302
    assert "/auth/login" in res.headers["Location"]

    # 2. CEO -> 200 OK
    auth_client.login("ceo_test", "CeoPassword123!")
    res_ceo = client.get("/employees/")
    assert res_ceo.status_code == 200
    assert b"Team & Telegram Management" in res_ceo.data
    auth_client.logout()

    # 3. Manager -> 403 Forbidden
    auth_client.login("mgr_test", "MgrPassword123!")
    res_mgr = client.get("/employees/")
    assert res_mgr.status_code == 403
    auth_client.logout()

    # 4. Employee -> 403 Forbidden
    auth_client.login("emp_test", "EmpPassword123!")
    res_emp = client.get("/employees/")
    assert res_emp.status_code == 403
    auth_client.logout()


def test_role_permissions_audit_logs(client, auth_client):
    """Audit logs are strictly reserved for the CEO."""
    auth_client.login("mgr_test", "MgrPassword123!")
    res_mgr = client.get("/audit/")
    assert res_mgr.status_code == 403
    auth_client.logout()

    auth_client.login("ceo_test", "CeoPassword123!")
    res_ceo = client.get("/audit/")
    assert res_ceo.status_code == 200
    assert b"System Audit Trail" in res_ceo.data
    auth_client.logout()


def test_role_permissions_reports(client, auth_client):
    """Both CEO and Manager can access reports; Employee cannot."""
    # Employee -> 403
    auth_client.login("emp_test", "EmpPassword123!")
    res_emp = client.get("/reports/")
    assert res_emp.status_code == 403
    auth_client.logout()

    # Manager -> 200
    auth_client.login("mgr_test", "MgrPassword123!")
    res_mgr = client.get("/reports/")
    assert res_mgr.status_code == 200
    assert b"Export Excel Reports" in res_mgr.data
    auth_client.logout()

    # CEO -> 200
    auth_client.login("ceo_test", "CeoPassword123!")
    res_ceo = client.get("/reports/")
    assert res_ceo.status_code == 200
    auth_client.logout()


def test_employee_isolation_on_sales_view(app, client, auth_client):
    """Employees should only see their own recorded sales."""
    with app.app_context():
        ceo = User.query.filter_by(username="ceo_test").first()
        emp = User.query.filter_by(username="emp_test").first()

        # Create a sale for CEO
        sale_ceo = Sale(
            employee_id=ceo.id,
            item="Secret CEO Enterprise Server",
            quantity=1,
            unit_price=100000.0,
            total=100000.0
        )
        # Create a sale for Employee
        sale_emp = Sale(
            employee_id=emp.id,
            item="Employee Basic USB Cable",
            quantity=2,
            unit_price=250.0,
            total=500.0
        )
        db.session.add_all([sale_ceo, sale_emp])
        db.session.commit()

    # Log in as Employee: should see their own sale, but NOT CEO's sale
    auth_client.login("emp_test", "EmpPassword123!")
    res = client.get("/sales/")
    assert res.status_code == 200
    assert b"Employee Basic USB Cable" in res.data
    assert b"Secret CEO Enterprise Server" not in res.data
    auth_client.logout()

    # Log in as CEO: should see BOTH sales
    auth_client.login("ceo_test", "CeoPassword123!")
    res = client.get("/sales/")
    assert res.status_code == 200
    assert b"Employee Basic USB Cable" in res.data
    assert b"Secret CEO Enterprise Server" in res.data
    auth_client.logout()
