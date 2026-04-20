"""
Section Splitting Utility for Aviation RAG (Production Hardened).
Identifies and extracts major numbered sections (e.g., '1. INTRODUCTION.') using regex patterns.
"""

import re


def split_sections(text):
    """
    Parses a single cleaned text block into a list of structured section dictionaries.
    Maintains titles and content for downstream granular chunking.
    """
    # Pattern for numbered sections (e.g., "1. HEADING.")
    pattern = r"\n?\d+\.\s+[A-Z][A-Z\s]+\."

    sections = re.split(pattern, text)
    titles = re.findall(pattern, text)

    structured = []

    # Iterate through results starting after the first split
    # (which is usually empty or header noise)
    for i, content in enumerate(sections[1:]):
        structured.append({
            "section": titles[i].strip(),
            "text": content.strip()
        })

    return structured
