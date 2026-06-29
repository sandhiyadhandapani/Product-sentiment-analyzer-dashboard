from fastapi import APIRouter, HTTPException, Query

from data.products import PRODUCTS
from schemas.product_schema import Product

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

    return {"product_id": product_id, "reviews": product["reviews"]}
