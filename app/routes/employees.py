from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.extensions import db
from app.models.user import User
from app.models.audit import AuditLog
from app.utils.decorators import ceo_required
from app.forms.employee_forms import EmployeeCreateForm, EmployeePasswordResetForm

employees_bp = Blueprint("employees", __name__, url_prefix="/employees")


@employees_bp.route("/", methods=["GET"])
@ceo_required
def index():
    """CEO-only: List and manage company employees."""
    users = User.query.order_by(User.role, User.name).all()
    create_form = EmployeeCreateForm()
    reset_form = EmployeePasswordResetForm()
    return render_template(
        "employees/index.html",
        users=users,
        create_form=create_form,
        reset_form=reset_form
    )


@employees_bp.route("/create", methods=["POST"])
@ceo_required
def create():
    """CEO-only: Create a new employee, manager, or CEO."""
    form = EmployeeCreateForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        if User.query.filter_by(username=username).first():
            flash(f"Username '{username}' is already taken. Please choose another.", "danger")
            return redirect(url_for("employees.index"))

        new_user = User(
            name=form.name.data.strip(),
            username=username,
            role=form.role.data,
            is_active=True
        )
        new_user.set_password(form.password.data)
        # Automatically generate a Telegram link code for immediate use
        code = new_user.generate_telegram_link_code()

        db.session.add(new_user)
        db.session.flush()

        AuditLog.log(
            action="USER_CREATED",
            user_id=current_user.id,
            details=f"CEO {current_user.username} created new user '{new_user.username}' with role '{new_user.role}'."
        )
        db.session.commit()

        flash(
            f"User '{new_user.name}' ({new_user.username}) created! Telegram link code: {code}",
            "success"
        )
        return redirect(url_for("employees.index"))

    for err_list in form.errors.values():
        for err in err_list:
            flash(err, "danger")
    return redirect(url_for("employees.index"))


@employees_bp.route("/toggle-status/<int:user_id>", methods=["POST"])
@ceo_required
def toggle_status(user_id: int):
    """CEO-only: Activate or deactivate a user account."""
    if user_id == current_user.id:
        flash("You cannot deactivate your own CEO account.", "warning")
        return redirect(url_for("employees.index"))

    target_user = User.query.get_or_404(user_id)
    target_user.is_active = not target_user.is_active
    status_str = "activated" if target_user.is_active else "deactivated"

    AuditLog.log(
        action="USER_STATUS_CHANGED",
        user_id=current_user.id,
        details=f"User '{target_user.username}' {status_str} by CEO {current_user.username}."
    )
    db.session.commit()
    flash(f"User '{target_user.name}' has been {status_str}.", "info")
    return redirect(url_for("employees.index"))


@employees_bp.route("/reset-password/<int:user_id>", methods=["POST"])
@ceo_required
def reset_password(user_id: int):
    """CEO-only: Reset an employee's password."""
    form = EmployeePasswordResetForm()
    if form.validate_on_submit():
        target_user = User.query.get_or_404(user_id)
        target_user.set_password(form.new_password.data)

        AuditLog.log(
            action="PASSWORD_RESET",
            user_id=current_user.id,
            details=f"Password for user '{target_user.username}' reset by CEO {current_user.username}."
        )
        db.session.commit()
        flash(f"Password for '{target_user.name}' reset successfully.", "success")
    else:
        for err_list in form.errors.values():
            for err in err_list:
                flash(err, "danger")
    return redirect(url_for("employees.index"))


@employees_bp.route("/generate-link-code/<int:user_id>", methods=["POST"])
@ceo_required
def generate_link_code(user_id: int):
    """CEO-only: Generate a one-time Telegram pairing link code."""
    target_user = User.query.get_or_404(user_id)
    code = target_user.generate_telegram_link_code()

    AuditLog.log(
        action="LINK_CODE_GENERATED",
        user_id=current_user.id,
        details=f"One-time Telegram link code generated for user '{target_user.username}'."
    )
    db.session.commit()
    flash(f"Telegram link code for '{target_user.name}' is: {code} (Send to employee)", "success")
    return redirect(url_for("employees.index"))


@employees_bp.route("/unlink-telegram/<int:user_id>", methods=["POST"])
@ceo_required
def unlink_telegram(user_id: int):
    """CEO-only: Unlink an employee's Telegram account."""
    target_user = User.query.get_or_404(user_id)
    old_tg_id = target_user.telegram_id
    target_user.telegram_id = None

    AuditLog.log(
        action="TELEGRAM_UNLINKED",
        user_id=current_user.id,
        details=f"Telegram ID {old_tg_id} unlinked from user '{target_user.username}'."
    )
    db.session.commit()
    flash(f"Telegram account unlinked for '{target_user.name}'.", "info")
    return redirect(url_for("employees.index"))
