"""
Aviation SOP Chat API Endpoint.
Handles conversational RAG flow: rewriting, hybrid retrieval, reranking, and generation.
"""

import time
from typing import List

from fastapi import APIRouter, Request, HTTPException

from app.models.schema import ChatRequest, ChatResponse, SourceMetadata
from app.utils.limiter import limiter
from app.services.query_rewriter import rewrite_query
from app.services.hybrid import hybrid_retrieve
from app.services.reranker import rerank
from app.services.context_builder import build_context
from app.services.llm import generate_answer
from app.services.metrics import track_query
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger("chat_api")
router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, chat_req: ChatRequest):
    """
    Main conversational endpoint with production security and precision layers.
    Flow: Rewrite -> Hybrid Retrieve -> Rerank -> Confidence Gate -> LLM Generate.
    """
    start_time = time.time()

    try:
        # 1. Query Rewriting (Contextual intelligence)
        rewritten_query = await rewrite_query(
            chat_req.query,
            chat_req.session_id
        )

        # 2. Hybrid Retrieval (Recall booster)
        db = request.app.state.db
        candidates = hybrid_retrieve(rewritten_query, db)

        # 3. Reranking (Precision booster)
        reranked_chunks = rerank(rewritten_query, candidates)

        # 🔥 PRODUCTION SAFETY: Confidence Threshold Gate
        if not reranked_chunks or reranked_chunks[0]["rerank_score"] < settings.MIN_RERANK_SCORE:
            score = reranked_chunks[0]['rerank_score'] if reranked_chunks else 'N/A'
            logger.info("Query rejected by safety gate. Top score: %s", score)
            track_query(success=True, latency=time.time() - start_time)
            return ChatResponse(
                answer="Not found in SOP",
                sources=[]
            )

        # 4. Context Preparation
        top_chunks = reranked_chunks[:3]
        final_context = build_context(top_chunks)

        # 5. LLM Answer Generation
        answer = await generate_answer(
            chat_req.query,
            final_context,
            memory=chat_req.session_id
        )

        # ✨ DUAL THRESHOLD: Precision Warning logic
        if reranked_chunks[0]["rerank_score"] < settings.CAUTION_RERANK_SCORE:
            answer += "\n\nNOTE: This information may be incomplete."

        # 6. Response Formatting
        sources: List[SourceMetadata] = [
            SourceMetadata(
                section=c["metadata"].get("section", "Unknown"),
                subsection=c["metadata"].get("subsection", "Unknown"),
                chunk_id=c["metadata"].get("chunk_id", "Unknown")
            ) for c in top_chunks
        ]

        # 📊 Metrics Tracking
        track_query(success=True, latency=time.time() - start_time)

        return ChatResponse(
            answer=answer,
            sources=sources
        )

    except Exception as e:
        logger.error("Chat Endpoint Failure: %s", e, exc_info=True)
        track_query(success=False, latency=time.time() - start_time)
        raise HTTPException(
            status_code=500,
            detail="An internal processing error occurred."
        ) from e
