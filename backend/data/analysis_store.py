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
    
    # Also save to MongoDB
    try:
        import asyncio
        product_payload = {
            "product_name": data.get("product_name"),
            "product_url": data.get("product_url"),
            "product_image": data.get("product_image"),
            "price": data.get("product_price"),
            "rating": data.get("product_rating"),
            "total_reviews": data.get("total_reviews"),
            "platform": data.get("platform"),
        }
        reviews_payload = data.get("reviews", [])
        
        # Run async MongoDB save in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            mongo_result = loop.run_until_complete(save_product_with_reviews(product_payload, reviews_payload))
            if mongo_result:
                logger.info(f"Product saved to MongoDB: {data.get('product_name')}")
            else:
                logger.warning("MongoDB save returned None - check connection")
        except Exception as e:
            logger.error(f"Failed to save to MongoDB: {e}")
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"MongoDB save error: {e}")
    
    return data


def get_analysis_history() -> list[dict]:
    return list(ANALYSIS_HISTORY)
