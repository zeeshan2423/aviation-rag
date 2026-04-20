from sentence_transformers import CrossEncoder
from app.services.rerank_cache import get_rerank_cache, set_rerank_cache

model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def rerank(results, query):
    chunk_ids = [r.get("metadata", {}).get("chunk_id", "") for r in results]
    
    # 🕒 1. Check Cache
    cached_scores = get_rerank_cache(query, chunk_ids)
    if cached_scores:
        for r in results:
            cid = r.get("metadata", {}).get("chunk_id", "")
            r["rerank_score"] = cached_scores.get(cid, 0.0)
        return sorted(results, key=lambda x: x["rerank_score"], reverse=True)

    # 🚀 2. Compute if Miss
    pairs = [(query, r["text"]) for r in results]
    scores = model.predict(pairs).tolist()

    scores_to_cache = {}
    for r, s in zip(results, scores):
        # 🔥 Section-Based Boosting (Production Polish)
        final_score = s
        section_name = r.get("metadata", {}).get("section", "").upper()
        if "SUMMARY" in section_name:
            final_score -= 1.5
            
        r["rerank_score"] = final_score
        cid = r.get("metadata", {}).get("chunk_id", "")
        scores_to_cache[cid] = final_score

    # 🕒 3. Store in Cache
    set_rerank_cache(query, chunk_ids, scores_to_cache)

    return sorted(results, key=lambda x: x["rerank_score"], reverse=True)