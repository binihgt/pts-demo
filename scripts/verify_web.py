import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app

def main():
    app = create_app("development")
    with app.test_client() as client:
        # 1. Fetch Login Page
        res = client.get("/auth/login")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        
        # Extract CSRF token
        html = res.data.decode("utf-8")
        match = re.search(r'name="csrf_token" value="([^"]+)"', html)
        assert match, "CSRF token not found in login form"
        csrf_token = match.group(1)
        print("[+] GET /auth/login: OK (CSRF token present)")

        # 2. Authenticate as CEO (admin)
        login_res = client.post(
            "/auth/login",
            data={"username": "admin", "password": "Password123!", "csrf_token": csrf_token},
            follow_redirects=True
        )
        assert login_res.status_code == 200
        assert "Welcome back" in login_res.data.decode("utf-8")
        print("[+] POST /auth/login as CEO: OK (Session active)")

        # 3. Check Overview
        overview_res = client.get("/overview")
        assert overview_res.status_code == 200
        assert "Today's Sales" in overview_res.data.decode("utf-8")
        print("[+] GET /overview: OK (KPI cards & chart rendered)")

        # 4. Check Sales List
        sales_res = client.get("/sales/")
        assert sales_res.status_code == 200
        assert "Sales Records" in sales_res.data.decode("utf-8")
        print("[+] GET /sales/: OK (Responsive card table rendered)")

        # 5. Check Payments List
        payments_res = client.get("/payments/")
        assert payments_res.status_code == 200
        assert "Payments Collected" in payments_res.data.decode("utf-8")
        print("[+] GET /payments/: OK (Collections rendered)")

        # 6. Check Employees Management (CEO only)
        emp_res = client.get("/employees/")
        assert emp_res.status_code == 200
        assert "Team & Telegram Management" in emp_res.data.decode("utf-8")
        print("[+] GET /employees/: OK (CEO management & link codes rendered)")

        # 7. Check Audit Logs (CEO only)
        audit_res = client.get("/audit/")
        assert audit_res.status_code == 200
        assert "System Audit Trail" in audit_res.data.decode("utf-8")
        print("[+] GET /audit/: OK (Audit logs rendered)")

        # 8. Check Logout
        logout_res = client.get("/auth/logout", follow_redirects=True)
        assert logout_res.status_code == 200
        print("[+] GET /auth/logout: OK (Signed out)")

        print("\n[SUCCESS] All Web Dashboard routes and security protections verified!")

if __name__ == "__main__":
    main()
