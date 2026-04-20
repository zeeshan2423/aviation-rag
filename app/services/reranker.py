from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
from app.services.rerank_cache import get_rerank_cache, set_rerank_cache
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger("reranker_service")

# Initialize the Cross-Encoder model (once at startup)
try:
    model = CrossEncoder(settings.RERANK_MODEL_NAME)
    logger.info(f"Reranking model '{settings.RERANK_MODEL_NAME}' successfully loaded.")
except Exception as e:
    logger.error(f"Failed to load reranking model: {e}")
    model = None

def rerank(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rescores retrieve candidates using a Cross-Encoder for top-tier precision.
    Includes section-based boosting and Redis caching for low-latency repeats.
    """
    if not model or not chunks:
        return chunks

    # 1. Prepare pairs [Query, ChunkText] for batch prediction
    pairs = [[query, c["text"]] for c in chunks]
    
    try:
        # Check cache if available to bypass compute
        cached_scores = get_rerank_cache(query, [c["text"] for c in chunks])
        if cached_scores and len(cached_scores) == len(chunks):
            scores = cached_scores
        else:
            scores = model.predict(pairs)
            set_rerank_cache(query, [c["text"] for c in chunks], scores.tolist())
    except Exception as e:
        logger.warning(f"Reranker scoring failed, falling back to raw similarity: {e}")
        return chunks

    # 2. Add scores and apply production boosting logic
    for i, chunk in enumerate(chunks):
        score = float(scores[i])
        
        # 🔥 SECTION-BASED BOOSTING (Critical for Industry Standard)
        # Penalize summaries to prioritize high-value SOP / Derived Knowledge
        if "SUMMARY" in chunk.get("metadata", {}).get("section", "").upper():
            score -= 1.5
            
        chunk["rerank_score"] = score

    # 3. Sort by new score (descending)
    sorted_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
    return sorted_chunks
