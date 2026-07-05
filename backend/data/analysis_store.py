from collections import deque

from schemas.product_schema import AnalysisResponse

ANALYSIS_HISTORY: deque[dict] = deque(maxlen=50)


def save_analysis_result(result: dict) -> dict:
    validated = AnalysisResponse.model_validate(result)
    data = validated.model_dump()
    ANALYSIS_HISTORY.appendleft(data)
    return data


def get_analysis_history() -> list[dict]:
    return list(ANALYSIS_HISTORY)
