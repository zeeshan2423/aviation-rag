"""
Aviation RAG Feedback Loop.
Captures and stores failed queries and low-confidence responses for continuous improvement.
"""

import json
from typing import Dict, Any, List
import redis

from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger("feedback_service")

# Initialize Redis client
try:
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True
    )
except Exception as e:
    logger.error("Failed to connect to Redis for feedback: %s", e)
    redis_client = None

def log_failed_query(
    query: str, 
    confidence: float, 
    reason: str,
    answer: str = "",
    retrieved_chunks: List[Dict[str, Any]] = None,
    rerank_scores: List[float] = None
) -> bool:
    """
    Logs comprehensive context for a failed or low-confidence query.
    Payload includes everything needed for root-cause analysis.
    """
    if not redis_client:
        logger.warning("Feedback logging skipped (Redis unavailable).")
        return False

    payload = {
        "query": query,
        "confidence": confidence,
        "reason": reason,
        "answer": answer,
        "retrieved_chunks_count": len(retrieved_chunks) if retrieved_chunks else 0,
        "top_rerank_scores": rerank_scores[:3] if rerank_scores else [],
        "timestamp": json.dumps({"$date": "now"}) # Placeholder or actual timestamp
    }

    try:
        # Use a rolling list for feedback logs
        redis_client.lpush("metrics:feedback_logs", json.dumps(payload))
        # Keep only the last 1000 failures to prevent memory bloat
        redis_client.ltrim("metrics:feedback_logs", 0, 999)
        
        logger.info("Feedback logged for query failure: %s (Reason: %s)", query[:50], reason)
        return True
    except Exception as e:
        logger.error("Failed to push feedback log to Redis: %s", e)
        return False
