from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    """Audit log tracking critical business actions and security events."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    user = db.relationship("User", back_populates="audit_logs")

    @classmethod
    def log(cls, action: str, user_id: int | None = None, details: str | None = None) -> "AuditLog":
        """Helper to create and stage an audit log entry."""
        entry = cls(action=action, user_id=user_id, details=details)
        db.session.add(entry)
        return entry

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action='{self.action}' user_id={self.user_id}>"
