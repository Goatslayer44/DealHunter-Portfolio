"""Identify a product's model and category from its title using simple rules."""
import re

MAX_TITLE_LENGTH = 200


def validate_title(title):
    """Return a cleaned title, or raise TypeError/ValueError if it is unusable."""
    if not isinstance(title, str):
        raise TypeError(f"title must be a string, got {type(title).__name__}")
    title = title.strip()
    if not title:
        raise ValueError("title cannot be empty")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"title cannot exceed {MAX_TITLE_LENGTH} characters")
    return title


def match_product(title):
    """Return a dict with the product's "model" and "category".

    Matching is case-insensitive and rule-based (no AI or live data).
    """
    title = validate_title(title).upper()

    # Look for an example model number
    if re.search(r"\bZ930M\b", title):
        return {"model": "Z930M", "category": "LAWN MOWER PART"}

    # Look for common product categories
    if "LAPTOP" in title:
        return {"model": "UNKNOWN", "category": "COMPUTER"}

    if "CONTROLLER" in title:
        return {"model": "UNKNOWN", "category": "GAMING ACCESSORY"}

    return {"model": "UNKNOWN", "category": "OTHER"}


if __name__ == "__main__":
    examples = [
        "John Deere Z930M Mower Part",
        "Used Gaming Controller",
        "Dell Laptop Computer",
        "Unknown Product",
    ]

    for product in examples:
        result = match_product(product)
        print(f"\nProduct: {product}")
        print(f"Model: {result['model']}")
        print(f"Category: {result['category']}")
