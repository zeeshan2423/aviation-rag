import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.prompt import build_prompt
from app.services.cache import make_llm_key, get_cache, set_cache, get_or_lock

load_dotenv()

# Initialize the Gemini model
# Note: Using Gemini 3.1 Flash Lite as requested for enhanced performance
MODEL_NAME = "gemini-3.1-flash-lite-preview"

llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME,
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0
)


async def generate_answer(query, context, memory=None):
    """
    Generates an answer using the Gemini model based on context and query.
    Includes senior refinements: Locking, Negative Caching, and better Keys.
    """
    # ⚙️ 1. Generate Robust Key
    key = make_llm_key(query, context, memory, MODEL_NAME)

    # ⚙️ 2. Check Cache with Stampede Protection (get_or_lock)
    cached_val, should_compute = get_or_lock(key)
    
    if cached_val:
        return cached_val
        
    if not should_compute:
        # 🕒 Briefly wait and retry once if another process is computing
        import asyncio
        await asyncio.sleep(0.2)
        cached_val = get_cache(key)
        if cached_val:
            return cached_val

    # 🚀 3. Compute (if lock owner)
    prompt = build_prompt(query, context, memory)
    response = await llm.ainvoke(prompt)

    # Handle both string and block-list response formats
    if hasattr(response, "content") and isinstance(response.content, list) and len(response.content) > 0:
        answer = response.content[0].get("text", "")
    elif hasattr(response, "content"):
        answer = response.content
    else:
        answer = str(response)

    # ⚙️ 4. Store in Cache (with Negative Caching check)
    ttl = 3600
    if "Not found in SOP" in answer:
        ttl = 600  # Negative caching: 10 mins for missing info
    
    set_cache(key, answer, ttl=ttl)

    return answer