from contextlib import asynccontextmanager
from fastapi import FastAPI
from langchain_community.vectorstores import FAISS

from app.api.chat import router as chat_router
from app.utils.limiter import limiter
from app.services.embeddings import get_embedding_model
from app.services.hybrid import init_bm25
from app.services.metrics import get_metrics
from app.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Industry-standard startup/shutdown handling.
    Initializes FAISS and BM25 once during application launch.
    """
    # 1. Load FAISS database
    logger.info("Initializing Search Engines (FAISS + BM25)...")
    db = FAISS.load_local(
        "vectorstore",
        get_embedding_model(),
        allow_dangerous_deserialization=True
    )
    app.state.db = db
    
    # 2. Extract all documents from FAISS to initialize BM25
    raw_docs = db.docstore._dict.values()
    all_chunks = [
        {"text": d.page_content, "metadata": d.metadata} 
        for d in raw_docs
    ]
    
    # 3. Initialize Global BM25
    init_bm25(all_chunks)
    
    yield

app = FastAPI(lifespan=lifespan)

# Register the rate limiter in the application state
app.state.limiter = limiter

app.include_router(chat_router)

@app.get("/metrics")
def metrics():
    """
    Exposes production metrics for observability.
    """
    return get_metrics()

@app.get("/")
def read_root():
    return {"message": "Aviation SOP RAG API Active"}