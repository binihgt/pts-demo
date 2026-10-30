import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    """User model with role-based access control and Telegram account linking."""
    __tablename__ = "users"

    ROLE_CEO = "ceo"
    ROLE_MANAGER = "manager"
    ROLE_EMPLOYEE = "employee"
    VALID_ROLES = (ROLE_CEO, ROLE_MANAGER, ROLE_EMPLOYEE)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_EMPLOYEE)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True, index=True)
    telegram_link_code = db.Column(db.String(32), unique=True, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    sales = db.relationship("Sale", back_populates="employee", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the user's password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_ceo(self) -> bool:
        return self.role == self.ROLE_CEO

    @property
    def is_manager(self) -> bool:
        return self.role == self.ROLE_MANAGER

    @property
    def is_employee(self) -> bool:
        return self.role == self.ROLE_EMPLOYEE

    @property
    def can_view_all_sales(self) -> bool:
        """CEOs and Managers can view company-wide sales."""
        return self.role in (self.ROLE_CEO, self.ROLE_MANAGER)

    def generate_telegram_link_code(self) -> str:
        """Generate a secure, human-friendly 8-character one-time link code."""
        code = secrets.token_hex(4).upper()  # e.g., 'A1B2C3D4'
        self.telegram_link_code = code
        return code

    def clear_telegram_link_code(self) -> None:
        """Invalidate the one-time link code after successful Telegram pairing."""
        self.telegram_link_code = None

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"
