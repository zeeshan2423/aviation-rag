def rerank(results, query):
    query_lower = query.lower()

    for r in results:
        score = r["score"]

        # Boost definitions
        if r["metadata"].get("type") == "definition":
            score -= 0.1

        # Boost PURPOSE section
        if "purpose" in r["metadata"]["section"].lower():
            score -= 0.05

        # 🔥 Keyword boost
        if any(word in r["text"].lower() for word in query_lower.split()):
            score -= 0.02

        r["adjusted_score"] = score

    return sorted(results, key=lambda x: x["adjusted_score"])