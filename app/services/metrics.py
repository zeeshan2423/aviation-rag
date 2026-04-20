import time
from app.services.cache import r

METRIC_TOTAL_QUERIES = "metrics:total_queries"
METRIC_CACHE_HITS = "metrics:cache_hits"
METRIC_LATENCY_LIST = "metrics:latency_ms_list"

def track_request(latency_ms: int, cache_hit: bool):
    """
    Updates production metrics in Redis.
    """
    try:
        # Increment total queries
        r.incr(METRIC_TOTAL_QUERIES)
        
        # Increment hits if applicable
        if cache_hit:
            r.incr(METRIC_CACHE_HITS)
            
        # Push latency to a list (keep last 500 for rolling avg)
        r.lpush(METRIC_LATENCY_LIST, latency_ms)
        r.ltrim(METRIC_LATENCY_LIST, 0, 499)
    except Exception as e:
        # Metrics should never crash the main request flow
        print(f"Metrics Error: {e}")

def get_metrics():
    """
    Aggregates metrics for the GET /metrics endpoint.
    """
    try:
        total = int(r.get(METRIC_TOTAL_QUERIES) or 0)
        hits = int(r.get(METRIC_CACHE_HITS) or 0)
        
        latencies = r.lrange(METRIC_LATENCY_LIST, 0, -1)
        latencies = [int(l) for l in latencies]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        return {
            "total_queries": total,
            "cache_hits": hits,
            "cache_hit_rate_percent": round(hit_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "rolling_window_queries": len(latencies)
        }
    except Exception as e:
        return {"error": str(e)}
