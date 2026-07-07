from collections import deque
import logging

from schemas.product_schema import AnalysisResponse
from database import save_product_with_reviews

logger = logging.getLogger(__name__)

ANALYSIS_HISTORY: deque[dict] = deque(maxlen=50)


def save_analysis_result(result: dict) -> dict:
    validated = AnalysisResponse.model_validate(result)
    data = validated.model_dump()
    ANALYSIS_HISTORY.appendleft(data)
    
    # Note: persistence into MongoDB is performed by the analyzer (async)
    # Keep analysis history in-memory only to avoid running nested event loops here.
    
    return data


def get_analysis_history() -> list[dict]:
    return list(ANALYSIS_HISTORY)
