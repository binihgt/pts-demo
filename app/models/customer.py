from datetime import datetime, timezone
from app.extensions import db


class Customer(db.Model):
    """Customer entity who purchases items."""
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(40), nullable=True, index=True)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    sales = db.relationship("Sale", back_populates="customer", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name='{self.name}'>"
