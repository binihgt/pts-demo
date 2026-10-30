from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length
from app.models.user import User


class EmployeeCreateForm(FlaskForm):
    """Form for CEO to create a new employee or manager."""
    name = StringField(
        "Full Name",
        validators=[DataRequired(message="Full name is required."), Length(min=2, max=100)],
        render_kw={"placeholder": "e.g. Dawit Haile"}
    )
    username = StringField(
        "Username",
        validators=[DataRequired(message="Username is required."), Length(min=3, max=80)],
        render_kw={"placeholder": "e.g. dawit"}
    )
    password = PasswordField(
        "Initial Password",
        validators=[DataRequired(message="Password is required."), Length(min=8, max=100)],
        render_kw={"placeholder": "Minimum 8 characters"}
    )
    role = SelectField(
        "Role",
        choices=[
            (User.ROLE_EMPLOYEE, "Employee (Sales only)"),
            (User.ROLE_MANAGER, "Manager (Reports & All Sales)"),
            (User.ROLE_CEO, "CEO (Full Administrative Access)"),
        ],
        default=User.ROLE_EMPLOYEE,
        validators=[DataRequired()]
    )
    submit = SubmitField("Add Team Member")


class EmployeePasswordResetForm(FlaskForm):
    """Form for CEO to reset an employee's password."""
    new_password = PasswordField(
        "New Password",
        validators=[DataRequired(message="New password is required."), Length(min=8, max=100)],
        render_kw={"placeholder": "Minimum 8 characters"}
    )
    submit = SubmitField("Reset Password")
