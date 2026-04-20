from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

async def get_session_id(request: Request) -> str:
    """
    Extracts the session_id from the JSON body to allow per-session rate limiting.
    Falls back to remote IP if session_id is missing.
    """
    try:
        body = await request.json()
        return body.get("session_id", get_remote_address(request))
    except Exception:
        return get_remote_address(request)

# Initialize the rate limiter with session-based granularity support
limiter = Limiter(key_func=get_session_id)
