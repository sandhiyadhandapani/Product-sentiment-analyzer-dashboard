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


class SentimentResponse(BaseModel):
    sentiment: str
