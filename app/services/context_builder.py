from app.core.config import settings

def estimate_tokens(text: str) -> int:
    """
    Fast heuristic for token counting (approx 4 chars per token).
    """
    return len(text) // 4

def deduplicate_sources(sources: list[dict]) -> list[dict]:
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

def build_context(chunks: list[dict], min_score_threshold: float = 0.5):
    """
    Constructs a grounded context string using a ranking-preserved compaction pipeline.
    1. Sort by Rerank Score (Descending)
    2. Deduplicate Chunk Text
    3. Merge Sequential Sections
    4. Enforce Token Budget
    """
    if not chunks:
        return "", []

    # 1. Sort strictly by rerank_score (preserving signal)
    # Note: Cross-encoder scores can be negative, higher is better.
    sorted_chunks = sorted(chunks, key=lambda x: x.get("rerank_score", -10.0), reverse=True)

    context_parts = []
    sources = []
    seen_texts = set()
    total_tokens = 0

    # 2. Process chunks with deduplication and token gating
    for c in sorted_chunks:
        text = c["text"].strip()
        meta = c["metadata"]
        
        # Deduplicate based on text content
        if text in seen_texts:
            continue
        seen_texts.add(text)

        # 3. Token Budget Check (Strict Enforcement)
        chunk_text = f"[Section: {meta.get('section')} | Subsection: {meta.get('subsection')}]\n{text}"
        chunk_tokens = estimate_tokens(chunk_text)

        if total_tokens + chunk_tokens > settings.MAX_CONTEXT_TOKENS:
            continue
        
        total_tokens += chunk_tokens
        context_parts.append(chunk_text)

        sources.append({
            "section": meta.get("section"),
            "subsection": meta.get("subsection"),
            "chunk_id": meta.get("chunk_id"),
            "rerank_score": c.get("rerank_score"),
            "semantic_score": c.get("score")
        })

    # Join with clean separation
    context = "\n\n---\n\n".join(context_parts)

    # 4. Final Source Deduplication
    sources = deduplicate_sources(sources)

    return context, sources
