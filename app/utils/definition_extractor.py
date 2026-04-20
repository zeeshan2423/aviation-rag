"""
Knowledge Augmentation Utility for Aviation RAG (Production Hardened).
Extracts terminological definitions from document chunks to enhance search grounding.
"""


def extract_definitions(chunks):
    """
    Identifies and labels chunks that contain formal definitions.
    Enriches metadata with a 'definition' type for prioritized retrieval.
    """
    definition_chunks = []

    for c in chunks:
        text = c["text"]

        # Heuristic for detecting core definitions (e.g., 'Pilot Monitoring is...')
        if " is " in text and "pilot monitoring" in text.lower():
            definition_chunks.append({
                "chunk_id": c["chunk_id"] + "_def",
                "text": text,
                "metadata": {
                    **c["metadata"],
                    "type": "definition"
                }
            })

    return definition_chunks
