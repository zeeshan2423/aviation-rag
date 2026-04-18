# utils/token_chunker.py

from app.utils.cleaner import clean_text
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,         # increase size
    chunk_overlap=100,
    separators=[
        "\n\n", "\n", ".", " ", ""
    ]
)

def is_valid_chunk(text):
    if len(text) < 50:
        return False
    if text.endswith(("mode", "procedur", "operatio")):  # crude truncation check
        return False
    return True

def split_into_token_chunks(section_chunks):
    final_chunks = []

    for idx, chunk in enumerate(section_chunks):
        splits = splitter.split_text(chunk["text"])

        for i, s in enumerate(splits):
            cleaned = clean_text(s)  # 🔥 APPLY HERE

            if is_valid_chunk(cleaned):
                final_chunks.append({
                "chunk_id": f"{idx}_{i}",
                "text": cleaned,
                "metadata": {
                    "section": chunk["section"],
                    "subsection": chunk["subsection"],
                    "source": "FAA",
                    "aircraft": "Generic"
                }
            })

    return final_chunks