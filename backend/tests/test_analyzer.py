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
    def test_analyze_product_treats_mixed_as_firstcry(self, mock_firstcry):
        mock_firstcry.return_value = {
            "reviews": [{"review_text": "Bad experience and slow delivery", "rating": 2, "platform": "firstcry"}],
            "meta": {"blocked": False, "message": ""},
        }

        result = analyze_product("iphone 15", platform="mixed")

        self.assertEqual(result["platform"], "mixed")
        self.assertEqual(result["reviews"][0]["sentiment"], "Negative")


if __name__ == "__main__":
    unittest.main()
