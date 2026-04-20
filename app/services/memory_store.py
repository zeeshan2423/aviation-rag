"""
Global Session Store for Aviation RAG.
Provides local persistence for conversational history objects across API calls.
"""

from typing import Dict
from app.services.memory import ChatMemory
from app.utils.logger import setup_logger

logger = setup_logger("memory_store")

# Global singleton store for user sessions
_memory_store: Dict[str, ChatMemory] = {}


def get_history(session_id: str) -> ChatMemory:
    """
    Retrieves or initializes the conversational memory for a given session.
    """
    if session_id not in _memory_store:
        logger.info("Initializing new conversational session: %s", session_id)
        _memory_store[session_id] = ChatMemory()
    return _memory_store[session_id]
