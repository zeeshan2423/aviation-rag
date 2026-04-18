from app.services.reranker import rerank
from langchain_community.vectorstores import FAISS
from app.services.embeddings import get_embedding_model
from app.services.retriever import retrieve



def load_faiss():
    return FAISS.load_local(
        "vectorstore",
        get_embedding_model(),
        allow_dangerous_deserialization=True
    )


if __name__ == "__main__":
    db = load_faiss()

    query = "What is pilot monitoring?"

    results = retrieve(query, db)
    reranked = rerank(results, query)

    for r in reranked[:3]:
        print("\n---")
        print("Score:", r["score"])
        print("Text:", r["text"][:200])
        print("Section:", r["metadata"]["section"])
        print("Chunk ID:", r["metadata"]["chunk_id"])