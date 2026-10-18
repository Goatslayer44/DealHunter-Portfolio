import unittest

from product_matcher import MAX_TITLE_LENGTH, match_product


class TestProductMatcher(unittest.TestCase):

    def test_model_number_match(self):
        result = match_product("John Deere Z930M Mower Part")
        self.assertEqual(result, {"model": "Z930M", "category": "LAWN MOWER PART"})

    def test_case_insensitive(self):
        self.assertEqual(match_product("dell LAPTOP")["category"], "COMPUTER")

    def test_controller_category(self):
        self.assertEqual(match_product("Used Gaming Controller")["category"], "GAMING ACCESSORY")

    def test_unknown_product(self):
        self.assertEqual(match_product("Mystery Item"), {"model": "UNKNOWN", "category": "OTHER"})

    def test_model_requires_word_boundary(self):
        self.assertEqual(match_product("XZ930MX part")["model"], "UNKNOWN")

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            match_product("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(TypeError):
            match_product(None)

    def test_overlong_title_rejected(self):
        with self.assertRaises(ValueError):
            match_product("a" * (MAX_TITLE_LENGTH + 1))


if __name__ == "__main__":
    unittest.main()
