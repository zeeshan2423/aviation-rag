"""
LLM Generation Service for Aviation RAG.
Interfaces with Google Gemini for grounded answer generation.
Features Redis-backed caching with stampede protection and negative caching logic.
"""

import asyncio
from typing import Any, Optional

import redis
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.prompt import build_prompt
from app.services.cache import make_llm_key, get_cache, set_cache, get_or_lock
from app.core.config import settings
from app.utils.logger import setup_logger

logger = setup_logger("llm_service")

# Initialize the Gemini model using centralized settings
# Using Gemini 3.1 Flash as identified in technical specifications
llm = ChatGoogleGenerativeAI(
    model=settings.LLM_MODEL_NAME,
    google_api_key=settings.GEMINI_API_KEY,
    temperature=0
)


async def generate_answer(query: str, context: str, memory: Optional[Any] = None) -> str:
    """
    Generates an answer using the Gemini model based on context and query.
    Includes production refinements: Locking, Negative Caching, and type-safe responses.
    """
    # ⚙️ 1. Generate Robust Key
    key = make_llm_key(query, context, memory, settings.LLM_MODEL_NAME)

    # ⚙️ 2. Check Cache with Stampede Protection
    try:
        cached_val, should_compute = get_or_lock(key)

        if cached_val:
            logger.info("Cache hit for LLM response.")
            return str(cached_val)

        if not should_compute:
            # 🕒 Briefly wait and retry once if another process is computing
            await asyncio.sleep(0.2)
            cached_val = get_cache(key)
            if cached_val:
                return str(cached_val)
    except redis.RedisError as e:
        # Non-blocking cache layer should fallback to computation
        logger.warning("Cache lookup failed, falling back to live computation: %s", e)
        should_compute = True

    # 🚀 3. Compute (if lock owner or fallback)
    try:
        prompt = build_prompt(query, context, memory)
        response = await llm.ainvoke(prompt)

        # Handle various response formats from the model
        if hasattr(response, "content"):
            if isinstance(response.content, list) and len(response.content) > 0:
                answer = response.content[0].get("text", "")
            else:
                answer = str(response.content)
        else:
            answer = str(response)

        # ⚙️ 4. Store in Cache (with Negative Caching logic)
        ttl = 3600
        if "Not found in SOP" in answer:
            ttl = 600  # Negative caching: 10 mins for missing info

        set_cache(key, answer, ttl=ttl)
        return answer

    except (ValueError, TypeError, redis.RedisError) as e:
        # Standardized error reporting for known potential failure points
        logger.error("LLM Generation Failed (Infrastructure/Data): %s", e, exc_info=True)
        return "I'm sorry, an internal reasoning error occurred. Please try again shortly."
    except RuntimeError as e:
        # Final safety net for unexpected issues (Standardized for Production)
        logger.error("Unexpected LLM Generation Failure: %s", e, exc_info=True)
        return "An unexpected error occurred. Please try again."
