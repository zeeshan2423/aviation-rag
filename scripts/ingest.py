"""
Data Ingestion Pipeline for Aviation RAG.
Orchestrates PDF parsing, structural splitting, token chunking, and FAISS indexing.
"""

import json
import logging
import time

from langchain_community.vectorstores import FAISS
from app.services.embeddings import get_embedding_model
from app.utils.pdf_parser import load_and_merge_pdf
from app.utils.section_splitter import split_sections
from app.utils.subsection_splitter import split_subsections
from app.utils.token_chunker import split_into_token_chunks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------
# DATA LOADING
# -----------------------------
def load_augmented_data():
    """Loads supplementary grounding data from the augmented definitions vault."""
    with open("data/augmented/definitions.json", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------
# DOCUMENT PROCESSING
# -----------------------------
def process_document(sections):
    """
    Splits identified sections into the sub-section architectural layer.
    Ensures every segment maintains its parent section provenance.
    """
    final_chunks = []

    for sec in sections:
        subsections = split_subsections(sec)

        if subsections:
            final_chunks.extend(subsections)
        else:
            final_chunks.append({
                "section": sec["section"],
                "subsection": None,
                "text": sec["text"]
            })

    return final_chunks


# -----------------------------
# FAISS BUILDING (BATCHED)
# -----------------------------
def build_faiss(chunks):
    """
    Constructs a FAISS vector index from chunks in batched transactions.
    Saves the finalized index to the designated vectorstore path.
    """
    texts = [c["text"] for c in chunks]

    # 🔥 include chunk_id in metadata
    metadatas = [
        {
            **c["metadata"],
            "chunk_id": c["chunk_id"]
        }
        for c in chunks
    ]

    embedding_model = get_embedding_model()

    batch_size = 20
    db = None

    logger.info("Total chunks: %d", len(chunks))

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_metadatas = metadatas[i:i + batch_size]

        logger.info("Batch %d", i // batch_size + 1)

        if db is None:
            db = FAISS.from_texts(
                texts=batch_texts,
                embedding=embedding_model,
                metadatas=batch_metadatas
            )
        else:
            db.add_texts(
                texts=batch_texts,
                metadatas=batch_metadatas
            )

        # Respect rate limits (optional)
        if i + batch_size < len(texts):
            time.sleep(60)

    db.save_local("vectorstore")
    logger.info("✅ FAISS index saved")

    return db


# -----------------------------
# MAIN INGESTION PIPELINE
# -----------------------------
def run_ingestion():
    """
    Executes the end-to-end ingestion orchestrator:
    Merge -> Split -> Subsection -> Tokenize -> Augment -> Index.
    """
    logger.info("📄 Loading PDF...")
    text = load_and_merge_pdf("data/raw/faa_sop.pdf")

    logger.info("📑 Splitting sections...")
    sections = split_sections(text)

    logger.info("🧠 Processing subsections...")
    subsections = process_document(sections)

    logger.info("✂️ Token chunking...")
    final_chunks = split_into_token_chunks(subsections)

    logger.info("➕ Adding augmented knowledge...")
    augmented = load_augmented_data()

    for i, a in enumerate(augmented):
        a["chunk_id"] = f"aug_{i}"

    final_chunks.extend(augmented)

    logger.info("✅ Final chunks: %d", len(final_chunks))

    logger.info("⚙️ Building FAISS index...")
    build_faiss(final_chunks)


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    run_ingestion()