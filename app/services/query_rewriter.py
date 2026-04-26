"""
Query Rewriting Service for Aviation RAG.
Resolves conversational context and pronouns to create standalone search queries.
Features Redis-backed caching with stampede protection.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.cache import make_key, set_cache, get_or_lock
from app.core.config import settings
from app.utils.logger import setup_logger
from app.services.memory_store import get_history

logger = setup_logger("query_rewriter")

from app.services.llm import get_llm

# Initialize the rewriting model using the abstraction factory
llm = get_llm()


def should_decompose(query: str) -> bool:
    """
    Heuristic gate based on Senior Engineer specification.
    Decomposes if query contains conjunctions or at least one question mark.
    """
    return any([
        " and " in query.lower(),
        " or " in query.lower(),
        len(query.split("?")) > 1,
        len(query.split(" and ")) > 1
    ])


async def decompose_query(query: str) -> list[str]:
    """
    Decomposes a complex query into simpler sub-queries for broader retrieval.
    Includes a maximum limit of 3 sub-queries and string-based deduplication.
    """
    if not should_decompose(query):
        return [query]

    prompt = f"""
    You are an Aviation SOP Query Decomposition Assistant.
    Goal: Break down the following user query into at most {settings.MAX_SUB_QUERIES} standalone, simpler sub-queries for retrieval.
    Rule: Return only the sub-queries, one per line. Do not add numbering or extra text.
    
    User Query:
    {query}
    
    Sub-Queries:
    """

    try:
        response = await llm.ainvoke(prompt)
        sub_queries = [q.strip() for q in str(response.content).strip().split("\n") if q.strip()]
        
        # Deduplicate and limit to max N queries
        unique_queries = list(dict.fromkeys(sub_queries))[:settings.MAX_SUB_QUERIES]
        
        logger.info("Query decomposed into: %s", unique_queries)
        return unique_queries
    except Exception as e:
        logger.error("Query decomposition failed: %s", e)
        return [query]


async def rewrite_query(query: str, session_id: str) -> str:
    """
    Rewrites a conversational query into a standalone search query.
    Resolves pronouns by examining the multi-turn session history.
    """
    # 1. Fetch conversational history for this session
    history = get_history(session_id)
    if not history:
        return query

    # 2. Build Cache Key
    key_payload = {
        "model": settings.LLM_MODEL_NAME,
        "q": query,
        "hist": str(history)  # Convert object to string for JSON serialization
    }
    key = make_key("rewrite", key_payload)

    # 3. Check Cache (Stampede protection)
    try:
        cached_val, should_compute = get_or_lock(key)
        if cached_val:
            return str(cached_val)
    except Exception as e:
        # Catching Exception here and logging because this is a non-blocking 
        # cache layer that should fallback to computation.
        logger.warning("Rewriter cache lookup failed: %s", e)
        should_compute = True

    if not should_compute:
        return query  # Fallback

    # 4. Perform Rewriting
    prompt = f"""
    You are a query rewriting assistant for an Aviation SOP RAG system.
    Goal: Rewrite the user's latest query into a standalone, descriptive search question.
    Rule: Resolve pronouns (it, they, those) using the provided conversation history.
    
    Conversation History:
    {history}
    
    Latest User Query:
    {query}
    
    Rewritten Search Query:
    """

    try:
        response = await llm.ainvoke(prompt)
        rewritten = str(response.content).strip()

        # 5. Store result
        set_cache(key, rewritten, ttl=1800)
        return rewritten
    except Exception as e:
        # Standardize logging
        logger.error("Query rewriting failed: %s", e)
        return query  # Fallback to original query
