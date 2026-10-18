import sqlite3
from contextlib import closing

from profit_calculator import calculate_profit
from product_matcher import match_product

DATABASE_NAME = "portfolio.db"


def create_database():
    with closing(sqlite3.connect(DATABASE_NAME)) as conn:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    model TEXT,
                    category TEXT,
                    buy_price REAL,
                    sell_price REAL,
                    expected_profit REAL
                )
            """)


def save_product(title, buy_price, sell_price, shipping, fees):
    product = match_product(title)

    profit = calculate_profit(
        buy_price, sell_price, shipping, fees
    )

    with closing(sqlite3.connect(DATABASE_NAME)) as conn:
        with conn:
            existing = conn.execute("""
                SELECT id FROM products WHERE title = ?
            """, (title,)).fetchone()

            if existing:
                print(f"Already saved: {title}")
                return profit

            conn.execute("""
                INSERT INTO products
                (title, model, category, buy_price,
                 sell_price, expected_profit)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                title,
                product["model"],
                product["category"],
                buy_price,
                sell_price,
                profit
            ))

    print(f"Saved: {title}")
    return profit


def show_products():
    with closing(sqlite3.connect(DATABASE_NAME)) as conn:
        products = conn.execute("""
            SELECT title, model, category, expected_profit
            FROM products
        """).fetchall()

    print("\nDEALHUNTER DATABASE")
    print("--------------------")

    for title, model, category, profit in products:
        print(f"\nProduct: {title}")
        print(f"Model: {model}")
        print(f"Category: {category}")
        print(f"Expected Profit: ${profit:.2f}")


def main():
    create_database()

    save_product(
        "John Deere Z930M Mower Part",
        150, 400, 20, 50
    )

    save_product(
        "Used Gaming Controller",
        40, 100, 10, 15
    )

    save_product(
        "Dell Laptop Computer",
        200, 450, 20, 50
    )

    show_products()


if __name__ == "__main__":
    main()