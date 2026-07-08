from __future__ import annotations

import asyncio
import copy
import logging
import time
from datetime import datetime, timezone

from data.analysis_store import save_analysis_result
from database import save_dashboard_snapshot, save_product_with_reviews
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


# ---------------------------------------------------------------------------
# Short-lived result cache (Issues 1, 7, 8): repeated analyses of the same
# product - e.g. navigating Search -> Details -> Reviews, or re-searching the
# same term - reuse the already-scraped result instead of launching a brand new
# (expensive) Selenium scrape every time. This removes duplicate scraping and
# makes repeated searches return a consistent result.
# ---------------------------------------------------------------------------
MAX_REVIEWS_PER_ANALYSIS = 30
_ANALYSIS_CACHE_TTL = 600.0  # seconds
_ANALYSIS_CACHE: dict[str, tuple[float, dict]] = {}
_ANALYSIS_LOCKS: dict[str, asyncio.Lock] = {}


def _cache_key(platform: str, query: str) -> str:
    return f"{platform}::{query.strip().lower()}"


def analyze_product(product_name: str, platform: str | None = None) -> dict:
    return asyncio.run(analyze_product_async(product_name, platform))


async def analyze_product_async(product_name: str, platform: str | None = None) -> dict:
    """Public entry point. Validates input, serves a fresh-enough cached result
    when available, and otherwise runs a single scrape+analysis (never more than
    one concurrent scrape for the same query)."""
    product_query = (product_name or "").strip()
    if not product_query:
        raise ValueError("Product name cannot be empty")

    requested_platform = (platform or "firstcry").strip().lower()
    if requested_platform != "firstcry":
        raise ValueError("Platform must be: firstcry")

    key = _cache_key(requested_platform, product_query)
    cached = _ANALYSIS_CACHE.get(key)
    if cached and cached[0] > time.monotonic():
        logger.info("Serving cached analysis for '%s' (no re-scrape needed)", product_query)
        return copy.deepcopy(cached[1])

    # Serialize identical concurrent requests so only one scrape runs per query.
    lock = _ANALYSIS_LOCKS.setdefault(key, asyncio.Lock())
    async with lock:
        cached = _ANALYSIS_CACHE.get(key)
        if cached and cached[0] > time.monotonic():
            logger.info("Serving cached analysis for '%s' (populated while waiting)", product_query)
            return copy.deepcopy(cached[1])

        result = await _run_product_analysis(product_query, requested_platform)
        try:
            _ANALYSIS_CACHE[key] = (time.monotonic() + _ANALYSIS_CACHE_TTL, copy.deepcopy(result))
        except Exception:
            pass
        return result


