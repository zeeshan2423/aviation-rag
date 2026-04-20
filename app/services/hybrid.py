from app.services.bm25 import BM25Retriever

# Global instance initialized during app startup
BM25 = None

def init_bm25(all_chunks):
    """
    Initializes the global BM25 instance with the provided document chunks.
    Called once during application startup.
    """
    global BM25
    BM25 = BM25Retriever(all_chunks)


def hybrid_retrieve(query, db, bm25, k=10):
    """
    Combines results from semantic (FAISS) and keyword (BM25) search.
    Deduplicates results based on 'chunk_id' to ensure unique content.
    """
    # 1. Fetch Candidates (k=10 from both)
    faiss_results = db.similarity_search_with_score(query, k=k)
    bm_results = bm25.search(query, k=k)

    seen = set()
    combined = []

    # 2. Process FAISS results (prioritize Dense hits)
    for doc, score in faiss_results:
        cid = doc.metadata.get("chunk_id")
        if cid in seen:
            continue
        seen.add(cid)
        combined.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
            "origin": "faiss"
        })

    # 3. Process BM25 results (Keyword hits)
    for d in bm_results:
        cid = d["metadata"].get("chunk_id")
        if cid in seen:
            continue
        seen.add(cid)
        combined.append({
            "text": d["text"],
            "metadata": d["metadata"],
            "score": 0.5,  # Neutral baseline as BM25 scores aren't normalized with FAISS
            "origin": "bm25"
        })

    return combined
