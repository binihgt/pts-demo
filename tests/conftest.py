import pytest
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.customer import Customer
from app.models.sale import Sale
from app.models.payment import Payment


@pytest.fixture
def app():
    """Create and configure a new app instance for each test with in-memory DB."""
    app = create_app(config_name="testing")
    with app.app_context():
        db.create_all()

        # Seed standard users for test scenarios
        ceo = User(name="Test CEO", username="ceo_test", role=User.ROLE_CEO, is_active=True)
        ceo.set_password("CeoPassword123!")

        manager = User(name="Test Manager", username="mgr_test", role=User.ROLE_MANAGER, is_active=True)
        manager.set_password("MgrPassword123!")

        employee = User(name="Test Employee", username="emp_test", role=User.ROLE_EMPLOYEE, is_active=True)
        employee.set_password("EmpPassword123!")

        disabled = User(name="Disabled User", username="disabled_test", role=User.ROLE_EMPLOYEE, is_active=False)
        disabled.set_password("DisabledPassword123!")

        db.session.add_all([ceo, manager, employee, disabled])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Helper class to log in as different roles."""
    class AuthActions:
        def login(self, username="ceo_test", password="CeoPassword123!"):
            return client.post("/auth/login", data={"username": username, "password": password}, follow_redirects=True)

        def logout(self):
            return client.get("/auth/logout", follow_redirects=True)

    return AuthActions()
