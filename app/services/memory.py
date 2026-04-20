"""
Conversational Memory Logic for Aviation RAG.
Manages session-specific history storage and windowing for retrieval-augmented generation.
"""

from typing import List


class ChatMemory:
    """
    Industry-standard conversational memory manager.
    Tracks the last N turns of a conversation for context-aware reasoning.
    """
    def __init__(self, window_size: int = 5):
        self.history: List[str] = []
        self.window_size = window_size

    def add_turn(self, query: str, answer: str) -> None:
        """
        Adds a new Q&A turn to the history and maintains the window size.
        """
        turn = f"User: {query}\nAssistant: {answer}"
        self.history.append(turn)
        if len(self.history) > self.window_size:
            self.history.pop(0)

    def __str__(self) -> str:
        """
        Returns a formatted string representation of the conversation history.
        """
        if not self.history:
            return "No previous history."
        return "\n---\n".join(self.history)
