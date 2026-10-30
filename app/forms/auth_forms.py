from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    """Secure login form with CSRF token and length constraints."""
    username = StringField(
        "Username",
        validators=[DataRequired(message="Username is required."), Length(min=3, max=80)],
        render_kw={
            "placeholder": "e.g. admin or alemu",
            "autocomplete": "username",
            "autocapitalize": "none",
            "autocorrect": "off",
            "spellcheck": "false",
            "autofocus": True,
        }
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")],
        render_kw={"placeholder": "••••••••", "autocomplete": "current-password"}
    )
    submit = SubmitField("Sign In")
