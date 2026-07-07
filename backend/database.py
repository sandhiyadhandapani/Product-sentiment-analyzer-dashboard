from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

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
    if not mongodb_uri or mongodb_uri.strip() == "mongodb://localhost:27017":
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
    rating = product_data.get("rating") or product_data.get("product_rating") or 0
    total_reviews = product_data.get("total_reviews") or product_data.get("total_ratings") or len(reviews_payload)

    product_doc = {
        "product_name": product_name,
        "product_url": product_url,
        "image_url": product_data.get("image_url") or product_data.get("product_image"),
        "price": price,
        "rating": float(rating) if isinstance(rating, (int, float)) else 0.0,
        "total_reviews": int(total_reviews) if isinstance(total_reviews, (int, float)) else len(reviews_payload),
        "platform": platform,
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
    total_reviews = len(reviews)
    positive_count = sum(1 for review in reviews if str(review.get("sentiment", "")).lower() == "positive")
    negative_count = sum(1 for review in reviews if str(review.get("sentiment", "")).lower() == "negative")
    neutral_count = sum(1 for review in reviews if str(review.get("sentiment", "")).lower() == "neutral")

    positive_percentage = round((positive_count / total_reviews) * 100, 2) if total_reviews else 0.0
    negative_percentage = round((negative_count / total_reviews) * 100, 2) if total_reviews else 0.0
    neutral_percentage = round((neutral_count / total_reviews) * 100, 2) if total_reviews else 0.0

    rating_values = [int(review.get("rating") or 0) for review in reviews]
    average_rating = round(sum(rating_values) / total_reviews, 2) if total_reviews else 0.0

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

    return {
        "product_name": product.get("product_name") or product.get("name") or "Unknown Product",
        "rating": product.get("rating") or 0,
        "price": product.get("price") or "N/A",
        "total_reviews": total_reviews,
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
    }
