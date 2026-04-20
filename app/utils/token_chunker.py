"""
Semantic Token-aware Chunking Utility for Aviation RAG (Production Hardened).
Leverages RecursiveCharacterTextSplitter to create optimized context segments from SOP sub-sections.
Includes validation logic to filter out noise or truncated fragments.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.utils.cleaner import clean_text

# Configure the semantic splitter with SOP-optimized separators
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100,
    separators=[
        "\n\n", "\n", ".", " ", ""
    ]
)


def is_valid_chunk(text: str) -> bool:
    """
    Validates the quality of a generated chunk.
    Filters out fragments that are too short or likely truncated mid-word/term.
    """
    if len(text) < 50:
        return False
    # Avoid chunks that end with likely truncated technical suffixes
    if text.endswith(("mode", "procedur", "operatio")):
        return False
    return True


def split_into_token_chunks(section_chunks):
    """
    Orchestrates the granular splitting of section-based chunks into token-optimized segments.
    Applies text cleaning and structural validation to each child fragment.
    """
    final_chunks = []

    for idx, chunk in enumerate(section_chunks):
        splits = splitter.split_text(chunk["text"])

        for i, s in enumerate(splits):
            cleaned = clean_text(s)

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
