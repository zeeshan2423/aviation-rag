"""
Sub-section Splitting Utility for Aviation RAG (Production Hardened).
Identifies and extracts alphabetic sub-sections (e.g., 'a. Responsibilities') from SOP text blocks.
"""

import re


def split_subsections(section):
    """
    Parses a section dictionary and splits its text into individual sub-sections.
    Resolves sub-titles and maintains cross-references to the parent section.
    """
    text = section["text"]
    section_title = section["section"]

    # Pattern captures sub-section markers like "a. Heading"
    pattern = r"(?:^|\s)([a-z]\.\s+[A-Z][^\.]+)"

    splits = re.split(pattern, text)

    structured = []

    # Iterate through splits; odds are titles, evens are content
    for i in range(1, len(splits), 2):
        subsection_title = splits[i].strip()
        content = splits[i + 1].strip()

        structured.append({
            "section": section_title,
            "subsection": subsection_title,
            "text": content
        })

    return structured
