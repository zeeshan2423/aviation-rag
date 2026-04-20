import json
import hashlib
from app.services.cache import r

def get_rerank_cache(query, chunk_ids):
    """
    Retrieves cached reranker scores for a query + set of chunk IDs.
    """
    try:
        # Create a unique key for this query + specific chunk search results
        ids_str = ",".join(sorted(chunk_ids))
        raw = f"rerank:{query}:{ids_str}"
        key = hashlib.md5(raw.encode()).hexdigest()
        
        cached = r.get(f"cache:{key}")
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    return None

def set_rerank_cache(query, chunk_ids, scores_dict, ttl=3600):
    """
    Stores reranker results in Redis.
    scores_dict format: {chunk_id: score}
    """
    try:
        ids_str = ",".join(sorted(chunk_ids))
        raw = f"rerank:{query}:{ids_str}"
        key = hashlib.md5(raw.encode()).hexdigest()
        
        r.setex(f"cache:{key}", ttl, json.dumps(scores_dict))
    except Exception:
        pass
