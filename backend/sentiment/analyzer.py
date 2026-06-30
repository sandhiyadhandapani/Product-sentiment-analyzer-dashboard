from __future__ import annotations

import logging

from scraper.amazon_scraper import scrape_amazon_reviews
from scraper.flipkart_scraper import scrape_flipkart_reviews
from utils.cleaner import clean_text

logger = logging.getLogger(__name__)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception:  # pragma: no cover - fallback for environments without vader
    SentimentIntensityAnalyzer = None


def analyze_sentiment(text: str) -> dict:
    cleaned = clean_text(text)
    if not cleaned:
        return {"sentiment": "Neutral", "score": 0.0}

    if SentimentIntensityAnalyzer is not None:
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(cleaned)
        compound = scores.get("compound", 0.0)
        if compound >= 0.05:
            sentiment = "Positive"
        elif compound <= -0.05:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
        return {"sentiment": sentiment, "score": round(compound, 3)}

    positive_words = {"good", "great", "excellent", "love", "amazing", "best", "nice", "fantastic", "awesome"}
    negative_words = {"bad", "poor", "worst", "hate", "terrible", "awful", "disappointing", "slow", "expensive"}
    lower_text = cleaned.lower()
    positive_count = sum(1 for word in positive_words if word in lower_text)
    negative_count = sum(1 for word in negative_words if word in lower_text)

    if positive_count > negative_count:
        return {"sentiment": "Positive", "score": round(0.5 + (positive_count - negative_count) * 0.05, 3)}
    if negative_count > positive_count:
        return {"sentiment": "Negative", "score": round(-0.5 - (negative_count - positive_count) * 0.05, 3)}
    return {"sentiment": "Neutral", "score": 0.0}


def analyze_product(product_name: str) -> dict:
    product_query = (product_name or "").strip()
    if not product_query:
        raise ValueError("Product name cannot be empty")

    amazon_reviews: list[dict] = []
    flipkart_reviews: list[dict] = []

    try:
        amazon_reviews = scrape_amazon_reviews(product_query, max_reviews=10)
    except Exception as exc:
        logger.warning("Amazon review scraping failed: %s", exc)

    try:
        flipkart_reviews = scrape_flipkart_reviews(product_query, max_reviews=10)
    except Exception as exc:
        logger.warning("Flipkart review scraping failed: %s", exc)

    analyzed_reviews: list[dict] = []
    for review_entry in amazon_reviews + flipkart_reviews:
        review_text = review_entry.get("review", "") or ""
        cleaned_review = clean_text(review_text)
        if not cleaned_review:
            continue

        result = analyze_sentiment(cleaned_review)
        analyzed_reviews.append(
            {
                "review": cleaned_review,
                "sentiment": result["sentiment"],
                "score": result["score"],
            }
        )

    positive = sum(1 for item in analyzed_reviews if item["sentiment"] == "Positive")
    negative = sum(1 for item in analyzed_reviews if item["sentiment"] == "Negative")
    neutral = sum(1 for item in analyzed_reviews if item["sentiment"] == "Neutral")

    if analyzed_reviews:
        message = "Analysis completed successfully."
    else:
        message = "No real reviews found."

    return {
        "product": product_query,
        "total_reviews": len(analyzed_reviews),
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "reviews": analyzed_reviews,
        "message": message,
    }
