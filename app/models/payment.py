from datetime import datetime, timezone
from app.extensions import db


class Payment(db.Model):
    """Payment recorded against a sale."""
    __tablename__ = "payments"

    METHOD_CASH = "cash"
    METHOD_TELEBIRR = "telebirr"
    METHOD_BANK = "bank"
    VALID_METHODS = (METHOD_CASH, METHOD_TELEBIRR, METHOD_BANK)

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20), nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    sale = db.relationship("Sale", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} sale_id={self.sale_id} amount={self.amount} method='{self.method}'>"
