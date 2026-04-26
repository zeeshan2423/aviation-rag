"""
Hybrid Retrieval Engine for Aviation RAG.
Orchestrates Sparse (BM25) and Dense (FAISS) search with deduplication logic.
Uses a singleton pattern to maintain engine state without global keywords.
"""

from typing import List, Dict, Any, Optional, Set

from langchain_community.vectorstores import FAISS
from app.services.bm25 import BM25Retriever
from app.utils.logger import setup_logger

logger = setup_logger("hybrid_retrieval")


class HybridSearchOrchestrator:
    """
    Encapsulates the state and logic for hybrid retrieval.
    """
    _bm25: Optional[BM25Retriever] = None

    @classmethod
    def initialize_bm25(cls, all_chunks: List[Dict[str, Any]]) -> None:
        """
        Initializes the sparse retriever instance within the orchestrator.
        """
        try:
            cls._bm25 = BM25Retriever(all_chunks)
            logger.info("BM25 Retrieval Engine initialized with %d chunks.", len(all_chunks))
        except (ValueError, KeyError, TypeError) as e:
            logger.error("Data error during BM25 initialization: %s", e)
            cls._bm25 = None
        except RuntimeError as e:
            # Final safety net for BM25 initialization (Standardized for Production)
            logger.error("Unexpected failure during BM25 initialization: %s", e)
            cls._bm25 = None

    @classmethod
    def get_bm25(cls) -> Optional[BM25Retriever]:
        """Returns the current BM25 instance."""
        return cls._bm25


def init_bm25(all_chunks: List[Dict[str, Any]]) -> None:
    """
    Legacy wrapper for orchestrator initialization.
    """
    HybridSearchOrchestrator.initialize_bm25(all_chunks)


import asyncio

def _faiss_search(query: str, db: FAISS, k: int) -> List[Dict[str, Any]]:
    """Internal sync helper for semantic search."""
    results = []
    try:
        faiss_results = db.similarity_search_with_score(query, k=k)
        for doc, score in faiss_results:
            results.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
    except (RuntimeError, ValueError) as e:
        logger.warning("Failure in semantic FAISS retrieval: %s", e)
    return results


def _bm25_search(query: str, k: int) -> List[Dict[str, Any]]:
    """Internal sync helper for keyword search."""
    results = []
    bm25 = HybridSearchOrchestrator.get_bm25()
    if bm25:
        try:
            bm_results = bm25.search(query, k=k)
            for d in bm_results:
                results.append({
                    "text": d["text"],
                    "metadata": d["metadata"],
                    "score": float(d.get("score", 0.0))
                })
        except (KeyError, ValueError, RuntimeError) as e:
            logger.warning("Failure in keyword BM25 retrieval: %s", e)
    else:
        logger.warning("BM25 Engine not initialized, skipping sparse retrieval.")
    return results


async def hybrid_retrieve(query: str, db: FAISS, k: int = 10, alpha: float = 0.5) -> List[Dict[str, Any]]:
    """
    Orchestrates a parallel hybrid search combining Semantic (Dense) and Keyword (Sparse) retrieval.
    Includes Min-Max normalization to ensure unbiased merging of disparate scoring systems.
    """
    # Execute both searches in parallel using threads
    faiss_task = asyncio.to_thread(_faiss_search, query, db, k)
    bm25_task = asyncio.to_thread(_bm25_search, query, k)
    
    dense_results, sparse_results = await asyncio.gather(faiss_task, bm25_task)
    
    # --- Normalization Logic ---
    
    # 1. Normalize Dense Scores (FAISS L2 distance -> Similarity 0-1)
    # distance 0 = similarity 1.0; distance increases = similarity decreases
    for d in dense_results:
        # Simple inversion for distance-to-similarity conversion
        d["norm_score"] = 1.0 / (1.0 + d["score"])

    # 2. Normalize Sparse Scores (BM25 raw -> Similarity 0-1)
    if sparse_results:
        max_sparse = max(s["score"] for s in sparse_results)
        min_sparse = min(s["score"] for s in sparse_results)
        denom = (max_sparse - min_sparse) if max_sparse != min_sparse else 1.0
        for s in sparse_results:
            s["norm_score"] = (s["score"] - min_sparse) / denom
    
    # Merge and calculate combined score
    results: List[Dict[str, Any]] = []
    seen_chunk_ids: Set[str] = set()
    
    # Process Dense
    for cand in dense_results:
        chunk_id = cand["metadata"].get("chunk_id")
        if chunk_id:
            seen_chunk_ids.add(chunk_id)
            cand["combined_score"] = cand["norm_score"] * alpha
            results.append(cand)
            
    # Process Sparse with deduplication
    for cand in sparse_results:
        chunk_id = cand["metadata"].get("chunk_id")
        if not chunk_id:
            continue
            
        if chunk_id in seen_chunk_ids:
            # Update existing candidate score
            for existing in results:
                if existing["metadata"].get("chunk_id") == chunk_id:
                    existing["combined_score"] += cand["norm_score"] * (1 - alpha)
                    break
        else:
            seen_chunk_ids.add(chunk_id)
            cand["combined_score"] = cand["norm_score"] * (1 - alpha)
            results.append(cand)

    # Use combined_score as the final score for downstream pruning/sorting
    for r in results:
        r["score"] = r["combined_score"]

    logger.debug("Parallel hybrid retrieval (normalized) finished with %d candidates.", len(results))
    return results
