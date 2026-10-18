from utils.logger import log_info


class BaseDiscountRule:
    """Base rule for discount computation."""

    def get_max_discount(self) -> float:
        """Return maximum allowable discount."""
        return 50.0


class PercentageDiscountRule(BaseDiscountRule):
    """Percentage discount rule inheriting from BaseDiscountRule."""

    def calculate_percentage_discount(self, subtotal: float, percent: float = 0.10) -> float:
        """Calculate discount amount capped at maximum limit."""
        log_info(f"Applying {percent * 100}% discount on {subtotal}")
        discount = subtotal * percent
        max_discount = self.get_max_discount()
        return min(discount, max_discount)


def calculate_discount(subtotal: float) -> float:
    """Standalone helper function to calculate standard discount."""
    rule = PercentageDiscountRule()
    return rule.calculate_percentage_discount(subtotal, 0.15)
