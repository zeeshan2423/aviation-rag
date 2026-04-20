import redis
import json
import hashlib
import time

r = redis.Redis(host='localhost', port=6379, db=0)


def make_key(prefix, data):
    raw = prefix + ":" + json.dumps(data, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def make_llm_key(query, context, memory, model_name, version="v1"):
    """
    Creates a robust cache key for LLm responses.
    Prevents cross-session leaks and stale results when the model/context changes.
    """
    payload = {
        "v": version,
        "model": model_name,
        "q": query,
        "ctx": context,
        "mem": memory
    }
    return make_key("llm", payload)


def get_cache(key):
    val = r.get(key)
    if val:
        return json.loads(val)
    return None


def set_cache(key, value, ttl=3600):
    r.setex(key, ttl, json.dumps(value))


def get_or_lock(key, ttl=10):
    """
    Implementation of a lightweight lock to prevent Cache Stampedes.
    If the key is not in cache, the first request acquires a lock.
    """
    lock_key = key + ":lock"
    # setnx (set if not exists)
    if r.setnx(lock_key, 1):
        r.expire(lock_key, ttl)
        return None, True  # caller computes
    
    # Not the owner of the lock, return the current cache value (if any)
    return get_cache(key), False