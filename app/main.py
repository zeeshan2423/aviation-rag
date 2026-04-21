"""
Main Entry Point for Aviation RAG API.
Handles application lifecycle, middleware configuration, and global exception handling.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.vectorstores import FAISS

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.utils.limiter import limiter
from app.services.embeddings import get_embedding_model
from app.services.hybrid import init_bm25
from app.utils.logger import logger
from app.core.config import settings

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Industry-standard startup/shutdown handling.
    Performs environment validation and initializes search engines.
    """
    try:
        # 🔥 STEP 3: STARTUP VALIDATION (Professional Safety Gate)
        logger.info("Validating environment...")
        required_vars = ["GEMINI_API_KEY", "VOYAGE_API_KEY"]
        for var in required_vars:
            if not getattr(settings, var):
                raise RuntimeError(f"Missing critical env variable: {var}")
        logger.info("Environment valid ✅")

        # 🚀 STEP 4: PRELOAD EVERYTHING (Professional Preloading)
        logger.info("Loading FAISS Knowledge Base...")
        db = FAISS.load_local(
            settings.VEC_STORE_PATH,
            get_embedding_model(),
            allow_dangerous_deserialization=True
        )
        app_instance.state.db = db
        logger.info("FAISS Loaded ✅")

        # Extract all documents from FAISS to initialize BM25
        logger.info("Initializing BM25 Sparse Engine...")
        docstore = getattr(db, "docstore")
        raw_docs = getattr(docstore, "_dict").values()
        all_chunks = [
            {"text": d.page_content, "metadata": d.metadata}
            for d in raw_docs
        ]
        init_bm25(all_chunks)
        logger.info("BM25 Ready ✅")
        
        logger.info("Engines ready for production traffic.")
    except Exception as e:
        logger.error("Critical Startup Error: %s", e)
        raise e

    yield

app = FastAPI(
    title="Aviation SOP RAG API",
    description="Production-grade conversational AI for aviation SOPs.",
    version="1.0.0",
    lifespan=lifespan
)

# 🌐 CORS Middleware (Essential for Industry Adoption)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this to specific domains in real production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🛡️ Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Ensures a standardized JSON response for any unhandled service errors.
    """
    logger.error("Unhandled Exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": (
                "A service-level error occurred. Please consult the "
                "metrics dashboard or logs."
            )
        }
    )

# Register the rate limiter in the application state
app.state.limiter = limiter

app.include_router(chat_router)
app.include_router(health_router)
app.include_router(metrics_router)

@app.get("/")
def read_root():
    """Root endpoint verifying API availability."""
    message = (
        settings.title if hasattr(settings, "title")
        else "Aviation SOP RAG API Active"
    )
    return {"message": message}
