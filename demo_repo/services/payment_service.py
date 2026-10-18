from utils.logger import log_info, log_error


def charge_credit_card(amount: float, card_token: str) -> bool:
    """Simulates communication with an external payment gateway."""
    log_info(f"Charging {amount} with token {card_token}")
    return True


def process_order_payment(amount: float, card_token: str) -> bool:
    """Validates and triggers payment charging."""
    if amount <= 0:
        log_error("Payment amount must be greater than zero")
        return False
    return charge_credit_card(amount, card_token)
