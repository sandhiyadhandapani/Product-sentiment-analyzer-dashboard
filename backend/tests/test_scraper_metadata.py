import unittest

from scraper.firstcry_scraper import extract_firstcry_product_metadata


class ScraperMetadataTests(unittest.TestCase):
    def test_firstcry_metadata_extraction(self):
        html = """
        <html><head><meta property="og:title" content="Apple iPhone 15"/></head>
        <body>
          <h1>Apple iPhone 15</h1>
          <img id="productImage" src="https://example.com/phone.jpg"/>
          <div class="price">₹79,900</div>
          <div class="rating">4.5</div>
          <span class="review-count">4,567 ratings</span>
        </body></html>
        """
        metadata = extract_firstcry_product_metadata(html)
        self.assertEqual(metadata["product_name"], "Apple iPhone 15")
        self.assertEqual(metadata["product_image"], "https://example.com/phone.jpg")
        self.assertEqual(metadata["product_price"], "₹79,900")
        self.assertEqual(metadata["product_rating"], 4.5)
        self.assertEqual(metadata["total_ratings"], 4567)

    def test_firstcry_cards_are_preferred_over_logo_assets(self):
        html = """
        <html><head><title>FirstCry Search</title></head><body>
          <img src="https://cdn.firstcry.com/assets/logo.png" alt="FirstCry"/>
          <div class="product-card">
            <a href="/apple-iphone-15-pro"><h2>Apple iPhone 15 Pro</h2></a>
            <img src="https://example.com/phone.jpg"/>
            <div class="price">₹1,39,900</div>
            <div class="rating">4.6</div>
          </div>
          <div class="product-card">
            <a href="/apple-iphone-15-plus"><h2>Apple iPhone 15 Plus</h2></a>
          </div>
        </body></html>
        """
        metadata = extract_firstcry_product_metadata(html)
        self.assertEqual(metadata["product_name"], "Apple iPhone 15 Pro")
        self.assertEqual(metadata["product_image"], "https://example.com/phone.jpg")
        self.assertEqual(metadata["product_price"], "₹1,39,900")
        self.assertEqual(metadata["product_rating"], 4.6)

    def test_page_title_is_not_used_as_product_name(self):
        html = """
        <html><head><title>Search results for iphone</title></head><body>
          <h1>Apple iPhone 15 Pro</h1>
          <img src="https://example.com/phone.jpg"/>
          <div>₹1,39,900</div>
        </body></html>
        """
        metadata = extract_firstcry_product_metadata(html)
        self.assertEqual(metadata["product_name"], "Apple iPhone 15 Pro")
        self.assertEqual(metadata["product_image"], "https://example.com/phone.jpg")


if __name__ == "__main__":
    unittest.main()
