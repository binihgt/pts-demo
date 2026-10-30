import re
from datetime import datetime, timezone, timedelta
from typing import Any

# East Africa Time (UTC+3)
EAT = timezone(timedelta(hours=3), name="EAT")


def format_money(amount: Any) -> str:
    """Format any numeric value into standard ETB currency display: '225,000.00 ETB'."""
    try:
        val = float(amount or 0.0)
        return f"{val:,.2f} ETB"
    except (ValueError, TypeError):
        return "0.00 ETB"


def to_eat_datetime(dt: datetime | None) -> datetime | None:
    """Convert any UTC or naive datetime to Africa/Addis_Ababa (EAT, UTC+3)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume stored as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(EAT)


def format_eat_datetime(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime into East Africa Time string."""
    eat_dt = to_eat_datetime(dt)
    if not eat_dt:
        return "-"
    return eat_dt.strftime(fmt)


def normalize_ethiopian_phone(phone: str | None) -> str | None:
    """
    Validate and normalize Ethiopian phone numbers to international format: +2519XXXXXXXX or +2517XXXXXXXX.
    Accepts:
        - 09XXXXXXXX, 9XXXXXXXX, +2519XXXXXXXX, 2519XXXXXXXX (Ethio Telecom)
        - 07XXXXXXXX, 7XXXXXXXX, +2517XXXXXXXX, 2517XXXXXXXX (Safaricom Ethiopia)
    Returns:
        Normalized phone string (e.g. '+251911223344') or None if input is empty.
    Raises:
        ValueError: If phone is provided but does not match valid Ethiopian mobile pattern.
    """
    if not phone or not phone.strip():
        return None

    # Strip whitespace, hyphens, dots, parentheses
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone.strip())

    # Match patterns:
    # 1. +251[79]\d{8}
    if re.fullmatch(r"\+251[79]\d{8}", cleaned):
        return cleaned

    # 2. 251[79]\d{8}
    if re.fullmatch(r"251[79]\d{8}", cleaned):
        return f"+{cleaned}"

    # 3. 0[79]\d{8}
    if re.fullmatch(r"0[79]\d{8}", cleaned):
        return f"+251{cleaned[1:]}"

    # 4. [79]\d{8}
    if re.fullmatch(r"[79]\d{8}", cleaned):
        return f"+251{cleaned}"

    raise ValueError(
        "Invalid phone number. Please enter a valid Ethiopian mobile number "
        "(e.g., 0911223344, 0711223344, or +251911223344)."
    )


def validate_product_name(item: str | None) -> str:
    """
    Validate item name:
        - Required, trimmed
        - Maximum 100 characters
        - No newlines allowed (reject multi-line pasted text)
    """
    if not item or not item.strip():
        raise ValueError("Product name is required.")

    trimmed = item.strip()

    if "\n" in trimmed or "\r" in trimmed:
        raise ValueError(
            "Product name cannot contain multiple lines. Please enter a single-line product name."
        )

    if len(trimmed) > 100:
        raise ValueError(
            f"Product name is too long ({len(trimmed)} characters). Maximum allowed is 100 characters."
        )

    return trimmed
