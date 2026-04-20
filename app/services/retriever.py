def retrieve(query, db, k=15):
    results = db.similarity_search_with_score(query, k=k)

    formatted = []

    for doc, score in results:
        formatted.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })

    return formatted

def hybrid_retrieve(query, db, bm25, k=5):
    faiss_results = db.similarity_search_with_score(query, k=k)
    bm25_results = bm25.search(query, k=k)

    combined = []

    for doc, score in faiss_results:
        combined.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })

    for doc in bm25_results:
        combined.append({
            "text": doc["text"],
            "metadata": doc["metadata"],
            "score": 0.5  # neutral score
        })

    return combined