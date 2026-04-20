"""
Prompt Engineering Service for Aviation RAG.
Constructs strictly grounded LLM instructions using document context and session history.
"""

from typing import Optional
from app.services.memory_store import get_history


def build_prompt(query: str, context: str, session_id: Optional[str] = None) -> str:
    """
    Constructs the final grounding prompt for the LLM.
    Enforces strict adherence to the provided context and maintains conversational tone.
    """
    history = "No previous history."
    if session_id:
        # Fetch actual history object for the session
        history = str(get_history(session_id))

    return f"""
    You are an expert Aviation SOP Assistant. 
    Your mission is to provide accurate, safe, and context-grounded answers based on Standard Operating Procedures.

    ### STRICT GROUNDING RULES:
    - Answer ONLY using the information provided in the [Context] section below.
    - If the answer is not explicitly present in the [Context], respond exactly with: "Not found in SOP".
    - Do NOT assume, add external knowledge, or interpolate between chapters.
    - Use a professional, technical, and objective tone.

    ### CONVERSATION HISTORY:
    {history}

    ### DATA CONTEXT (SOP Segments):
    {context}

    ### LATEST QUERY:
    {query}

    ### FINAL GROUNDED ANSWER:
    """
