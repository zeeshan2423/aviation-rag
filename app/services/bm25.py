"""
BM25 Retrieval Engine for Keyword search.
Uses the rank_bm25 library for efficient lexical matching.
"""

from rank_bm25 import BM25Okapi


class BM25Retriever:
    """
    Standard BM25 keyword search interface.
    Handles tokenization and scoring for document retrieval.
    """
    def __init__(self, documents):
        """
        Initializes the index with provided documents.
        """
        self.texts = [d["text"] for d in documents]
        self.tokenized = [t.lower().split() for t in self.texts]
        self.bm25 = BM25Okapi(self.tokenized)
        self.documents = documents

    def search(self, query, k=5):
        """
        Performs lexical search and returns top-k matching documents.
        """
        scores = self.bm25.get_scores(query.lower().split())
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

        return [self.documents[i] for i in top_idx]
