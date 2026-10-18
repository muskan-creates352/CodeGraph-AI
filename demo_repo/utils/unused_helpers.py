def legacy_format_currency(amount: float) -> str:
    """Intentionally unused legacy helper for formatting currency."""
    return f"${amount:,.2f}"


def calculate_vat_deprecated(amount: float, rate: float = 0.20) -> float:
    """Intentionally unused deprecated calculation."""
    return amount * rate
