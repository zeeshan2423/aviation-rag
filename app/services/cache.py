"""
Redis Caching Service for Aviation RAG.
Handles LLM response caching and Cache Stampede protection (locking).
"""

import hashlib
import json
from typing import Any, Optional, Tuple

import redis
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger("cache_service")

# Initialize Redis client with configuration from settings
try:
    REDIS_CLIENT = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        socket_timeout=2.0
    )
except (redis.ConnectionError, redis.TimeoutError) as e:
    logger.error("Failed to initialize Redis: %s", e)
    REDIS_CLIENT = None  # Graceful degradation


def get_redis_client():
    """
    Returns the established Redis singleton client constant.
    """
    return REDIS_CLIENT


def make_key(prefix: str, data: Any) -> str:
    """
    Utility to create a deterministic MD5 hash key.
    """
    raw = prefix + ":" + json.dumps(data, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def make_llm_key(
    query: str,
    context: str,
    memory: Any,
    model_name: str,
    version: str = "v1"
) -> str:
    """
    Creates a robust cache key for LLM responses.
    Prevents cross-session leaks and stale results.
    """
    payload = {
        "v": version,
        "model": model_name,
        "q": query,
        "ctx": context,
        "mem": memory
    }
    return make_key("llm", payload)


def get_cache(key: str) -> Optional[Any]:
    """
    Retrieves a value from Redis with error handling.
    """
    if not REDIS_CLIENT:
        return None
    try:
        val = REDIS_CLIENT.get(key)
        if val:
            return json.loads(val)
    except redis.RedisError as e:
        logger.warning("Redis get execution failed: %s", e)
    return None


def set_cache(key: str, value: Any, ttl: int = 3600) -> bool:
    """
    Stores a value in Redis with error handling.
    """
    if not REDIS_CLIENT:
        return False
    try:
        REDIS_CLIENT.setex(key, ttl, json.dumps(value))
        return True
    except redis.RedisError as e:
        logger.warning("Redis set execution failed: %s", e)
    return False


def get_or_lock(key: str, ttl: int = 10) -> Tuple[Optional[Any], bool]:
    """
    Lightweight lock to prevent Cache Stampedes.
    Returns (cached_value, should_compute_flag).
    """
    if not REDIS_CLIENT:
        return None, True  # Always compute if Redis is down

    lock_key = key + ":lock"
    try:
        # setnx (set if not exists)
        if REDIS_CLIENT.setnx(lock_key, 1):
            REDIS_CLIENT.expire(lock_key, ttl)
            return None, True  # caller computes

        # Not the owner of the lock, return the current cache value (if any)
        return get_cache(key), False
    except redis.RedisError as e:
        logger.warning("Redis locking logic failed: %s", e)
        return None, True  # Fallback to live computation
def close_redis():
    """
    Safely closes the Redis connection during shutdown.
    """
    if REDIS_CLIENT:
        try:
            REDIS_CLIENT.close()
            logger.info("Redis connection closed successfully.")
        except Exception as e:
            logger.error("Error closing Redis connection: %s", e)
