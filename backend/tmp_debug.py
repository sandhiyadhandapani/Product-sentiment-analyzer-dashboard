from scraper.firstcry_scraper import _safe_json_loads, _iter_json_objects, _extract_embedded_json_payload

content = 'window.__NEXT_DATA__ = {"props": {"pageProps": {"product": {"name": "Baby Stroller", "image": "https://example.com/stroller.jpg", "price": "₹2,499", "originalPrice": "₹3,499", "discountPercentage": 28, "rating": 4.5, "ratings": 1200, "reviews": 300}}}};'
print(_safe_json_loads(content))
for obj in _iter_json_objects(_safe_json_loads(content)):
    if isinstance(obj, dict):
        print(obj.keys())
print(_extract_embedded_json_payload('<html><body><script>'+content+'</script></body></html>'))
