from fastapi import APIRouter, HTTPException

from data.analysis_store import get_analysis_history
from schemas.product_schema import AnalyzeRequest, AnalysisResponse, ReviewRequest, SentimentResponse
from sentiment.analyzer import analyze_product, analyze_product_async, analyze_sentiment

router = APIRouter(tags=["sentiment"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_product_endpoint(payload: AnalyzeRequest):
    if not payload.product or not payload.product.strip():
        raise HTTPException(status_code=400, detail="Product name cannot be empty")

    try:
        return await analyze_product_async(payload.product, platform=payload.platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive handling
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


@router.get("/history", response_model=list[AnalysisResponse])
async def get_analysis_history_endpoint():
    return get_analysis_history()


@router.post("/api/analyze", response_model=AnalysisResponse, include_in_schema=False)
async def analyze_product_alias(payload: AnalyzeRequest):
    return await analyze_product_endpoint(payload)


@router.post("/api/review-analyze", response_model=SentimentResponse, include_in_schema=False)
async def analyze_review(payload: ReviewRequest):
    if not payload.review_text or not payload.review_text.strip():
        raise HTTPException(status_code=400, detail="Review text cannot be empty")

    sentiment = analyze_sentiment(payload.review_text)
    return {"sentiment": sentiment["sentiment"]}
