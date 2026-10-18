def calculate_profit(buy_price, sell_price, shipping, fees):
    total_cost = buy_price + shipping + fees
    return sell_price - total_cost


def main():
    # Fictional product example
    buy_price = 150
    sell_price = 400
    shipping = 20
    fees = 50

    profit = calculate_profit(
        buy_price, sell_price, shipping, fees
    )

    print("DEALHUNTER PORTFOLIO")
    print("--------------------")
    print(f"Purchase Price: ${buy_price:.2f}")
    print(f"Resale Price:   ${sell_price:.2f}")
    print(f"Shipping:       ${shipping:.2f}")
    print(f"Fees:           ${fees:.2f}")
    print(f"Expected Profit: ${profit:.2f}")

    if profit >= 100:
        print("Decision: PROFITABLE DEAL")
    else:
        print("Decision: SKIP")


if __name__ == "__main__":
    main()