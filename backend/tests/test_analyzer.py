import unittest
from unittest.mock import patch

from sentiment.analyzer import analyze_product


class AnalyzeProductTests(unittest.TestCase):
    @patch("sentiment.analyzer.scrape_firstcry_reviews")
    def test_analyze_product_uses_firstcry_when_requested(self, mock_firstcry):
        mock_firstcry.return_value = {
            "reviews": [{"review_text": "Great phone and excellent camera", "rating": 5, "platform": "firstcry"}],
            "meta": {"blocked": False, "message": ""},
        }

        result = analyze_product("iphone 15", platform="firstcry")

        self.assertEqual(result["platform"], "firstcry")
        self.assertEqual(result["total_reviews"], 1)
        self.assertEqual(result["reviews"][0]["sentiment"], "Positive")

    @patch("sentiment.analyzer.scrape_firstcry_reviews")
    def test_analyze_product_defaults_to_firstcry(self, mock_firstcry):
        mock_firstcry.return_value = {
            "reviews": [{"review_text": "Bad experience and slow delivery", "rating": 2, "platform": "firstcry"}],
            "meta": {"blocked": False, "message": ""},
        }

        result = analyze_product("iphone 15", platform=None)

        self.assertEqual(result["platform"], "firstcry")
        self.assertEqual(result["reviews"][0]["sentiment"], "Negative")

    def test_analyze_product_invalid_platform_raises_error(self):
        with self.assertRaises(ValueError):
            analyze_product("iphone 15", platform="invalid")


if __name__ == "__main__":
    unittest.main()
