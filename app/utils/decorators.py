from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from app.models.user import User


def role_required(*allowed_roles):
    """Decorator to restrict view access to specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not current_user.is_active:
                flash("Your account has been deactivated. Please contact your CEO.", "danger")
                return redirect(url_for("auth.logout"))
            if current_user.role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def ceo_required(f):
    """Restrict access strictly to the CEO."""
    return role_required(User.ROLE_CEO)(f)


def manager_or_ceo_required(f):
    """Restrict access to Managers and CEOs."""
    return role_required(User.ROLE_CEO, User.ROLE_MANAGER)(f)
