import unittest
from unittest.mock import patch

from scraper.firstcry_scraper import (
    extract_firstcry_product_details,
    extract_reviews_from_html,
    scrape_firstcry_reviews,
)


class FirstCryScraperTests(unittest.TestCase):
    def test_extract_firstcry_product_details_parses_common_fields(self):
        html = """
        <html>
          <head>
            <meta property="og:title" content="Baby Stroller" />
            <meta property="og:image" content="https://example.com/stroller.jpg" />
          </head>
          <body>
            <h1>Baby Stroller</h1>
            <div class="price-row">
              <span class="price">₹2,499</span>
              <span class="mrp">₹3,499</span>
            </div>
            <div class="discount">28% Off</div>
            <div class="rating">4.5</div>
            <div class="rating-count">1200 Ratings</div>
            <div class="review-count">300 Reviews</div>
            <div class="product-description">Lightweight stroller with extra storage.</div>
          </body>
        </html>
        """

        result = extract_firstcry_product_details(html)

        self.assertEqual(result["product_name"], "Baby Stroller")
        self.assertEqual(result["current_price"], 2499)
        self.assertEqual(result["original_price"], 3499)
        self.assertEqual(result["discount_percentage"], 28)
        self.assertEqual(result["rating"], 4.5)
        self.assertEqual(result["total_ratings"], 1200)
        self.assertEqual(result["total_reviews"], 300)
        self.assertEqual(result["description"], "Lightweight stroller with extra storage.")
        self.assertEqual(result["product_image"], "https://example.com/stroller.jpg")

    def test_extract_firstcry_product_details_parses_embedded_json_fallback(self):
        html = """
        <html>
          <body>
            <script>
              window.__NEXT_DATA__ = {"props": {"pageProps": {"product": {"name": "Baby Stroller", "image": "https://example.com/stroller.jpg", "price": "₹2,499", "originalPrice": "₹3,499", "discountPercentage": 28, "rating": 4.5, "ratings": 1200, "reviews": 300}}}};
            </script>
          </body>
        </html>
        """

        result = extract_firstcry_product_details(html)

        self.assertEqual(result["product_name"], "Baby Stroller")
        self.assertEqual(result["current_price"], 2499)
        self.assertEqual(result["original_price"], 3499)
        self.assertEqual(result["discount_percentage"], 28)
        self.assertEqual(result["rating"], 4.5)
        self.assertEqual(result["total_ratings"], 1200)
        self.assertEqual(result["total_reviews"], 300)
        self.assertEqual(result["product_image"], "https://example.com/stroller.jpg")

    def test_extract_reviews_from_html_filters_placeholder_and_duplicates(self):
        html = """
        <html>
          <body>
            <div class="review-card">
              <div class="review-text">Ratings & Reviews</div>
            </div>
            <div class="review-card">
              <div class="review-text">Write a Review</div>
            </div>
            <div class="review-card">
              <div class="reviewer-name">Asha</div>
              <div class="review-rating">5</div>
              <div class="review-text">This stroller is excellent and very easy to use for daily walks.</div>
            </div>
            <div class="review-card">
              <div class="reviewer-name">Asha</div>
              <div class="review-rating">5</div>
              <div class="review-text">This stroller is excellent and very easy to use for daily walks.</div>
            </div>
          </body>
        </html>
        """

        result = extract_reviews_from_html(html, max_reviews=5)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["reviewer_name"], "Asha")
        self.assertEqual(result[0]["review_rating"], 5)

    @patch("scraper.firstcry_scraper._build_driver")
    def test_scrape_firstcry_reviews_returns_structured_payload(self, mock_build_driver):
        class DummyDriver:
            def __init__(self):
                self.page_source = """
                <html>
                  <body>
                    <a href="/p/test-product">Product</a>
                    <div class="review-card">
                      <div class="reviewer-name">Asha</div>
                      <div class="review-rating">5</div>
                      <div class="review-text">Excellent product and easy to use.</div>
                      <div class="review-date">2024-01-01</div>
                    </div>
                  </body>
                </html>
                """
                self.title = "FirstCry"

            def set_page_load_timeout(self, *_args, **_kwargs):
                return None

            def set_script_timeout(self, *_args, **_kwargs):
                return None

            def get(self, *_args, **_kwargs):
                return None

            def execute_script(self, script, *args, **kwargs):
                return None

            def find_elements(self, *args, **kwargs):
                return []

            def quit(self):
                return None

        mock_build_driver.return_value = DummyDriver()

        result = scrape_firstcry_reviews("baby stroller", return_metadata=True)

        self.assertTrue(result["meta"]["success"])
        self.assertEqual(result["meta"]["product_name"], "Product")
        self.assertEqual(len(result["reviews"]), 1)
        self.assertEqual(result["reviews"][0]["reviewer_name"], "Asha")
        self.assertEqual(result["reviews"][0]["review_rating"], 5)


if __name__ == "__main__":
    unittest.main()
