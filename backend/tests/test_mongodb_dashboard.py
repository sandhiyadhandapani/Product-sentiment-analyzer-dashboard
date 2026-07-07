from database import build_dashboard_payload


def test_build_dashboard_payload_calculates_metrics_and_recent_reviews():
    product = {
        "_id": "product-1",
        "product_name": "Baby Bottle",
        "price": "499",
        "rating": 4.5,
        "total_reviews": 5,
    }
    reviews = [
        {"review_text": "Great", "rating": 5, "sentiment": "Positive", "created_at": "2024-01-05T00:00:00"},
        {"review_text": "Okay", "rating": 3, "sentiment": "Neutral", "created_at": "2024-01-04T00:00:00"},
        {"review_text": "Bad", "rating": 1, "sentiment": "Negative", "created_at": "2024-01-03T00:00:00"},
        {"review_text": "Nice", "rating": 4, "sentiment": "Positive", "created_at": "2024-01-02T00:00:00"},
        {"review_text": "Average", "rating": 2, "sentiment": "Neutral", "created_at": "2024-01-01T00:00:00"},
    ]

    payload = build_dashboard_payload(product, reviews)

    assert payload["product_name"] == "Baby Bottle"
    assert payload["total_reviews"] == 5
    assert payload["positive_count"] == 2
    assert payload["negative_count"] == 1
    assert payload["neutral_count"] == 2
    assert payload["positive_percentage"] == 40.0
    assert payload["negative_percentage"] == 20.0
    assert payload["neutral_percentage"] == 40.0
    assert payload["average_rating"] == 3.0
    assert payload["rating_distribution"]["5_star"] == 1
    assert payload["rating_distribution"]["4_star"] == 1
    assert payload["rating_distribution"]["3_star"] == 1
    assert payload["rating_distribution"]["2_star"] == 1
    assert payload["rating_distribution"]["1_star"] == 1
    assert len(payload["recent_reviews"]) == 5
