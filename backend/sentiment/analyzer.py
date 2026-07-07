from __future__ import annotations

import asyncio
import logging

from data.analysis_store import save_analysis_result
from database import save_product_with_reviews
from scraper.firstcry_scraper import scrape_firstcry_reviews
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


def _log_scraper_metadata(platform: str, scraper_name: str, metadata: dict | None) -> None:
    if not metadata:
        logger.info("Analyze selected platform: %s", platform)
        logger.info("Analyze scraper function called: %s", scraper_name)
        logger.info("Analyze review blocks detected: 0")
        logger.info("Analyze extracted reviews count: 0")
        return

    logger.info("Analyze selected platform: %s", platform)
    logger.info("Analyze scraper function called: %s", scraper_name)
    logger.info("Analyze search URL: %s", metadata.get("search_url") or "")
    logger.info("Analyze product URL: %s", metadata.get("product_url") or "")
    logger.info("Analyze review URL: %s", metadata.get("review_url") or "")
    logger.info("Analyze page title: %s", metadata.get("page_title") or "")
    logger.info("Analyze HTML length: %s", metadata.get("html_length") or 0)
    logger.info("Analyze review blocks detected: %s", metadata.get("review_blocks_detected") or 0)
    logger.info("Analyze extracted reviews count: %s", metadata.get("extracted_reviews_count") or 0)


def analyze_product(product_name: str, platform: str | None = None) -> dict:
    return asyncio.run(analyze_product_async(product_name, platform))


async def analyze_product_async(product_name: str, platform: str | None = None) -> dict:
    product_query = (product_name or "").strip()
    if not product_query:
        raise ValueError("Product name cannot be empty")

    requested_platform = (platform or "firstcry").strip().lower()
    if requested_platform != "firstcry":
        raise ValueError("Platform must be: firstcry")

    firstcry_result = {"reviews": [], "meta": {}}

    try:
        firstcry_result = scrape_firstcry_reviews(product_query, max_reviews=10, return_metadata=True)
    except Exception as exc:
        logger.warning("FirstCry review scraping failed: %s", exc)

    firstcry_reviews = firstcry_result.get("reviews", []) if isinstance(firstcry_result, dict) else []
    firstcry_meta = firstcry_result.get("meta", {}) if isinstance(firstcry_result, dict) else {}

    selected_platform = requested_platform
    selected_reviews: list[dict] = []
    selected_meta: dict | None = None
    product_metadata = {
        "product_name": product_query,
        "product_image": None,
        "product_price": None,
        "product_rating": None,
        "total_ratings": None,
        "current_price": None,
        "rating": None,
    }

    if firstcry_reviews:
        selected_reviews = firstcry_reviews
        selected_meta = firstcry_meta if firstcry_meta else None
        # Map scraper fields to analyzer expected fields
        product_metadata.update({
            "product_name": firstcry_meta.get("product_name") or product_metadata.get("product_name"),
            "product_image": firstcry_meta.get("product_image") or firstcry_meta.get("image"),
            "product_price": firstcry_meta.get("product_price") or firstcry_meta.get("current_price"),
            "product_rating": firstcry_meta.get("product_rating") or firstcry_meta.get("rating"),
            "total_ratings": firstcry_meta.get("total_ratings"),
        })
    else:
        selected_reviews = []
        selected_meta = firstcry_meta if firstcry_meta else None
        product_metadata.update({
            "product_name": firstcry_meta.get("product_name") or product_metadata.get("product_name"),
            "product_image": firstcry_meta.get("product_image") or firstcry_meta.get("image"),
            "product_price": firstcry_meta.get("product_price") or firstcry_meta.get("current_price"),
            "product_rating": firstcry_meta.get("product_rating") or firstcry_meta.get("rating"),
            "total_ratings": firstcry_meta.get("total_ratings"),
        })

    if firstcry_meta:
        _log_scraper_metadata("firstcry", "scrape_firstcry_reviews", firstcry_meta)

    logger.info("Analyze selected platform: %s", selected_platform)

    analyzed_reviews: list[dict] = []
    for review_entry in selected_reviews:
        review_text = review_entry.get("review_text") or review_entry.get("review", "") or ""
        cleaned_review = clean_text(review_text)
        if not cleaned_review:
            continue

        result = analyze_sentiment(cleaned_review)
        rating = review_entry.get("rating") or review_entry.get("review_rating") or 0
        analyzed_reviews.append(
            {
                "review_text": cleaned_review,
                "rating": int(rating) if isinstance(rating, (int, float)) else 0,
                "review_rating": int(rating) if isinstance(rating, (int, float)) else 0,
                "sentiment": result["sentiment"],
                "platform": selected_platform,
                "score": result.get("score", 0.0),
            }
        )

    positive = sum(1 for item in analyzed_reviews if item["sentiment"] == "Positive")
    negative = sum(1 for item in analyzed_reviews if item["sentiment"] == "Negative")
    neutral = sum(1 for item in analyzed_reviews if item["sentiment"] == "Neutral")

    block_message = "Unable to fetch real reviews. Site may be blocking scraping."
    product_name = product_metadata.get("product_name")
    product_image = product_metadata.get("product_image")
    product_price = product_metadata.get("product_price")
    has_real_product = bool(product_name and (product_price or product_image))

    if selected_meta and selected_meta.get("blocked") and has_real_product:
        message = selected_meta.get("message") or "Product details were found, but live reviews were blocked."
    elif selected_meta and selected_meta.get("blocked"):
        message = selected_meta.get("message") or block_message
    elif has_real_product:
        message = "Analysis completed successfully." if analyzed_reviews else "Product details were found, but no reviews were extracted."
    else:
        message = block_message

    result = {
        "success": has_real_product,
        "product": product_query,
        "product_name": product_name,
        "product_image": product_image,
        "product_price": product_price,
        "product_rating": product_metadata.get("product_rating"),
        "total_ratings": product_metadata.get("total_ratings"),
        "rating": product_metadata.get("product_rating"),  # Add rating field for frontend compatibility
        "current_price": product_price,  # Add current_price field for frontend compatibility
        "platform": selected_platform,
        "total_reviews": len(analyzed_reviews),
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "reviews": analyzed_reviews,
        "summary": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "total_reviews": len(analyzed_reviews),
        },
        "message": message,
    }

    try:
        await save_product_with_reviews(
            {
                "product_name": result.get("product_name") or product_query,
                "product_url": None,
                "image_url": result.get("product_image"),
                "price": result.get("product_price"),
                "rating": result.get("product_rating"),
                "total_reviews": result.get("total_reviews"),
                "platform": result.get("platform") or selected_platform,
            },
            [
                {
                    "review_text": review.get("review_text"),
                    "reviewer_name": "Customer",
                    "review_date": None,
                    "rating": review.get("rating"),
                    "sentiment": review.get("sentiment"),
                    "created_at": None,
                }
                for review in analyzed_reviews
            ],
        )
    except Exception as exc:
        logger.warning("Failed to persist analysis into MongoDB: %s", exc)
    
    logger.info(f"=== API Response to Frontend ===")
    logger.info(f"Product Name: {result['product_name']}")
    logger.info(f"Product Price: {result['product_price']}")
    logger.info(f"Product Rating: {result['product_rating']}")
    logger.info(f"Total Ratings: {result['total_ratings']}")
    logger.info(f"Total Reviews: {result['total_reviews']}")
    logger.info(f"Platform: {result['platform']}")
    logger.info(f"Success: {result['success']}")

    try:
        return save_analysis_result(result)
    except Exception as exc:
        logger.warning("Failed to store analysis result: %s", exc)
        return result
