# utils/definition_extractor.py

def extract_definitions(chunks):
    definition_chunks = []

    for c in chunks:
        text = c["text"]

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