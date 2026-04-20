"""
Rate Limiting Configuration for Aviation RAG.
Provides session-aware limiting to prevent API abuse and ensure fair resource allocation.
"""

import json
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


async def get_session_id(request: Request) -> str:
    """
    Extracts the session_id from the JSON body to allow per-session rate limiting.
    Falls back to remote IP if session_id is missing or body is unreadable.
    """
    try:
        body = await request.json()
        return body.get("session_id", get_remote_address(request))
    except (json.JSONDecodeError, ValueError, RuntimeError):
        # Body might be empty or unreadable; fallback to remote address (Production Hardened)
        return get_remote_address(request)


# Initialize the rate limiter with session-based granularity support
limiter = Limiter(key_func=get_session_id)
