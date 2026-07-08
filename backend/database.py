from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

DATABASE_NAME = "product_sentiment"

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _load_env_file() -> None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_env_file()


def get_mongo_uri() -> str:
    return os.getenv("MONGODB_URI", "mongodb://localhost:27017")


async def connect_to_mongo() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is not None and _client is not None:
        return _db

    mongodb_uri = get_mongo_uri()
    if not mongodb_uri:
        raise RuntimeError("MongoDB URI is not configured")

    try:
        _client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        _db = _client[DATABASE_NAME]
        await _ensure_indexes(_db)
    except Exception as exc:
        _client = None
        _db = None
        raise RuntimeError(f"MongoDB connection failed: {exc}") from exc

    return _db


async def close_mongo_connection() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


async def ping_database() -> bool:
    database = await get_database()
    if database is None:
        return False
    try:
        await database.command("ping")
        return True
    except Exception:
        return False


async def get_database() -> AsyncIOMotorDatabase | None:
    try:
        return await connect_to_mongo()
    except Exception:
        return None


async def _ensure_indexes(database: AsyncIOMotorDatabase) -> None:
    products: AsyncIOMotorCollection = database["products"]
    reviews: AsyncIOMotorCollection = database["reviews"]

    await products.create_index("product_url", unique=False)
    await products.create_index([("product_name", 1), ("platform", 1)])
    await reviews.create_index([("product_id", 1), ("sentiment", 1), ("rating", 1)])
    await reviews.create_index([("created_at", -1)])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_serializable(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if not document:
        return None

    payload = dict(document)
    if isinstance(payload.get("_id"), ObjectId):
        payload["id"] = str(payload["_id"])
        payload["_id"] = str(payload["_id"])
    elif "_id" in payload and payload["_id"] is not None:
        payload["id"] = str(payload["_id"])
    return payload


async def save_product_with_reviews(product_payload: dict[str, Any], reviews_payload: list[dict[str, Any]]) -> dict[str, Any] | None:
    database = await get_database()
    if database is None:
        return None

    product_data = dict(product_payload or {})
    product_name = product_data.get("product_name") or product_data.get("name") or "Unknown Product"
    product_url = product_data.get("product_url") or product_data.get("url") or product_data.get("product_link")
    platform = product_data.get("platform") or "firstcry"
    price = product_data.get("price") or product_data.get("product_price") or "N/A"
    # Preserve the real product rating; keep None when the site truly has no
    # rating so a missing value is never silently replaced with 0 (rating audit).
    _rating_source = product_data.get("rating")
    if _rating_source is None:
        _rating_source = product_data.get("product_rating")
    rating = float(_rating_source) if isinstance(_rating_source, (int, float)) and _rating_source else None
    logger.info("Storing product rating in MongoDB: %s (raw=%r)", rating, _rating_source)
    logger.info("Storing original_price in MongoDB: %s (raw=%r)", product_data.get("original_price"), product_data.get("original_price"))
    total_reviews = product_data.get("total_reviews") or product_data.get("total_ratings") or len(reviews_payload)

    product_doc = {
        "product_name": product_name,
        "product_url": product_url,
        "image_url": product_data.get("image_url") or product_data.get("product_image"),
        "price": price,
        "current_price": product_data.get("current_price") or price,
        "original_price": product_data.get("original_price"),
        "discount_percentage": product_data.get("discount_percentage"),
        "rating": rating,
        "total_reviews": int(total_reviews) if isinstance(total_reviews, (int, float)) else len(reviews_payload),
        "platform": platform,
        "scraping_time_seconds": product_data.get("scraping_time_seconds"),
        "created_at": product_data.get("created_at") or _utc_now(),
        "updated_at": _utc_now(),
    }

    filters = {"product_url": product_url} if product_url else {"product_name": product_name, "platform": platform}
    products_collection = database["products"]
    existing_product = await products_collection.find_one(filters)
    if existing_product is None:
        insert_result = await products_collection.insert_one(product_doc)
        product_doc["_id"] = insert_result.inserted_id
    else:
        product_doc["_id"] = existing_product.get("_id")
        await products_collection.update_one({"_id": existing_product["_id"]}, {"$set": product_doc}, upsert=True)

    product_id = str(product_doc.get("_id"))
    review_collection: AsyncIOMotorCollection = database["reviews"]

    for review in reviews_payload:
        review_text = review.get("review_text") or review.get("comment") or review.get("text") or ""
        if not review_text:
            continue
        review_doc = {
            "product_id": product_id,
            "review_text": review_text,
            "reviewer_name": review.get("reviewer_name") or review.get("username") or "Customer",
            "review_date": review.get("review_date") or review.get("date") or _utc_now(),
            "verified_purchase": bool(review.get("verified_purchase")),
            "rating": int(review.get("rating") or review.get("review_rating") or 0),
            "sentiment": review.get("sentiment") or "Neutral",
            "created_at": review.get("created_at") or _utc_now(),
        }
        duplicate_filter = {
            "product_id": product_id,
            "review_text": review_text,
            "reviewer_name": review_doc["reviewer_name"],
        }
        await review_collection.update_one(duplicate_filter, {"$setOnInsert": review_doc}, upsert=True)

    return _to_serializable({**product_doc, "id": product_id})


async def save_dashboard_snapshot(snapshot: dict[str, Any]) -> None:
    """Persist the single latest-analysis dashboard snapshot, overwriting the
    previous one (Issue 7). Stored under a fixed _id so there is always exactly
    one dashboard snapshot in MongoDB, replaced on every new analysis."""
    database = await get_database()
    if database is None:
        return
    doc = dict(snapshot or {})
    doc["_id"] = "latest"
    doc["updated_at"] = _utc_now()
    await database["dashboard_snapshots"].replace_one({"_id": "latest"}, doc, upsert=True)


async def get_dashboard_snapshot() -> dict[str, Any] | None:
    database = await get_database()
    if database is None:
        return None
    document = await database["dashboard_snapshots"].find_one({"_id": "latest"})
    return _to_serializable(document)


async def list_products(limit: int = 100) -> list[dict[str, Any]]:
    database = await get_database()
    if database is None:
        return []

    products_collection = database["products"]
    docs = await products_collection.find({}, {"_id": 1, "product_name": 1, "price": 1, "rating": 1, "total_reviews": 1, "platform": 1, "image_url": 1, "product_url": 1, "updated_at": 1}).sort("updated_at", -1).limit(limit).to_list(length=limit)
    return [_to_serializable(doc) for doc in docs if _to_serializable(doc)]


async def get_product_by_id(product_id: str) -> dict[str, Any] | None:
    database = await get_database()
    if database is None:
        return None

    products_collection = database["products"]
    try:
        document = await products_collection.find_one({"_id": ObjectId(product_id)})
    except Exception:
        document = await products_collection.find_one({"_id": product_id})

    if document is None:
        document = await products_collection.find_one({"product_name": product_id})
    return _to_serializable(document)


async def get_product_reviews(product_id: str, limit: int = 10, page: int = 1, sentiment: str | None = None, rating: int | None = None, sort: str = "desc") -> tuple[list[dict[str, Any]], int]:
    database = await get_database()
    if database is None:
        return [], 0

    review_collection = database["reviews"]
    query: dict[str, Any] = {"product_id": str(product_id)}
    if sentiment:
        query["sentiment"] = sentiment.capitalize()
    if rating is not None:
        query["rating"] = rating

    sort_order = -1 if sort.lower() != "asc" else 1
    total = await review_collection.count_documents(query)

    cursor = review_collection.find(query).sort("created_at", sort_order).skip((page - 1) * limit).limit(limit)
    documents = await cursor.to_list(length=limit)
    return [_to_serializable(doc) for doc in documents if _to_serializable(doc)], total


async def delete_old_reviews(product_id: str, older_than_days: int = 30) -> int:
    database = await get_database()
    if database is None:
        return 0

    review_collection = database["reviews"]
    cutoff = datetime.now(timezone.utc).timestamp() - (older_than_days * 86400)
    result = await review_collection.delete_many({"product_id": str(product_id), "created_at": {"$lt": datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()}})
    return int(result.deleted_count)


def build_dashboard_payload(product: dict[str, Any], reviews: list[dict[str, Any]]) -> dict[str, Any]:
    # `analyzed_reviews` = the sample we actually scraped & ran sentiment on
    # (used as the denominator for every percentage/average below). The DISPLAY
    # "Total Reviews" must instead show the website's own total review count.
    analyzed_reviews = len(reviews)

    def _as_int(value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    # Website's real total review count (stored on the product doc during the
    # scrape); fall back to total_ratings, then the analyzed sample size.
    site_total_reviews = (
        _as_int(product.get("total_reviews"))
        or _as_int(product.get("total_ratings"))
        or analyzed_reviews
    )

    positive_count = sum(1 for review in reviews if str(review.get("sentiment", "")).lower() == "positive")
    negative_count = sum(1 for review in reviews if str(review.get("sentiment", "")).lower() == "negative")
    neutral_count = sum(1 for review in reviews if str(review.get("sentiment", "")).lower() == "neutral")

    positive_percentage = round((positive_count / analyzed_reviews) * 100, 2) if analyzed_reviews else 0.0
    negative_percentage = round((negative_count / analyzed_reviews) * 100, 2) if analyzed_reviews else 0.0
    neutral_percentage = round((neutral_count / analyzed_reviews) * 100, 2) if analyzed_reviews else 0.0

    rating_values = [int(review.get("rating") or 0) for review in reviews]
    review_average = round(sum(rating_values) / analyzed_reviews, 2) if analyzed_reviews else 0.0
    # Fall back to the product's stored (site) rating when the persisted reviews
    # carry no per-review rating, so the dashboard never shows 0 when a rating exists.
    average_rating = review_average if review_average else round(float(product.get("rating") or 0), 2)

    rating_distribution = {
        "5_star": sum(1 for value in rating_values if value >= 5),
        "4_star": sum(1 for value in rating_values if value == 4),
        "3_star": sum(1 for value in rating_values if value == 3),
        "2_star": sum(1 for value in rating_values if value == 2),
        "1_star": sum(1 for value in rating_values if value == 1),
    }

    recent_reviews = sorted(
        reviews,
        key=lambda review: review.get("created_at") or review.get("review_date") or "",
        reverse=True,
    )[:5]

    product_name = product.get("product_name") or product.get("name") or "Unknown Product"
    # Headline rating falls back to the product's stored (site) rating when the
    # persisted review sample carries no per-review ratings.
    headline_rating = average_rating if average_rating else float(product.get("rating") or 0)

    # Source Summary built from the persisted product/review data (Issue 5) so
    # it stays populated across navigation and page refresh (Issue 3).
    source_summary = {
        "website": product.get("platform") or "FirstCry",
        "platform": product.get("platform") or "firstcry",
        "product_name": product_name,
        "total_reviews": site_total_reviews,
        "analyzed_reviews": analyzed_reviews,
        "average_rating": headline_rating,
        "positive_reviews": positive_count,
        "neutral_reviews": neutral_count,
        "negative_reviews": negative_count,
        "scraping_time_seconds": product.get("scraping_time_seconds"),
        "analysis_completed_at": product.get("updated_at"),
        "data_source": product.get("product_url"),
    }

    return {
        "product_name": product_name,
        "product_image": product.get("image_url") or product.get("product_image"),
        "platform": product.get("platform") or "firstcry",
        "product_url": product.get("product_url"),
        "rating": product.get("rating") or 0,
        "price": product.get("price") or "N/A",
        "total_reviews": site_total_reviews,
        "analyzed_reviews": analyzed_reviews,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "positive_percentage": positive_percentage,
        "negative_percentage": negative_percentage,
        "neutral_percentage": neutral_percentage,
        "average_rating": average_rating,
        "recent_reviews": recent_reviews,
        "sentiment_distribution": {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
        },
        "rating_distribution": rating_distribution,
        "source_summary": source_summary,
    }
