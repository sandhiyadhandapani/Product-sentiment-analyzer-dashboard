from fastapi import APIRouter, HTTPException, Query

from database import build_dashboard_payload, get_product_by_id, get_product_reviews, list_products

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard_default():
    products = await list_products(limit=1)
    if not products:
        raise HTTPException(status_code=404, detail="No products found")
    return await get_dashboard(products[0]["id"])


@router.get("/dashboard/{product_id}")
async def get_dashboard(product_id: str):
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    reviews, _ = await get_product_reviews(product_id, limit=100, page=1)
    return build_dashboard_payload(product, reviews)


@router.get("/products/{product_id}/reviews")
async def get_product_reviews_collection(
    product_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    sentiment: str | None = Query(default=None),
    rating: int | None = Query(default=None, ge=1, le=5),
    sort: str = Query(default="desc"),
):
    product = await get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    reviews, total = await get_product_reviews(
        product_id,
        limit=limit,
        page=page,
        sentiment=sentiment,
        rating=rating,
        sort=sort,
    )
    return {
        "product_id": product_id,
        "reviews": reviews,
        "count": len(reviews),
        "total": total,
        "page": page,
        "limit": limit,
    }
