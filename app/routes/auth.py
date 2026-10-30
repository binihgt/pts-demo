from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import limiter, db
from app.forms.auth_forms import LoginForm
from app.models.user import User
from app.models.audit import AuditLog

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    """Sign-in route with brute-force rate limiting and CSRF protection."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.overview"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        password = form.password.data
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                AuditLog.log("LOGIN_BLOCKED", user_id=user.id, details="Attempted login on deactivated account.")
                db.session.commit()
                flash("Your account is currently disabled. Please contact your CEO.", "danger")
                return render_template("auth/login.html", form=form)

            login_user(user, remember=False)
            AuditLog.log("LOGIN_SUCCESS", user_id=user.id, details=f"User '{user.username}' logged in via web dashboard.")
            db.session.commit()

            next_page = request.args.get("next")
            # Ensure next_page is safe (relative URL)
            if not next_page or not next_page.startswith("/"):
                next_page = url_for("dashboard.overview")
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(next_page)
        else:
            AuditLog.log("LOGIN_FAILED", details=f"Failed login attempt for username '{username}' from {request.remote_addr}.")
            db.session.commit()
            flash("Invalid username or password. Please try again.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout current user and record audit log."""
    user_id = current_user.id
    username = current_user.username
    logout_user()
    AuditLog.log("LOGOUT", user_id=user_id, details=f"User '{username}' logged out.")
    db.session.commit()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("auth.login"))
