from datetime import datetime, timezone
from app.extensions import db


class Sale(db.Model):
    """Sale transaction recorded by an employee."""
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    item = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    employee = db.relationship("User", back_populates="sales")
    customer = db.relationship("Customer", back_populates="sales")
    payments = db.relationship(
        "Payment",
        back_populates="sale",
        cascade="all, delete-orphan",
        order_by="Payment.created_at.desc()"
    )

    @property
    def total_paid(self) -> float:
        """Sum of all payments made for this sale."""
        return round(sum(p.amount for p in self.payments), 2)

    @property
    def balance(self) -> float:
        """Remaining unpaid balance for this sale."""
        rem = self.total - self.total_paid
        return round(max(0.0, rem), 2)

    @property
    def payment_status(self) -> str:
        """Payment status badge helper."""
        paid = self.total_paid
        if paid >= self.total and self.total > 0:
            return "paid"
        if paid > 0:
            return "partial"
        return "unpaid"

    def __repr__(self) -> str:
        return f"<Sale id={self.id} item='{self.item}' total={self.total}>"
