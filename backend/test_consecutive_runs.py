import json
import time
from scraper.firstcry_scraper import scrape_firstcry_reviews

def test_consecutive_runs():
    query = "baby diapers"
    max_reviews = 5
    num_runs = 10
    
    results = []
    print(f"Testing scraper {num_runs} consecutive times with query: '{query}'")
    print("=" * 80)
    
    for i in range(num_runs):
        print(f"\n--- Run {i + 1}/{num_runs} ---")
        start = time.time()
        result = scrape_firstcry_reviews(query, max_reviews=max_reviews, return_metadata=True, headless=True)
        elapsed = time.time() - start
        
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
        print(f"Elapsed Time: {elapsed:.2f}s")
        print(f"Retry Count: {meta.get('retry_count')}")
        print(f"Message: {meta.get('message')}")
        
        # Store key fields for consistency check
        results.append({
            "run": i + 1,
            "product_name": meta.get('product_name'),
            "current_price": meta.get('current_price'),
            "original_price": meta.get('original_price'),
            "rating": meta.get('rating'),
            "total_ratings": meta.get('total_ratings'),
            "total_reviews": meta.get('total_reviews'),
            "reviews_count": len(reviews),
            "success": meta.get('success'),
            "elapsed": elapsed,
        })
        
        # Small delay between runs
        if i < num_runs - 1:
            time.sleep(2)
    
    # Analyze consistency
    print("\n" + "=" * 80)
    print("CONSISTENCY ANALYSIS")
    print("=" * 80)
    
    successful_runs = [r for r in results if r['success']]
    print(f"Successful runs: {len(successful_runs)}/{num_runs}")
    
    if len(successful_runs) > 1:
        product_names = set(r['product_name'] for r in successful_runs if r['product_name'])
        current_prices = set(r['current_price'] for r in successful_runs if r['current_price'])
        ratings = set(r['rating'] for r in successful_runs if r['rating'])
        
        print(f"Unique product names: {len(product_names)}")
        print(f"Unique current prices: {len(current_prices)}")
        print(f"Unique ratings: {len(ratings)}")
        
        if len(product_names) == 1:
            print("✓ Product name is CONSISTENT across runs")
        else:
            print("✗ Product name is INCONSISTENT across runs")
            print(f"  Found: {product_names}")
        
        if len(current_prices) == 1:
            print("✓ Current price is CONSISTENT across runs")
        else:
            print("✗ Current price is INCONSISTENT across runs")
            print(f"  Found: {current_prices}")
        
        if len(ratings) == 1:
            print("✓ Rating is CONSISTENT across runs")
        else:
            print("✗ Rating is INCONSISTENT across runs")
            print(f"  Found: {ratings}")
        
        # Check review counts
        review_counts = [r['reviews_count'] for r in successful_runs]
        avg_reviews = sum(review_counts) / len(review_counts)
        print(f"Average reviews per run: {avg_reviews:.1f}")
        print(f"Review count range: {min(review_counts)} - {max(review_counts)}")
    
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    for r in results:
        print(f"Run {r['run']}: name={r['product_name']}, price={r['current_price']}, rating={r['rating']}, reviews={r['reviews_count']}, success={r['success']}, time={r['elapsed']:.2f}s")
    
    # Save results to file
    with open('test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to test_results.json")

if __name__ == "__main__":
    test_consecutive_runs()
