"""
Aviation RAG Performance Evaluation Utility.
Measures Accuracy, Retrieval Hit Rate, and End-to-End Latency.
"""

import json
import time
import asyncio
import os
from typing import List, Dict, Any

from langchain_community.vectorstores import FAISS

from app.services.embeddings import get_embedding_model
from app.services.query_rewriter import rewrite_query
from app.services.hybrid import hybrid_retrieve, HybridSearchOrchestrator
from app.services.reranker import rerank
from app.services.context_builder import build_context
from app.services.llm import generate_answer
from app.core.config import settings

# --- Setup Utilities ---

def initialize_engines():
    """Initializes FAISS and BM25 Orchestrator for evaluation."""
    print("🚀 Loading search engines...")
    db = FAISS.load_local(
        settings.VEC_STORE_PATH,
        get_embedding_model(),
        allow_dangerous_deserialization=True
    )
    
    # Initialize BM25 (Hybrid Orchestrator)
    docstore = getattr(db, "docstore")
    raw_docs = getattr(docstore, "_dict").values()
    all_chunks = [
        {"text": d.page_content, "metadata": d.metadata}
        for d in raw_docs
    ]
    HybridSearchOrchestrator.initialize_bm25(all_chunks)
    
    return db

def retrieval_hit(top_chunks: List[Dict[str, Any]], expected_keywords: List[str]) -> bool:
    """Checks if any expected keyword is present in the top-k retrieved chunks."""
    if not expected_keywords:
        return True # N/A for out_of_scope
    
    text = " ".join([c["text"] for c in top_chunks])
    return any(kw.lower() in text.lower() for kw in expected_keywords)

# --- Core Evaluation Runner ---

async def run_evaluation():
    db = initialize_engines()
    
    dataset_path = "evaluation/dataset.json"
    if not os.path.exists(dataset_path):
        print(f"❌ Error: {dataset_path} not found.")
        return

    with open(dataset_path) as f:
        dataset = json.load(f)

    results = []
    print(f"\n📊 Starting Evaluation on {len(dataset)} queries...\n" + "-"*50)

    for item in dataset:
        question = item["question"]
        expected_keywords = item["expected_keywords"] or []
        
        start_time = time.time()

        # 1. Pipeline Execution
        rewritten = await rewrite_query(question, "eval_session")
        candidates = await hybrid_retrieve(rewritten, db)
        reranked = rerank(rewritten, candidates)
        top_chunks = reranked[:3]

        context = build_context(top_chunks)
        answer, is_hit = await generate_answer(question, context, memory="eval_session")

        latency = time.time() - start_time

        # 2. Scoring Logic
        # Accuracy: Keyword match in the generated answer
        score = 0
        for kw in expected_keywords:
            if kw.lower() in answer.lower():
                score += 1
        
        accuracy = score / len(expected_keywords) if expected_keywords else (
            1.0 if "Not found" in answer or "sorry" in answer.lower() else 0.0
        )

        # Retrieval Success: Hit in the context
        ret_success = retrieval_hit(top_chunks, expected_keywords)

        results.append({
            "question": question,
            "accuracy": accuracy,
            "retrieval_success": ret_success,
            "latency": latency,
            "cache_hit": is_hit
        })
        
        print(f"Q: {question}")
        print(f"   Accuracy: {accuracy:.2f} | Latency: {latency:.2f}s | Retrieval Hit: {ret_success}")

    # 3. Summary Analytics
    avg_accuracy = sum(r["accuracy"] for r in results) / len(results)
    avg_latency = sum(r["latency"] for r in results) / len(results)
    hit_rate = sum(1 for r in results if r["retrieval_success"]) / len(results)

    print("\n" + "="*20 + " SUMMARY " + "="*20)
    print(f"Avg Accuracy:    {avg_accuracy:.2f}")
    print(f"Avg Latency:     {avg_latency:.2f}s")
    print(f"Retrieval Hit Rate: {hit_rate * 100:.1f}%")
    print("="*49)

if __name__ == "__main__":
    asyncio.run(run_evaluation())
