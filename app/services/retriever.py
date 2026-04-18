from app.services.query_rewriter import rewrite_query

def retrieve(query, db, k=15):
    query = rewrite_query(query)
    results = db.similarity_search_with_score(query, k=k)

    formatted = []

    for doc, score in results:
        formatted.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })

    return formatted