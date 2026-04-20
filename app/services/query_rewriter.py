import asyncio
from google.generativeai import GenerativeModel
from app.services.cache import make_key, get_cache, set_cache, get_or_lock

# Using Gemini 3.1 Flash Lite for query disambiguation
MODEL_NAME = "gemini-3.1-flash-lite-preview"
model = GenerativeModel(MODEL_NAME)


async def rewrite_query_with_memory(query: str, memory: str) -> str:
    """
    Rewrites a conversational query into a standalone search query.
    Refinements: Locking, Better Keys.
    """
    # ⚙️ 1. Generate Key (including model)
    key_payload = {
        "model": MODEL_NAME,
        "q": query,
        "mem": memory
    }
    key = make_key("rewrite", key_payload)

    # ⚙️ 2. Check Cache with Stampede Protection
    cached_val, should_compute = get_or_lock(key)
    
    if cached_val:
        return cached_val
        
    if not should_compute:
        await asyncio.sleep(0.2)
        cached_val = get_cache(key)
        if cached_val:
            return cached_val

    # 🚀 3. Compute
    prompt = f"""
You are a query rewriting assistant.

Your task:
- Rewrite the user's query into a standalone question
- Resolve pronouns using conversation history

Conversation:
{memory}

User Query:
{query}

Rewritten Query:
"""

    response = await model.generate_content_async(prompt)
    rewritten = response.text.strip()

    # ⚙️ 4. Store in Cache
    set_cache(key, rewritten)

    return rewritten