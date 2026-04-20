"""
Text Sanitization Utility for Aviation RAG (Production Hardened).
Provides regex-based cleaning to remove document-specific noise like AC numbers and dates.
"""

import re


def clean_text(text: str) -> str:
    """
    Standardizes and cleans raw document text.
    Removes AC identifiers, normalizes whitespace, and strips leading punctuation.
    """
    # Remove Advisory Circular identifiers and date patterns
    text = re.sub(r"AC\s*\d+-\d+[A-Z]?\s*\d+/\d+/\d+", "", text)
    # Normalize multiple whitespaces/newlines to a single space
    text = re.sub(r"\s+", " ", text)
    # Remove leading periods (common in PDF artifacts)
    text = re.sub(r"^\.\s*", "", text)

    return text.strip()
