import unittest
from profit_calculator import calculate_profit


class TestProfitCalculator(unittest.TestCase):

    def test_profitable_deal(self):
        result = calculate_profit(150, 400, 20, 50)
        self.assertEqual(result, 180)

    def test_no_profit(self):
        result = calculate_profit(200, 200, 0, 0)
        self.assertEqual(result, 0)

    def test_losing_deal(self):
        result = calculate_profit(300, 200, 20, 30)
        self.assertEqual(result, -150)


if __name__ == "__main__":
    unittest.main()