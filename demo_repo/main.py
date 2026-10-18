from utils.logger import log_info
from services.order_service import OrderService


def post_checkout_endpoint(payload: dict) -> dict:
    """Main API endpoint simulating an order checkout request."""
    log_info("Received checkout request")
    service = OrderService()
    order_id = payload.get("order_id", "demo-123")
    items = payload.get("items", [])
    token = payload.get("card_token", "tok_demo")
    return service.checkout_order(order_id, items, token)


if __name__ == "__main__":
    sample_order = {
        "order_id": "ORD-1001",
        "items": [{"name": "Mechanical Keyboard", "price": 120.0, "quantity": 1}],
        "card_token": "tok_visa_4242",
    }
    result = post_checkout_endpoint(sample_order)
    print("Demo order result:", result)
