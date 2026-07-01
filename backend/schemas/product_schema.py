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


class ReviewResult(BaseModel):
    review: str
    sentiment: str
    score: float


class AnalysisResponse(BaseModel):
    product: str
    total_reviews: int
    positive: int
    negative: int
    neutral: int
    reviews: list[ReviewResult]
    message: str | None = None


class SentimentResponse(BaseModel):
    sentiment: str
