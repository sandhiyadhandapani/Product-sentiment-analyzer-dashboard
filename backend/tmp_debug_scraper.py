from scraper.firstcry_scraper import _safe_json_loads, _extract_embedded_json_payload, extract_firstcry_product_details, extract_reviews_from_html

html = '''<html><body><script>window.__NEXT_DATA__ = {"props": {"pageProps": {"product": {"name": "Baby Stroller", "image": "https://example.com/stroller.jpg", "price": "₹2,499", "originalPrice": "₹3,499", "discountPercentage": 28, "rating": 4.5, "ratings": 1200, "reviews": 300}}}};</script></body></html>'''
print(_safe_json_loads('window.__NEXT_DATA__ = {"props": {"pageProps": {"product": {"name": "Baby Stroller"}}}};'))
print(_extract_embedded_json_payload(html))
print(extract_firstcry_product_details(html))

html2 = '''<html><head><title>FirstCry Search</title></head><body><img src="https://cdn.firstcry.com/assets/logo.png" alt="FirstCry"/><div class="product-card"><a href="/apple-iphone-15-pro"><h2>Apple iPhone 15 Pro</h2></a><img src="https://example.com/phone.jpg"/><div class="price">₹1,39,900</div><div class="rating">4.6</div></div><div class="product-card"><a href="/apple-iphone-15-plus"><h2>Apple iPhone 15 Plus</h2></a></div></body></html>'''
print(extract_firstcry_product_details(html2))

html3 = '''<html><body><div class="review-card"><div class="review-text">Ratings & Reviews</div></div><div class="review-card"><div class="review-text">Write a Review</div></div><div class="review-card"><div class="reviewer-name">Asha</div><div class="review-rating">5</div><div class="review-text">This stroller is excellent and very easy to use for daily walks.</div></div><div class="review-card"><div class="reviewer-name">Asha</div><div class="review-rating">5</div><div class="review-text">This stroller is excellent and very easy to use for daily walks.</div></div></body></html>'''
print(extract_reviews_from_html(html3, max_reviews=5))
