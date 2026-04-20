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
METRIC_LATENCY_LIST = "metrics:latency_seconds_list"


def track_query(success: bool, latency: float) -> None:
    """
    Updates production telemetry in Redis.
    Captures success rates and rolling average latency.
    """
    if not REDIS_CLIENT:
        return

    try:
        # Increment counters
        REDIS_CLIENT.incr(METRIC_TOTAL_QUERIES)
        if success:
            REDIS_CLIENT.incr(METRIC_SUCCESS_QUERIES)

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

        # Calculate Latency Metrics
        latencies_raw = REDIS_CLIENT.lrange(METRIC_LATENCY_LIST, 0, -1)
        latencies = [float(l) for l in latencies_raw]

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        success_rate = (successes / total * 100) if total > 0 else 0

        return {
            "total_queries": total,
            "success_rate_percent": round(success_rate, 2),
            "avg_latency_seconds": round(avg_latency, 4),
            "telemetry_window_size": len(latencies),
            "status": "Healthy"
        }
    except (redis.RedisError, ValueError, TypeError) as e:
        logger.error("Failed to aggregate metrics: %s", e)
        return {"error": "Telemetry aggregation failure", "details": str(e)}
