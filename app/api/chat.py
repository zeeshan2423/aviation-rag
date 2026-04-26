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
from app.services.query_rewriter import rewrite_query, decompose_query
from app.services.hybrid import hybrid_retrieve
from app.services.reranker import rerank
from app.services.context_builder import build_context
from app.services.llm import generate_answer
from app.services.metrics import track_query, log_retrieval
from app.services.guardrails import validate_response
from app.services.feedback import log_failed_query
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger("chat_api")
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, chat_req: ChatRequest):
    """
    Main conversational endpoint with production security and precision layers.
    Flow: Rewrite -> Decompose -> Hybrid Retrieve -> Prune -> Rerank -> LLM -> Guardrails -> Feedback.
    """
    start_time = time.time()
    db = request.app.state.db

    try:
        # 1. Query Rewriting
        rewritten_root = await rewrite_query(chat_req.query, chat_req.session_id)

        # 2. Query Decomposition
        sub_queries = await decompose_query(rewritten_root)
        
        # 3. Multi-Query Hybrid Retrieval
        semaphore = asyncio.Semaphore(4)
        async def semaphored_retrieve(q):
            async with semaphore:
                try:
                    return await asyncio.wait_for(hybrid_retrieve(q, db, k=20), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Retrieval timed out for sub-query: %s", q)
                    return []
                except Exception as e:
                    logger.error("Retrieval failure for sub-query %s: %s", q, e)
                    return []

        retrieval_tasks = [semaphored_retrieve(q) for q in sub_queries]
        results_per_query = await asyncio.gather(*retrieval_tasks)
        
        all_candidates = []
        seen_chunk_ids = set()
        for q_candidates in results_per_query:
            for cand in q_candidates:
                cid = cand["metadata"].get("chunk_id")
                if cid and cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    all_candidates.append(cand)

        # ✂️ CANDIDATE PRUNING
        all_candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
        pruned_candidates = all_candidates[:50]

        # 4. Reranking
        reranked_chunks = rerank(rewritten_root, pruned_candidates)
        
        # 📊 Logging Retrieval Quality
        log_retrieval(
            query=rewritten_root,
            chunks=reranked_chunks,
            rerank_scores=[c["rerank_score"] for c in reranked_chunks]
        )

        # 🔢 Score Calculation
        top_score = reranked_chunks[0]["rerank_score"] if reranked_chunks else 0.0
        confidence = min(1.0, max(0.0, top_score / settings.CAUTION_RERANK_SCORE))

        # 🔥 PRODUCTION SAFETY: Tiered Confidence Gates
        # Tier 1: Absolute Reject (< 0.3 Confidence)
        if not reranked_chunks or confidence < 0.3:
            logger.info("Query rejected by safety gate (Low Confidence: %s)", confidence)
            log_failed_query(
                query=rewritten_root, 
                confidence=confidence, 
                reason="low_confidence_reject",
                retrieved_chunks=reranked_chunks,
                rerank_scores=[c["rerank_score"] for c in reranked_chunks]
            )
            track_query(success=True, latency=time.time() - start_time)
            return ChatResponse(
                answer="Not found in SOP",
                sources=[],
                confidence=float(confidence),
                retrieval_score=float(top_score)
            )

        # 5. Context Preparation
        final_context, source_list = build_context(reranked_chunks)

        # 6. LLM Answer Generation
        answer, is_hit = await generate_answer(chat_req.query, final_context, memory=chat_req.session_id)

        # 🔢 COMPOSITE CONFIDENCE CALCULATION (Phase 3.1)
        normalized_rerank = min(1.0, max(0.0, top_score / settings.CAUTION_RERANK_SCORE))
        source_score = min(1.0, len(source_list) / 2.0)  # 2+ sources = 100% signal
        length_score = min(1.0, len(answer.split()) / 50.0)  # 50+ words = 100% signal
        
        composite_confidence = (0.6 * normalized_rerank) + (0.2 * source_score) + (0.2 * length_score)
        confidence = float(min(1.0, max(0.0, composite_confidence)))

        # 🛡️ GUARDRAILS: Signal-based Post-Validation
        guardrail_result = validate_response(answer, confidence, source_list)
        final_warning = guardrail_result["warning"]

        # Tier 2: Cautionary UX (0.3 <= Confidence < 0.6 or Guardrail Warning)
        if not guardrail_result["is_valid"]:
            # If guardrail says invalid, escalate to warning if not already set
            if not final_warning:
                final_warning = {"type": "GUARDRAIL_FLAG", "message": "Safety check failed. Please verify with SOP."}
            
            log_failed_query(
                query=rewritten_root,
                confidence=confidence,
                reason=guardrail_result["reason"] or "guardrail_fail",
                answer=answer,
                retrieved_chunks=reranked_chunks,
                rerank_scores=[c["rerank_score"] for c in reranked_chunks]
            )

        track_query(success=True, latency=time.time() - start_time, cache_hit=is_hit)

        return ChatResponse(
            answer=answer,
            sources=[SourceMetadata(**s) for s in source_list],
            confidence=confidence,
            retrieval_score=float(top_score),
            warning=final_warning
        )

    except Exception as e:
        logger.error("Chat Endpoint Failure: %s", e, exc_info=True)
        track_query(success=False, latency=time.time() - start_time)
        raise HTTPException(
            status_code=500,
            detail="An internal processing error occurred."
        ) from e
