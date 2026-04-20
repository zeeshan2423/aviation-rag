import time
from fastapi import APIRouter, Request
from app.models.schema import ChatRequest, ChatResponse
from app.services.reranker import rerank
from app.services.context_builder import build_context
from app.services.llm import generate_answer
from app.services.query_rewriter import rewrite_query_with_memory
from app.services.memory_store import get_memory
from app.services import hybrid
from app.utils.logger import logger
from app.utils.limiter import limiter

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(req: ChatRequest, request: Request):
    start_time = time.time()
    
    memory = get_memory(req.session_id)
    memory_context = memory.get_context()

    # 🚀 1. Await Rewriting
    rewritten_query = await rewrite_query_with_memory(req.query, memory_context)
    
    # 🔍 2. Hybrid Retrieval (Dense FAISS + Sparse BM25)
    db = request.app.state.db
    candidates = hybrid.hybrid_retrieve(rewritten_query, db, hybrid.BM25, k=12)
    
    # 🎯 3. Cross-Encoder Reranking
    reranked = rerank(candidates, rewritten_query)

    # 🔥 Answer Threshold Gate
    MIN_RERANK_SCORE = 2.0
    CAUTION_RERANK_SCORE = 5.0
    
    top_chunks = reranked[:3]
    top_score = top_chunks[0].get("rerank_score", -10) if top_chunks else -10
    
    if not top_chunks or top_score < MIN_RERANK_SCORE:
        answer = "Not found in SOP"
        sources = []
    else:
        context, sources = build_context(top_chunks)
        if not context:
            answer = "Not found in SOP"
            sources = []
        else:
            answer = await generate_answer(req.query, context, memory_context)
            
            if top_score < CAUTION_RERANK_SCORE:
                answer += "\n\n⚠️ NOTE: This information may be incomplete based on your query's precision."
                
            memory.add(req.query, answer)

    # 📊 Observability & Metrics
    total_latency_ms = int((time.time() - start_time) * 1000)
    
    from app.services.metrics import track_request
    track_request(latency_ms=total_latency_ms, cache_hit=False)

    logger.info({
        "event": "chat_request",
        "session_id": req.session_id,
        "query": req.query,
        "rewritten": rewritten_query,
        "latency_ms": total_latency_ms,
        "top_score": round(top_score, 4)
    })

    return ChatResponse(answer=answer, sources=sources)