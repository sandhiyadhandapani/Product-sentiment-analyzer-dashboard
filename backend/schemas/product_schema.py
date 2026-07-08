from typing import Literal

from pydantic import BaseModel, Field


class Review(BaseModel):
    # Make review model permissive to accommodate DB and scraper shapes
    id: str | None = None
    username: str | None = None
    reviewer_name: str | None = None
    rating: float | None = None
    review_rating: int | None = None
    review_text: str | None = None
    comment: str | None = None


class Product(BaseModel):
    # Accept both legacy frontend fields and DB fields
    id: str | None = None
    name: str | None = None
    product_name: str | None = None
    category: str | None = None
    price: str | None = None
    product_price: str | None = None
    image: str | None = None
    image_url: str | None = None
    product_image: str | None = None
    description: str | None = None
    rating: float | None = None
    product_rating: float | None = None
    total_ratings: int | None = None
    total_reviews: int | None = None
    reviews: list[Review] | None = None

    class Config:
        extra = "allow"


class ReviewRequest(BaseModel):
    review_text: str = Field(..., min_length=1)


class AnalyzeRequest(BaseModel):
    product: str = Field(..., min_length=1)
    platform: Literal["firstcry"] = Field(default="firstcry")


class ReviewSummary(BaseModel):
    positive: int
    negative: int
    neutral: int
    total_reviews: int


class ReviewResult(BaseModel):
    review_text: str
    rating: int
    review_rating: int | None = None
    reviewer_name: str | None = None
    review_date: str | None = None
    verified_purchase: bool | None = None
    sentiment: str
    platform: str | None = None
    score: float | None = None


class AnalysisResponse(BaseModel):
    success: bool = True
    product: str
    product_name: str | None = None
    product_image: str | None = None
    product_price: str | None = None
    product_rating: float | None = None
    total_ratings: int | None = None
    current_price: str | None = None
    original_price: float | None = None
    discount_percentage: int | None = None
    product_url: str | None = None
    rating: float | None = None
    platform: str | None = None
    total_reviews: int
    positive: int
    negative: int
    neutral: int
    reviews: list[ReviewResult]
    summary: ReviewSummary | None = None
    source_summary: dict | None = None
    dashboard_data: dict | None = None
    message: str | None = None


class SentimentResponse(BaseModel):
    sentiment: str
