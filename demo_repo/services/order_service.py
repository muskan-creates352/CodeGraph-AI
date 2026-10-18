from utils.logger import log_info
from services.discount_service import calculate_discount
from services.payment_service import process_order_payment


class OrderService:
    """Manages order placement, pricing, and fulfillment."""

    def validate_cart(self, items: list) -> bool:
        """Ensure the order contains at least one item."""
        return len(items) > 0

    def calculate_order_total(self, items: list) -> float:
        """Compute the final order total after applying discounts."""
        subtotal = sum(item.get("price", 0.0) * item.get("quantity", 1) for item in items)
        discount = calculate_discount(subtotal)
        return max(0.0, subtotal - discount)

    def checkout_order(self, order_id: str, items: list, card_token: str) -> dict:
        """Execute complete checkout flow: validate, calculate, and charge."""
        log_info(f"Beginning checkout for order {order_id}")
        if not self.validate_cart(items):
            return {"status": "rejected", "reason": "empty_cart"}

        total = self.calculate_order_total(items)
        payment_success = process_order_payment(total, card_token)

        return {
            "order_id": order_id,
            "total": total,
            "status": "paid" if payment_success else "payment_failed",
        }
