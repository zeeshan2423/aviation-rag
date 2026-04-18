# app/utils/chunker.py

def create_chunks(sections):
    """Create chunks from sections"""
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