"""
Aviation SOP Chat API Endpoint.
Handles conversational RAG flow: rewriting, hybrid retrieval, reranking, and generation.
"""

import time
import asyncio
from typing import List

from fastapi import APIRouter, Request, HTTPException

from app.models.schema import ChatRequest, ChatResponse, SourceMetadata
from app.utils.limiter import limiter
from app.services.query_rewriter import rewrite_query
from app.services.hybrid import hybrid_retrieve
from app.services.reranker import rerank
from app.services.context_builder import build_context
from app.services.llm import generate_answer
from app.services.metrics import track_query, log_retrieval
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger("chat_api")
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, chat_req: ChatRequest):
    """
    Main conversational endpoint with production security and precision layers.
    Flow: Rewrite -> Decompose -> Hybrid Retrieve (multi-query) -> Rerank -> Confidence Gate -> LLM Generate.
    """
    start_time = time.time()
    db = request.app.state.db

    try:
        # 1. Query Rewriting (Contextual intelligence)
        rewritten_root = await rewrite_query(
            chat_req.query,
            chat_req.session_id
        )

        # 2. Query Decomposition (Controlled)
        sub_queries = await decompose_query(rewritten_root)
        
        # 3. Multi-Query Hybrid Retrieval (Parallelized across sub-queries)
        retrieval_tasks = [hybrid_retrieve(q, db, k=10) for q in sub_queries]
        results_per_query = await asyncio.gather(*retrieval_tasks)
        
        all_candidates = []
        seen_chunk_ids = set()
        
        for q_candidates in results_per_query:
            for cand in q_candidates:
                cid = cand["metadata"].get("chunk_id")
                if cid and cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    all_candidates.append(cand)

        # 4. Reranking (Precision booster)
        # Rescore relative to the rewritten root intended query
        reranked_chunks = rerank(rewritten_root, all_candidates)
        
        # 📊 Logging Retrieval Quality for Phase 3 Feedback Loop
        log_retrieval(
            query=rewritten_root,
            chunks=reranked_chunks,
            rerank_scores=[c["rerank_score"] for c in reranked_chunks]
        )

        # 🔥 PRODUCTION SAFETY: Confidence Threshold Gate
        if not reranked_chunks or reranked_chunks[0]["rerank_score"] < settings.MIN_RERANK_SCORE:
            score = reranked_chunks[0]['rerank_score'] if reranked_chunks else 0.0
            logger.info("Query rejected by safety gate. Top score: %s", score)
            track_query(success=True, latency=time.time() - start_time)
            return ChatResponse(
                answer="Not found in SOP",
                sources=[],
                confidence=0.0,
                retrieval_score=float(score)
            )

        # 5. Context Preparation (Ranking-Preserved Compaction)
        # build_context now handles sorting and token budget strictly
        final_context, source_list = build_context(reranked_chunks)

        # 6. LLM Answer Generation
        answer, is_hit = await generate_answer(
            chat_req.query,
            final_context,
            memory=chat_req.session_id
        )

        # ✨ DUAL THRESHOLD: Precision Warning logic
        top_score = reranked_chunks[0]["rerank_score"]
        if top_score < settings.CAUTION_RERANK_SCORE:
            answer += "\n\nNOTE: This information may be incomplete."

        # 📊 Metrics and Scoring Mapping
        # Normalize score for V1 confidence (e.g., 5.0+ = 100%)
        confidence = min(1.0, max(0.0, top_score / settings.CAUTION_RERANK_SCORE))
        
        track_query(success=True, latency=time.time() - start_time, cache_hit=is_hit)

        return ChatResponse(
            answer=answer,
            sources=[SourceMetadata(**s) for s in source_list],
            confidence=float(confidence),
            retrieval_score=float(top_score)
        )

    except Exception as e:
        logger.error("Chat Endpoint Failure: %s", e, exc_info=True)
        track_query(success=False, latency=time.time() - start_time)
        raise HTTPException(
            status_code=500,
            detail="An internal processing error occurred."
        ) from e
