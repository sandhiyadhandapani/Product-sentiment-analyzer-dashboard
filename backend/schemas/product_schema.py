from typing import Literal

from pydantic import BaseModel, Field


class Review(BaseModel):
    id: str
    username: str
    rating: float
    comment: str


class Product(BaseModel):
    id: str
    name: str
    category: str
    price: str
    image: str
    description: str
    rating: float
    reviews: list[Review]


class ReviewRequest(BaseModel):
    review_text: str = Field(..., min_length=1)


class AnalyzeRequest(BaseModel):
    product: str = Field(..., min_length=1)
    platform: Literal["amazon", "flipkart", "mixed"] = Field(default="mixed")


class ReviewSummary(BaseModel):
    positive: int
    negative: int
    neutral: int
    total_reviews: int


class ReviewResult(BaseModel):
    review_text: str
    rating: int
    review_rating: int | None = None
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
    platform: str | None = None
    total_reviews: int
    positive: int
    negative: int
    neutral: int
    reviews: list[ReviewResult]
    summary: ReviewSummary | None = None
    message: str | None = None


class SentimentResponse(BaseModel):
    sentiment: str
