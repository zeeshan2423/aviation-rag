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


def hybrid_retrieve(query: str, db: FAISS, k: int = 10) -> List[Dict[str, Any]]:
    """
    Orchestrates a hybrid search combining Semantic (Dense) and Keyword (Sparse) retrieval.
    Includes chunk-level deduplication and strict type-safe results.
    """
    results: List[Dict[str, Any]] = []
    seen_chunk_ids: Set[str] = set()

    # 1. Execute FAISS Semantic Search
    try:
        faiss_results = db.similarity_search_with_score(query, k=k)
        for doc, score in faiss_results:
            chunk_id = doc.metadata.get("chunk_id")
            if chunk_id and chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                results.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)  # Cast to Python float for JSON compatibility
                })
    except (RuntimeError, ValueError) as e:
        logger.warning("Failure in semantic FAISS retrieval: %s", e)

    # 2. Execute BM25 Keyword Search
    bm25 = HybridSearchOrchestrator.get_bm25()
    if bm25:
        try:
            bm_results = bm25.search(query, k=k)
            for d in bm_results:
                chunk_id = d["metadata"].get("chunk_id")
                if chunk_id and chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    results.append({
                        "text": d["text"],
                        "metadata": d["metadata"],
                        "score": float(d.get("score", 0.0))
                    })
        except (KeyError, ValueError, RuntimeError) as e:
            logger.warning("Failure in keyword BM25 retrieval: %s", e)
    else:
        logger.warning("BM25 Engine not initialized, skipping sparse retrieval.")

    logger.debug("Hybrid retrieval finished with %d deduplicated candidates.", len(results))
    return results
