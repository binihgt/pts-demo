from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional, ValidationError
from app.models.payment import Payment
from app.utils.formatting import validate_product_name, normalize_ethiopian_phone


class SaleForm(FlaskForm):
    """Form to record a new sale."""
    item = StringField(
        "Item Name / Description",
        validators=[DataRequired(message="Item name is required."), Length(max=100)],
        render_kw={"placeholder": "e.g. Dell Latitude 5420 Laptop", "maxlength": 100}
    )
    quantity = IntegerField(
        "Quantity",
        default=1,
        validators=[DataRequired(message="Quantity is required."), NumberRange(min=1, max=10000)],
        render_kw={"min": 1, "step": 1}
    )
    unit_price = DecimalField(
        "Unit Price (ETB)",
        places=2,
        validators=[DataRequired(message="Unit price is required."), NumberRange(min=0.01)],
        render_kw={"placeholder": "0.00", "step": "0.01"}
    )
    customer_name = StringField(
        "Customer Name",
        validators=[Optional(), Length(max=120)],
        render_kw={"placeholder": "Optional customer name"}
    )
    customer_phone = StringField(
        "Customer Phone",
        validators=[Optional(), Length(max=40)],
        render_kw={"placeholder": "e.g. 0911223344 or +251911223344"}
    )
    submit = SubmitField("Record Sale")

    def validate_item(self, field):
        try:
            field.data = validate_product_name(field.data)
        except ValueError as e:
            raise ValidationError(str(e))

    def validate_customer_phone(self, field):
        if field.data and field.data.strip():
            try:
                field.data = normalize_ethiopian_phone(field.data)
            except ValueError as e:
                raise ValidationError(str(e))


class PaymentForm(FlaskForm):
    """Form to record a payment against an existing sale."""
    amount = DecimalField(
        "Payment Amount (ETB)",
        places=2,
        validators=[DataRequired(message="Payment amount is required."), NumberRange(min=0.01)],
        render_kw={"placeholder": "0.00", "step": "0.01"}
    )
    method = SelectField(
        "Payment Method",
        choices=[
            (Payment.METHOD_TELEBIRR, "Telebirr"),
            (Payment.METHOD_BANK, "Bank Transfer / CBE"),
            (Payment.METHOD_CASH, "Cash"),
        ],
        validators=[DataRequired(message="Payment method is required.")]
    )
    submit = SubmitField("Record Payment")
