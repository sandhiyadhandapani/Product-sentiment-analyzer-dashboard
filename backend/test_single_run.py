from scraper.firstcry_scraper import scrape_firstcry_reviews

query = "baby diapers"
print(f"Testing single run with query: '{query}'")
result = scrape_firstcry_reviews(query, max_reviews=5, return_metadata=True, headless=True)

meta = result.get("meta", {})
reviews = result.get("reviews", [])

print(f"Success: {meta.get('success')}")
print(f"Product Name: {meta.get('product_name')}")
print(f"Current Price: {meta.get('current_price')}")
print(f"Original Price: {meta.get('original_price')}")
print(f"Rating: {meta.get('rating')}")
print(f"Total Ratings: {meta.get('total_ratings')}")
print(f"Total Reviews: {meta.get('total_reviews')}")
print(f"Reviews Extracted: {len(reviews)}")
print(f"Message: {meta.get('message')}")