async def _run_product_analysis(product_name: str, platform: str | None = None) -> dict:
    product_query = (product_name or "").strip()
    if not product_query:
        raise ValueError("Product name cannot be empty")

    requested_platform = (platform or "firstcry").strip().lower()
    if requested_platform != "firstcry":
        raise ValueError("Platform must be: firstcry")

    firstcry_result = {"reviews": [], "meta": {}}

    try:
        # Run the blocking Selenium scrape in a worker thread so it never blocks
        # the FastAPI event loop (root cause of the "Network Error" timeout).
        firstcry_result = await asyncio.to_thread(
            scrape_firstcry_reviews,
            product_query,
            max_reviews=MAX_REVIEWS_PER_ANALYSIS,
            return_metadata=True,
        )
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
        "total_reviews": None,
        "current_price": None,
        "original_price": None,
        "discount_percentage": None,
        "product_url": None,
        "rating": None,
    }

    # Both branches map the same scraper metadata; reviews may or may not exist.
    selected_reviews = firstcry_reviews if firstcry_reviews else []
    selected_meta = firstcry_meta if firstcry_meta else None
    product_metadata.update({
        "product_name": firstcry_meta.get("product_name") or product_metadata.get("product_name"),
        "product_image": firstcry_meta.get("product_image") or firstcry_meta.get("image"),
        "product_price": firstcry_meta.get("product_price") or firstcry_meta.get("current_price"),
        "product_rating": firstcry_meta.get("product_rating") or firstcry_meta.get("rating"),
        "total_ratings": firstcry_meta.get("total_ratings"),
        "total_reviews": firstcry_meta.get("total_reviews"),
        "current_price": firstcry_meta.get("current_price"),
        "original_price": firstcry_meta.get("original_price"),
        "discount_percentage": firstcry_meta.get("discount_percentage"),
        "product_url": firstcry_meta.get("product_url"),
    })

    if firstcry_meta:
        _log_scraper_metadata("firstcry", "scrape_firstcry_reviews", firstcry_meta)

    logger.info("Analyze selected platform: %s", selected_platform)

    analyzed_reviews: list[dict] = []
    for review_entry in selected_reviews:
        # Preserve the ORIGINAL review text exactly as scraped for display;
        # sentiment is computed on a cleaned copy (analyze_sentiment cleans
        # internally) so cleaning never mangles what the user sees (Issue 4).
        original_text = (review_entry.get("review_text") or review_entry.get("review") or "").strip()
        if not clean_text(original_text):
            continue

        result = analyze_sentiment(original_text)
        rating = review_entry.get("rating") or review_entry.get("review_rating") or 0
        analyzed_reviews.append(
            {
                "review_text": original_text,
                "reviewer_name": (review_entry.get("reviewer_name") or "").strip() or None,
                "review_date": (review_entry.get("review_date") or "").strip() or None,
                "verified_purchase": bool(review_entry.get("verified_purchase")),
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

    # ------------------------------------------------------------------
    # Source Summary + Dashboard snapshot (Issues 5 & 6) - built entirely
    # from the real scraped/analyzed data, never hardcoded.
    # ------------------------------------------------------------------
    product_rating = product_metadata.get("product_rating")
    sample_ratings = [r["rating"] for r in analyzed_reviews if r.get("rating")]
    average_rating = (
        round(float(product_rating), 1)
        if isinstance(product_rating, (int, float)) and product_rating
        else (round(sum(sample_ratings) / len(sample_ratings), 1) if sample_ratings else 0.0)
    )
    analysis_completed_at = datetime.now(timezone.utc).isoformat()
    scraping_time_seconds = (selected_meta or {}).get("elapsed_seconds")

    def _as_int(value):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    analyzed_count = len(analyzed_reviews)
    # Website's OWN total review count (what FirstCry reports on the product
    # page). The "Total Reviews" box must reflect this real site total even
    # though we only scrape & analyze the latest `analyzed_count` reviews for
    # sentiment. Falls back to total_ratings, then the analyzed sample size when
    # the site count could not be extracted.
    site_total_reviews = (
        _as_int(product_metadata.get("total_reviews"))
        or _as_int(product_metadata.get("total_ratings"))
        or analyzed_count
    )

    source_summary = {
        "website": "FirstCry",
        "platform": selected_platform,
        "product_name": product_name,
        "total_reviews": site_total_reviews,
        "analyzed_reviews": analyzed_count,
        "average_rating": average_rating,
        "positive_reviews": positive,
        "neutral_reviews": neutral,
        "negative_reviews": negative,
        "scraping_time_seconds": scraping_time_seconds,
        "analysis_completed_at": analysis_completed_at,
        "data_source": (selected_meta or {}).get("product_url") or (selected_meta or {}).get("search_url"),
    }

    dashboard_data = {
        "product_name": product_name,
        "product_image": product_image,
        "price": product_price,
        "rating": average_rating,
        "total_reviews": site_total_reviews,
        "analyzed_reviews": analyzed_count,
        "positive_count": positive,
        "neutral_count": neutral,
        "negative_count": negative,
        "sentiment_distribution": {"positive": positive, "neutral": neutral, "negative": negative},
        "source_summary": source_summary,
    }

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
        "original_price": product_metadata.get("original_price"),
        "discount_percentage": product_metadata.get("discount_percentage"),
        "product_url": product_metadata.get("product_url"),
        "platform": selected_platform,
        "total_reviews": site_total_reviews,
        "analyzed_reviews": analyzed_count,
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "reviews": analyzed_reviews,
        "summary": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "total_reviews": analyzed_count,
        },
        "source_summary": source_summary,
        "dashboard_data": dashboard_data,
        "message": message,
    }

    try:
        await save_product_with_reviews(
            {
                "product_name": result.get("product_name") or product_query,
                "product_url": (selected_meta or {}).get("product_url"),
                "image_url": result.get("product_image"),
                "price": result.get("product_price"),
                "current_price": result.get("product_price"),
                "original_price": result.get("original_price"),
                "discount_percentage": result.get("discount_percentage"),
                "rating": result.get("product_rating"),
                "total_reviews": result.get("total_reviews"),
                "platform": result.get("platform") or selected_platform,
                "scraping_time_seconds": scraping_time_seconds,
            },
            [
                {
                    "review_text": review.get("review_text"),
                    "reviewer_name": review.get("reviewer_name") or "Customer",
                    "review_date": review.get("review_date"),
                    "verified_purchase": bool(review.get("verified_purchase")),
                    "rating": review.get("rating"),
                    "sentiment": review.get("sentiment"),
                    "created_at": None,
                }
                for review in analyzed_reviews
            ],
        )
    except Exception as exc:
        logger.warning("Failed to persist analysis into MongoDB: %s", exc)

    # Overwrite the single latest-analysis dashboard snapshot (Issue 7).
    try:
        await save_dashboard_snapshot(
            {
                "product_name": product_name,
                "dashboard_data": dashboard_data,
                "source_summary": source_summary,
            }
        )
    except Exception as exc:
        logger.warning("Failed to persist dashboard snapshot into MongoDB: %s", exc)

    logger.info(f"=== API Response to Frontend ===")
    logger.info(f"Product Name: {result['product_name']}")
    logger.info(f"Product Price (current): {result['product_price']}")
    logger.info(f"Returned original_price (MRP): {result['original_price']}")
    logger.info(f"Returned API rating: {result['product_rating']}")
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
