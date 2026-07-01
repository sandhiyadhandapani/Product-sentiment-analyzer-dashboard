import unittest

from scraper.amazon_scraper import extract_amazon_product_metadata
from scraper.flipkart_scraper import extract_flipkart_product_metadata


class ScraperMetadataTests(unittest.TestCase):
    def test_amazon_metadata_extraction(self):
        html = """
        <html><head><meta property="og:title" content="Apple iPhone 15"/></head>
        <body>
          <span id="productTitle">Apple iPhone 15</span>
          <img id="landingImage" src="https://example.com/phone.jpg"/>
          <span class="a-price"><span class="a-offscreen">₹79,900</span></span>
          <span class="a-icon-alt">4.5 out of 5 stars</span>
          <span id="acrCustomerReviewText">4,567 ratings</span>
        </body></html>
        """
        metadata = extract_amazon_product_metadata(html)
        self.assertEqual(metadata["product_name"], "Apple iPhone 15")
        self.assertEqual(metadata["product_image"], "https://example.com/phone.jpg")
        self.assertEqual(metadata["product_price"], "₹79,900")
        self.assertEqual(metadata["product_rating"], 4.5)
        self.assertEqual(metadata["total_ratings"], 4567)

    def test_flipkart_metadata_extraction(self):
        html = """
        <html><head><meta property="og:title" content="Apple iPhone 15 (Black, 128 GB)"/><meta property="og:image" content="https://example.com/flipkart.jpg"/></head>
        <body>
          <h1>Apple iPhone 15 (Black, 128 GB)</h1>
          <div class="_30jeq3 _16Jk6d">₹79,900</div>
          <div class="_3LWZlK">4.5</div>
          <span class="_2_R_DZ">4,567 Ratings & 9,277 Reviews</span>
        </body></html>
        """
        metadata = extract_flipkart_product_metadata(html)
        self.assertEqual(metadata["product_name"], "Apple iPhone 15 (Black, 128 GB)")
        self.assertEqual(metadata["product_image"], "https://example.com/flipkart.jpg")
        self.assertEqual(metadata["product_price"], "₹79,900")
        self.assertEqual(metadata["product_rating"], 4.5)
        self.assertEqual(metadata["total_ratings"], 4567)

    def test_amazon_cards_are_preferred_over_page_logo(self):
        html = """
        <html><head><title>Search results</title></head><body>
          <img src="https://images-na.ssl-images-amazon.com/images/G/01/amazon_logo.png" alt="Amazon"/>
          <div data-component-type="s-search-result">
            <a href="/dp/B0ABC123"><h2>Apple iPhone 15 Pro</h2></a>
            <img src="https://example.com/phone.jpg"/>
            <span class="a-price"><span class="a-offscreen">₹1,39,900</span></span>
            <span class="a-icon-alt">4.6 out of 5 stars</span>
          </div>
          <div data-component-type="s-search-result">
            <a href="/dp/B0XYZ999"><h2>Apple iPhone 15 Plus</h2></a>
          </div>
        </body></html>
        """
        metadata = extract_amazon_product_metadata(html)
        self.assertEqual(metadata["product_name"], "Apple iPhone 15 Pro")
        self.assertEqual(metadata["product_image"], "https://example.com/phone.jpg")
        self.assertEqual(metadata["product_price"], "₹1,39,900")
        self.assertEqual(metadata["product_rating"], 4.6)

    def test_flipkart_cards_are_preferred_over_logo_assets(self):
        html = """
        <html><head><title>Flipkart Search</title></head><body>
          <img src="https://rukminim1.flixcart.com/www/flipkart-logo.png" alt="Flipkart"/>
          <div class="_1AtVbE">
            <a class="VJA3rP" href="/apple-iphone-15-pro/p/itx123"><div>Apple iPhone 15 Pro</div></a>
            <img src="https://rukminim2.flixcart.com/image/phone.jpg"/>
            <div class="_30jeq3 _16Jk6d">₹1,39,900</div>
            <div class="_3LWZlK">4.6</div>
          </div>
          <div class="_1AtVbE">
            <a class="VJA3rP" href="/apple-iphone-15-plus/p/itx999"><div>Apple iPhone 15 Plus</div></a>
          </div>
        </body></html>
        """
        metadata = extract_flipkart_product_metadata(html)
        self.assertEqual(metadata["product_name"], "Apple iPhone 15 Pro")
        self.assertEqual(metadata["product_image"], "https://rukminim2.flixcart.com/image/phone.jpg")
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
        metadata = extract_amazon_product_metadata(html)
        self.assertEqual(metadata["product_name"], "Apple iPhone 15 Pro")
        self.assertEqual(metadata["product_image"], "https://example.com/phone.jpg")

    def test_flipkart_product_fields_are_extracted_from_the_same_card(self):
        html = """
        <html><body>
          <div class="_1AtVbE">
            <a class="VJA3rP" title="vivo Y28 5G (Crystal Purple, 128 GB)" href="/vivo-y28-5g-crystal-purple-128-gb/p/itme123">
              <div>vivo Y28 5G (Crystal Purple, 128 GB)</div>
            </a>
            <img src="https://rukminim2.flixcart.com/image/phone.jpg"/>
            <div class="_30jeq3 _16Jk6d">₹12,999</div>
            <div class="_3LWZlK">4.3</div>
            <div class="_3Ay6Sb">4.3 ★</div>
            <div class="_2kHMtA">Extra ₹1000 off</div>
            <div class="_13oc-S">128 GB • 8 GB RAM • 5G • 50MP Camera</div>
          </div>
        </body></html>
        """
        metadata = extract_flipkart_product_metadata(html)
        self.assertEqual(metadata["product_name"], "vivo Y28 5G (Crystal Purple, 128 GB)")
        self.assertEqual(metadata["product_image"], "https://rukminim2.flixcart.com/image/phone.jpg")
        self.assertEqual(metadata["product_price"], "₹12,999")
        self.assertEqual(metadata["product_rating"], 4.3)


if __name__ == "__main__":
    unittest.main()
