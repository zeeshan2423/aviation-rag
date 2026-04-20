# 🧩 System Design & Architecture

This document provides a deep-dive into the structural design of the **Aviation SOP Conversational RAG System**. It outlines the flow from raw data ingestion to high-assurance response generation.

---

## 🗺️ High-Level Architecture

The following diagram illustrates the structured, layered approach of the system, designed to maximize precision and ensure safety through deterministic gating.

```mermaid
flowchart TD
    A[User / Client] --> B[FastAPI /chat Endpoint]

    B --> C[Session Memory Store]
    C --> D[Query Rewriter - Gemini 3.1 Flash]

    D --> E{Hybrid Retriever}
    E --> E1[FAISS - Semantic Search]
    E --> E2[BM25 - Keyword Search]

    E1 --> F[Candidate Pool]
    E2 --> F

    F --> G[Cross-Encoder Reranker]
    G --> H[Section-Based Boosting]

    H --> I{Threshold Gate / Safety Layer}
    I -- Score < 2.0 --> J[Reject Response]
    I -- Score > 2.0 --> K[Context Builder]

    K --> L[LLM - Gemini 3.1 Flash]
    L --> M[Response Refiner]

    M --> N[Redis Caching Layer]
    N --> O[Production Metrics Engine]
    O --> P[Final Response + Sources]

    P --> B

    subgraph Data Pipeline
        Q[Raw FAA SOP PDFs]
        R[Recursive Section Splitting]
        S[Vector Store - FAISS]
        T[Inverted Index - BM25]
    end

    Q --> R
    R --> S
    R --> T

    style L fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#bbf,stroke:#333,stroke-width:2px
    style N fill:#bfb,stroke:#333,stroke-width:2px
    style I fill:#f66,stroke:#333,stroke-width:2px
```

---

## 🧠 Core Design Principles

### 1. Hybrid Retrieval (Recall Maximization)
We combine **Semantic Similarity** (FAISS) with **Keyword Correspondence** (BM25). In technical domains like aviation, semantic search alone often misses exact acronym matches (e.g., "PM" for Pilot Monitoring). Our hybrid approach ensures both conceptual and literal matches are captured.

### 2. Decision Logic & Safety (Determinism)
Unlike prototype RAG systems that rely solely on the LLM to decide relevance, our system implements a **hard safety gate** at the reranking stage. By using a Cross-Encoder as a "Referee", we can deterministically reject queries with low relevance scores, effectively eliminating hallucination risks for out-of-scope requests.

### 3. Conversational Intelligence
The **Query Rewriting** layer utilizes **Gemini 3.1 Flash** to transform ambiguous, multi-turn user queries into self-contained retrieval statements. This ensures that retrieval always targeted the original intent, even when users use pronouns like "it" or "their".

### 4. Production-Grade Observability
A dedicated **Metrics Engine** tracks every request's latency, cache status, and confidence scores in Redis. This metrics suite is exposed via the `/metrics` endpoint, enabling real-time monitoring and threshold tuning.

---

## ⚡ Performance Optimization Summary
- **Latency Control**: High-latency Cross-Encoder scores are cached in Redis to accelerate repeated interactions.
- **Async Concurrency**: The entire pipeline is built on FastAPI's `async` architecture to handle concurrent user sessions efficiently.
- **Weight Loading**: All models (FAISS, BM25, Cross-Encoder) are initialized once at the application's lifespan start, ensuring sub-500ms retrieval overhead.

---

## 🎯 Target Use Cases
- Pilot training and procedure verification.
- Simulation support for Pilot Flying (PF) and Pilot Monitoring (PM) responsibilities.
- Rapid lookup of FAA safety standards and procedural checklists.
落
