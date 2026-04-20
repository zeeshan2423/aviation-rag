"""
Caching layer for Reranker scores in Aviation RAG.
Stores and retrieves cross-encoder scores to minimize compute latency.
"""

import hashlib
import json

import redis
from app.services.cache import get_redis_client

# Get the Redis singleton constant
REDIS_CLIENT = get_redis_client()


def get_rerank_cache(query, chunk_ids):
    """
    Retrieves cached reranker scores for a query + set of chunk IDs.
    """
    if not REDIS_CLIENT:
        return None
    try:
        # Create a unique key for this query + specific chunk search results
        ids_str = ",".join(sorted(chunk_ids))
        raw = f"rerank:{query}:{ids_str}"
        key = hashlib.md5(raw.encode()).hexdigest()

        cached = REDIS_CLIENT.get(f"cache:{key}")
        if cached:
            return json.loads(cached)
    except redis.RedisError:
        # Non-blocking; if cache fails, we simply recompute
        pass
    return None


def set_rerank_cache(query, chunk_ids, scores_dict, ttl=3600):
    """
    Stores reranker results in Redis.
    scores_dict format: {chunk_id: score}
    """
    if not REDIS_CLIENT:
        return
    try:
        ids_str = ",".join(sorted(chunk_ids))
        raw = f"rerank:{query}:{ids_str}"
        key = hashlib.md5(raw.encode()).hexdigest()

        REDIS_CLIENT.setex(f"cache:{key}", ttl, json.dumps(scores_dict))
    except redis.RedisError:
        pass
