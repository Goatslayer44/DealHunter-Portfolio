"""Estimate resale profit from purchase price, shipping, and fees.

All prices in this portfolio project are fictional sample values.
"""
import math
from numbers import Real

PROFITABLE_THRESHOLD = 100  # Minimum profit (in dollars) to call a deal worthwhile.


def _validate_amount(name, value):
    """Return value if it is a finite, non-negative number; otherwise raise."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if value < 0:
        raise ValueError(f"{name} cannot be negative")
    return value


def calculate_profit(buy_price, sell_price, shipping, fees):
    """Return sell_price minus (buy_price + shipping + fees).

    Raises TypeError for non-numeric input and ValueError for negative,
    NaN, or infinite values. A negative result means a loss.
    """
    buy_price = _validate_amount("buy_price", buy_price)
    sell_price = _validate_amount("sell_price", sell_price)
    shipping = _validate_amount("shipping", shipping)
    fees = _validate_amount("fees", fees)

    total_cost = buy_price + shipping + fees
    return sell_price - total_cost


def is_profitable(profit, threshold=PROFITABLE_THRESHOLD):
    """Return True when profit meets the threshold."""
    return profit >= threshold


def main():
    # Fictional product example
    buy_price = 150
    sell_price = 400
    shipping = 20
    fees = 50

    profit = calculate_profit(buy_price, sell_price, shipping, fees)

    print("DEALHUNTER PORTFOLIO")
    print("--------------------")
    print(f"Purchase Price: ${buy_price:.2f}")
    print(f"Resale Price:   ${sell_price:.2f}")
    print(f"Shipping:       ${shipping:.2f}")
    print(f"Fees:           ${fees:.2f}")
    print(f"Expected Profit: ${profit:.2f}")

    if is_profitable(profit):
        print("Decision: PROFITABLE DEAL")
    else:
        print("Decision: SKIP")


if __name__ == "__main__":
    main()
