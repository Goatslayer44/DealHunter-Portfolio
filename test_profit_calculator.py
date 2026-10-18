import unittest
from profit_calculator import calculate_profit, is_profitable


class TestProfitCalculator(unittest.TestCase):

    def test_profitable_deal(self):
        self.assertEqual(calculate_profit(150, 400, 20, 50), 180)

    def test_no_profit(self):
        self.assertEqual(calculate_profit(200, 200, 0, 0), 0)

    def test_losing_deal(self):
        self.assertEqual(calculate_profit(300, 200, 20, 30), -150)

    def test_decimal_prices(self):
        self.assertAlmostEqual(calculate_profit(10.5, 20.25, 2.25, 1.0), 6.5)

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            calculate_profit(-1, 100, 0, 0)

    def test_non_numeric_rejected(self):
        with self.assertRaises(TypeError):
            calculate_profit("150", 400, 20, 50)

    def test_boolean_rejected(self):
        with self.assertRaises(TypeError):
            calculate_profit(True, 400, 20, 50)

    def test_nan_and_infinity_rejected(self):
        for bad in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                calculate_profit(bad, 400, 20, 50)

    def test_is_profitable_threshold(self):
        self.assertTrue(is_profitable(100))
        self.assertFalse(is_profitable(99.99))


if __name__ == "__main__":
    unittest.main()
