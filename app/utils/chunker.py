"""
Text Chunking Utility for Aviation RAG (Production Hardened).
Orchestrates the conversion of structural sections into flat chunk objects for downstream indexing.
"""


def create_chunks(sections):
    """
    Creates standardized chunk objects from structured sections.
    Applies initial metadata enrichment for the vector database.
    """
    chunks = []

    for sec in sections:
        chunks.append({
            "text": sec["text"],
            "metadata": {
                "section": sec["section"],
                "source": "FAA",
                "aircraft": "Generic"
            }
        })

    return chunks
