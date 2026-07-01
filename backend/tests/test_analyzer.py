import unittest
from unittest.mock import patch

from sentiment.analyzer import analyze_product


class AnalyzeProductTests(unittest.TestCase):
    @patch("sentiment.analyzer.scrape_flipkart_reviews")
    @patch("sentiment.analyzer.scrape_amazon_reviews")
    def test_analyze_product_preserves_requested_amazon_platform(self, mock_amazon, mock_flipkart):
        mock_amazon.return_value = {
            "reviews": [{"review_text": "Great phone and excellent camera", "rating": 5, "platform": "amazon"}],
            "meta": {"blocked": False, "message": ""},
        }
        mock_flipkart.return_value = {
            "reviews": [{"review_text": "Terrible battery and poor support", "rating": 1, "platform": "flipkart"}],
            "meta": {"blocked": False, "message": ""},
        }

        result = analyze_product("iphone 15", platform="amazon")

        self.assertEqual(result["platform"], "amazon")
        self.assertEqual(result["total_reviews"], 1)
        self.assertEqual(result["reviews"][0]["sentiment"], "Positive")

    @patch("sentiment.analyzer.scrape_flipkart_reviews")
    @patch("sentiment.analyzer.scrape_amazon_reviews")
    def test_analyze_product_uses_flipkart_when_requested(self, mock_amazon, mock_flipkart):
        mock_amazon.return_value = {"reviews": [], "meta": {"blocked": True, "message": ""}}
        mock_flipkart.return_value = {
            "reviews": [{"review_text": "Bad experience and slow delivery", "rating": 2, "platform": "flipkart"}],
            "meta": {"blocked": False, "message": ""},
        }

        result = analyze_product("iphone 15", platform="flipkart")

        self.assertEqual(result["platform"], "flipkart")
        self.assertEqual(result["reviews"][0]["sentiment"], "Negative")


if __name__ == "__main__":
    unittest.main()
