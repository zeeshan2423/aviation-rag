# services/query_rewriter.py

def rewrite_query(query: str) -> str:
    q = query.lower()

    if "what is" in q:
        return f"{query} definition meaning role responsibility explanation"

    if "why" in q:
        return f"{query} importance purpose benefits"

    return query