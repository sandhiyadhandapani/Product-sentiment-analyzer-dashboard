from fastapi import APIRouter, HTTPException, Query

from data.products import PRODUCTS
from schemas.product_schema import Product
from sentiment.analyzer import analyze_product

router = APIRouter(prefix="/api", tags=["products"])


def _find_product(product_id: str):
    return next((product for product in PRODUCTS if product["id"] == product_id), None)


@router.get("/products", response_model=list[Product])
async def get_products():
    return PRODUCTS


@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/search", response_model=list[Product])
async def search_products(query: str = Query(..., description="Search by product name or category")):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    search_value = query.strip().lower()
    results = [
        product
        for product in PRODUCTS
        if search_value in product["name"].lower() or search_value in product["category"].lower()
    ]
    return results


@router.get("/products/{product_id}/reviews")
async def get_product_reviews(product_id: str):
    product = _find_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    analysis = analyze_product(product["name"], platform="firstcry")
    review_items = []
    for index, review in enumerate(analysis.get("reviews", []), start=1):
        review_items.append(
            {
                "id": f"{product_id}-{index}",
                "username": "Customer",
                "rating": review.get("rating", 0),
                "comment": review.get("review_text", ""),
                "sentiment": review.get("sentiment", "Neutral"),
            }
        )

    return {
        "product_id": product_id,
        "product_name": product["name"],
        "platform": analysis.get("platform", "firstcry"),
        "reviews": review_items,
        "summary": analysis.get("summary", {"positive": 0, "negative": 0, "neutral": 0, "total_reviews": 0}),
        "message": analysis.get("message"),
    }
