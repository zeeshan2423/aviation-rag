"""
Production Telemetry Service for Aviation RAG.
Tracks success rates and rolling average latency using Redis as a back-end.
"""

from typing import Any, Dict

import redis
from app.services.cache import get_redis_client
from app.utils.logger import setup_logger

logger = setup_logger("metrics_service")

# Use consistent naming for Redis client constant
REDIS_CLIENT = get_redis_client()

# Production Metric Keys
METRIC_TOTAL_QUERIES = "metrics:total_queries"
METRIC_SUCCESS_QUERIES = "metrics:success_queries"
METRIC_CACHE_HITS = "metrics:cache_hits"
METRIC_LATENCY_LIST = "metrics:latency_seconds_list"
METRIC_RETRIEVAL_LOGS = "metrics:retrieval_logs"


def log_retrieval(query: str, chunks: list[dict], rerank_scores: list[float]) -> None:
    """
    Logs raw retrieval data for auditing and future feedback loops.
    Captures query intent and the quality of matched candidates.
    """
    if not REDIS_CLIENT:
        return

    import json
    import time

    payload = {
        "timestamp": time.time(),
        "query": query,
        "results_count": len(chunks),
        "top_scores": rerank_scores[:5],  # Log top 5 scores for density check
        "chunk_ids": [c.get("metadata", {}).get("chunk_id") for c in chunks[:5]]
    }

    try:
        # Store as a JSON string in a rolling Redis list (last 1000 logs)
        REDIS_CLIENT.lpush(METRIC_RETRIEVAL_LOGS, json.dumps(payload))
        REDIS_CLIENT.ltrim(METRIC_RETRIEVAL_LOGS, 0, 999)
        logger.debug("Retrieval telemetry logged for query: %s", query)
    except redis.RedisError as e:
        logger.warning("Retrieval logging failed: %s", e)


def track_query(success: bool, latency: float, cache_hit: bool = False) -> None:
    """
    Updates production telemetry in Redis.
    Captures success rates, cache efficiency, and rolling average latency.
    """
    if not REDIS_CLIENT:
        return

    try:
        # Increment counters
        REDIS_CLIENT.incr(METRIC_TOTAL_QUERIES)
        if success:
            REDIS_CLIENT.incr(METRIC_SUCCESS_QUERIES)
        if cache_hit:
            REDIS_CLIENT.incr(METRIC_CACHE_HITS)

        # Push latency (seconds) to a rolling window (last 100 queries)
        REDIS_CLIENT.lpush(METRIC_LATENCY_LIST, latency)
        REDIS_CLIENT.ltrim(METRIC_LATENCY_LIST, 0, 99)
    except redis.RedisError as e:
        # Metrics are non-blocking; we log failure but never crash the request flow
        logger.warning("Telemetry update failed: %s", e)


def get_metrics() -> Dict[str, Any]:
    """
    Aggregates system-wide performance metrics for observability.
    Used by the /metrics management endpoint.
    """
    if not REDIS_CLIENT:
        return {"error": "Redis unavailable for metrics"}

    try:
        total_raw = REDIS_CLIENT.get(METRIC_TOTAL_QUERIES)
        total = int(total_raw) if total_raw else 0

        successes_raw = REDIS_CLIENT.get(METRIC_SUCCESS_QUERIES)
        successes = int(successes_raw) if successes_raw else 0

        hits_raw = REDIS_CLIENT.get(METRIC_CACHE_HITS)
        hits = int(hits_raw) if hits_raw else 0

        # Calculate Latency Metrics
        latencies_raw = REDIS_CLIENT.lrange(METRIC_LATENCY_LIST, 0, -1)
        latencies = [float(l) for l in latencies_raw]

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        success_rate = (successes / total * 100) if total > 0 else 0
        hit_rate = (hits / total * 100) if total > 0 else 0

        return {
            "total_queries": total,
            "success_rate_percent": round(success_rate, 2),
            "cache_hit_rate_percent": round(hit_rate, 2),
            "avg_latency_seconds": round(avg_latency, 4),
            "telemetry_window_size": len(latencies),
            "status": "Healthy"
        }
    except (redis.RedisError, ValueError, TypeError) as e:
        logger.error("Failed to aggregate metrics: %s", e)
        return {"error": "Telemetry aggregation failure", "details": str(e)}
