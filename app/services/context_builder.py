def deduplicate_sources(sources):
    """
    Removes duplicate source entries based on section, subsection, and chunk_id.
    """
    seen = set()
    unique = []

    for s in sources:
        key = (s["section"], s["subsection"], s["chunk_id"])
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique


def build_context(chunks, min_score_threshold=0.5):
    context_parts = []
    sources = []

    for c in chunks:
        # 🔥 Filter weak matches
        if c.get("score", 0) > min_score_threshold:
            continue

        text = c["text"]
        meta = c["metadata"]

        context_parts.append(
            f"[Section: {meta.get('section')} | Subsection: {meta.get('subsection')}]\n{text}"
        )

        sources.append({
            "section": meta.get("section"),
            "subsection": meta.get("subsection"),
            "chunk_id": meta.get("chunk_id"),
            "rerank_score": c.get("rerank_score"),
            "semantic_score": c.get("score")
        })

    context = "\n\n".join(context_parts)
    
    # Deduplicate sources before returning
    sources = deduplicate_sources(sources)

    return context, sources