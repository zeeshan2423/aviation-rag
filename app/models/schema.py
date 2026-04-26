"""
Aviation RAG Data Schemas.
Defines standard Pydantic models for chat requests, responses, and source attribution.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """
    Standard schema for a chat request.
    """
    query: str = Field(..., example="What are Pilot Monitoring responsibilities?")
    session_id: str = Field(default="default_session", example="user_123")

class SourceMetadata(BaseModel):
    """
    Schema for document source attribution.
    """
    section: str = "Unknown"
    subsection: Optional[str] = "N/A"
    chunk_id: str

class ChatResponse(BaseModel):
    """
    Standard schema for a production chat response.
    """
    answer: str
    sources: List[SourceMetadata] = Field(default_factory=list)
    confidence: float = 0.0
    retrieval_score: float = 0.0
    warning: Optional[str] = None
