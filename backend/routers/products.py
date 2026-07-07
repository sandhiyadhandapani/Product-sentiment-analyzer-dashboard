from fastapi import APIRouter, HTTPException, Query

from database import get_product_by_id, get_product_reviews as get_db_reviews, list_products
from schemas.product_schema import Product
from sentiment.analyzer import analyze_product_async

router = APIRouter(prefix="/api", tags=["products"])


@router.get("/products", response_model=list[Product])
async def get_products():
    return await list_products(limit=100)


@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/search", response_model=list[Product])
async def search_products(query: str = Query(..., description="Search by product name or category")):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    search_value = query.strip().lower()
    products = await list_products(limit=100)
    results = [
        product
        for product in products
        if search_value in str(product.get("product_name") or "").lower() or search_value in str(product.get("platform") or "").lower()
    ]
    return results


@router.get("/products/{product_id}/reviews")
async def get_product_reviews(product_id: str):
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    analysis = await analyze_product_async(product.get("product_name") or product.get("name") or "", platform="firstcry")
    reviews, _ = await get_db_reviews(product_id, limit=100, page=1)
    review_items = []
    for index, review in enumerate(reviews or [], start=1):
        review_items.append(
            {
                "id": review.get("id") or f"{product_id}-{index}",
                "username": review.get("reviewer_name") or "Customer",
                "rating": review.get("rating", 0),
                "comment": review.get("review_text", ""),
                "sentiment": review.get("sentiment", "Neutral"),
            }
        )

    return {
        "product_id": product_id,
        "product_name": product.get("product_name") or product.get("name"),
        "platform": analysis.get("platform", "firstcry"),
        "reviews": review_items,
        "summary": analysis.get("summary", {"positive": 0, "negative": 0, "neutral": 0, "total_reviews": 0}),
        "message": analysis.get("message"),
    }
