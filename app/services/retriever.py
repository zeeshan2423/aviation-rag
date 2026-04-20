"""
Vector Retrieval Service for Aviation RAG.
Interfaces with FAISS (Dense) and BM25 (Sparse) retrieval mechanisms.
"""


def retrieve(query, db, k=15):
    """
    Performs standard similarity search against the FAISS vector database.
    """
    results = db.similarity_search_with_score(query, k=k)

    formatted = []
    for doc, score in results:
        formatted.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score)
        })

    return formatted


def hybrid_retrieve(query, db, bm25, k=5):
    """
    Combines FAISS (Semantic) and BM25 (Keyword) results.
    Provides a candidate pool for the cross-encoder reranker.
    """
    faiss_results = db.similarity_search_with_score(query, k=k)
    bm25_results = bm25.search(query, k=k)

    combined = []

    # Map FAISS results
    for doc, score in faiss_results:
        combined.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score)
        })

    # Map BM25 results
    for doc in bm25_results:
        combined.append({
            "text": doc["text"],
            "metadata": doc["metadata"],
            "score": 0.5  # Fixed neutral score for sparse match
        })

    return combined
