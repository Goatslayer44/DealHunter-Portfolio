import re


def match_product(title):
    """Identify a product using its title."""

    title = title.upper()

    # Look for an example model number
    model = re.search(r"\bZ930M\b", title)

    if model:
        return {
            "model": "Z930M",
            "category": "LAWN MOWER PART"
        }

    # Look for common product categories
    if "LAPTOP" in title:
        return {
            "model": "UNKNOWN",
            "category": "COMPUTER"
        }

    if "CONTROLLER" in title:
        return {
            "model": "UNKNOWN",
            "category": "GAMING ACCESSORY"
        }

    return {
        "model": "UNKNOWN",
        "category": "OTHER"
    }


if __name__ == "__main__":
    examples = [
        "John Deere Z930M Mower Part",
        "Used Gaming Controller",
        "Dell Laptop Computer",
        "Unknown Product"
    ]

    for product in examples:
        result = match_product(product)
        print(f"\nProduct: {product}")
        print(f"Model: {result['model']}")
        print(f"Category: {result['category']}")