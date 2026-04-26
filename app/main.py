import time
import asyncio
import uuid
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
from app.utils.logger import logger, request_id_ctx
from app.services.cache import get_redis_client, close_redis
from app.core.config import settings

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Hardened application lifecycle.
    Includes startup retries, granular timing, and graceful shutdown.
    """
    startup_start = time.time()
    startup_status = "success"
    
    try:
        # 1. Environment Validation
        logger.info("Validating environment...")
        required_vars = ["GEMINI_API_KEY", "VOYAGE_API_KEY"]
        for var in required_vars:
            if not getattr(settings, var):
                raise RuntimeError(f"Missing critical env variable: {var}")
        
        # 2. Redis Startup Resilience (Retry Loop)
        logger.info("Connecting to Redis...")
        redis_ready = False
        for i in range(5):
            client = get_redis_client()
            if client:
                try:
                    client.ping()
                    redis_ready = True
                    logger.info("Redis connection established ✅")
                    break
                except Exception as e:
                    logger.warning("Redis connection attempt %s failed. Retrying...", i+1, extra={"extra_data": {"retry": i+1, "error": str(e)}})
                    await asyncio.sleep(2 ** i) # Exponential backoff
            else:
                break
        
        if not redis_ready:
            logger.error("Redis connection failed after retries. Continuing in DEGRADED mode (no cache/feedback).", extra={"extra_data": {"status": "degraded"}})
            startup_status = "degraded"

        # 3. Granular Cold Start Preloading
        # - Embeddings
        emb_start = time.time()
        embedding_model = get_embedding_model()
        emb_time = (time.time() - emb_start) * 1000
        logger.info("Embeddings loaded in %.2fms ✅", emb_time)

        # - FAISS Index
        faiss_start = time.time()
        db = FAISS.load_local(
            settings.VEC_STORE_PATH,
            embedding_model,
            allow_dangerous_deserialization=True
        )
        app_instance.state.db = db
        faiss_time = (time.time() - faiss_start) * 1000
        logger.info("FAISS Index loaded in %.2fms ✅", faiss_time)

        # - BM25 Engine
        bm25_start = time.time()
        docstore = getattr(db, "docstore")
        raw_docs = getattr(docstore, "_dict").values()
        all_chunks = [{"text": d.page_content, "metadata": d.metadata} for d in raw_docs]
        init_bm25(all_chunks)
        bm25_time = (time.time() - bm25_start) * 1000
        logger.info("BM25 Engine ready in %.2fms ✅", bm25_time)

        total_startup = (time.time() - startup_start) * 1000
        logger.info("Startup sequence complete. Status: %s. Total time: %.2fms", startup_status, total_startup, extra={"extra_data": {"total_ms": total_startup, "status": startup_status}})

    except Exception as e:
        logger.error("Critical Startup Failure: %s", e, exc_info=True)
        raise e

    yield
    
    # 4. Graceful Shutdown
    logger.info("Shutdown sequence initiated...")
    close_redis()

app = FastAPI(
    title="Aviation SOP RAG API",
    description="Production-grade conversational AI for aviation SOPs.",
    version="1.0.0",
    lifespan=lifespan
)

# 🆔 Request ID Middleware (Correlation ID for tracing)
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled Exception at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "A service-level error occurred."
        }
    )

app.state.limiter = limiter
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(metrics_router)

@app.get("/")
def read_root():
    return {"message": "Aviation SOP RAG API Active"}
