from fastapi import APIRouter, HTTPException

from schemas.product_schema import AnalyzeRequest, AnalysisResponse, ReviewRequest, SentimentResponse
from sentiment.analyzer import analyze_product

router = APIRouter(tags=["sentiment"])


def analyze_sentiment_text(text: str) -> str:
    cleaned = text.strip().lower()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Review text cannot be empty")

    positive_words = {"good", "great", "excellent", "love", "amazing", "awesome", "best", "fantastic", "nice"}
    negative_words = {"bad", "poor", "worst", "hate", "terrible", "awful", "disappointing", "slow", "expensive"}

    positive_count = sum(1 for word in positive_words if word in cleaned)
    negative_count = sum(1 for word in negative_words if word in cleaned)

    if positive_count > negative_count:
        return "Positive"
    if negative_count > positive_count:
        return "Negative"
    return "Neutral"


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_product_endpoint(payload: AnalyzeRequest):
    if not payload.product or not payload.product.strip():
        raise HTTPException(status_code=400, detail="Product name cannot be empty")

    try:
        return analyze_product(payload.product, platform=payload.platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


@router.post("/api/analyze", response_model=AnalysisResponse, include_in_schema=False)
async def analyze_product_alias(payload: AnalyzeRequest):
    return await analyze_product_endpoint(payload)


@router.post("/api/review-analyze", response_model=SentimentResponse, include_in_schema=False)
async def analyze_review(payload: ReviewRequest):
    if not payload.review_text or not payload.review_text.strip():
        raise HTTPException(status_code=400, detail="Review text cannot be empty")

    sentiment = analyze_sentiment_text(payload.review_text)
    return {"sentiment": sentiment}
