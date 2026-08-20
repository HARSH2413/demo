"""
ActionRAG SME Backend — Enterprise Knowledge Agent API.

Config-driven, resilient, and future-proof.
Swap models and services by editing .env, not code.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limiter import limiter
from app.core.logger import logger
from app.core.dependencies import _get_embedder_adapter, _get_reranker_adapter
from app.api.chat import router as chat_router
from app.api.upload import router as upload_router
from app.api.documents import router as documents_router
from app.api.drive import router as drive_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — validates config on boot."""
    logger.info("=" * 50)
    logger.info("ActionRAG Backend starting up")
    logger.info(f"  LLM Model:       {settings.LLM_MODEL_NAME}")
    logger.info(f"  Embedding Model:  {settings.EMBEDDING_MODEL_NAME}")
    logger.info(f"  Reranker Model:   {settings.RERANKER_MODEL_NAME}")
    logger.info(f"  Retrieval Top-K:  {settings.RETRIEVAL_TOP_K} → Re-rank Top-K: {settings.RERANKER_TOP_K}")
    logger.info(f"  Min Relevance:    {settings.MIN_RELEVANCE_SCORE}")
    logger.info(f"  Query Rewrite:    {'ON' if settings.ENABLE_QUERY_REWRITE else 'OFF'}")
    logger.info(f"  Rate Limit:       {settings.RATE_LIMIT_CHAT}")
    logger.info(f"  Request Timeout:  {settings.REQUEST_TIMEOUT}s")
    logger.info(f"  CORS Origins:     {settings.CORS_ORIGINS}")
    logger.info("=" * 50)

    # Pre-download & initialize models BEFORE accepting requests.
    logger.info("Pre-loading embedding model (this may take a moment on first run)...")
    _get_embedder_adapter()
    logger.info("Embedding model ready.")

    logger.info("Pre-loading reranker model...")
    _get_reranker_adapter()
    logger.info("Reranker model ready.")

    yield
    logger.info("ActionRAG Backend shutting down")


# Initialize the App
app = FastAPI(
    title="ActionRAG SME Backend",
    description="The Anti-Hallucination Knowledge Agent API",
    version="1.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — reads allowed origins from config
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
allow_credentials = "*" not in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Browsers do not allow credentialed requests with a wildcard origin.
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(documents_router)
app.include_router(drive_router)


@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "version": "1.1.0",
        "model": settings.LLM_MODEL_NAME,
        "message": "ActionRAG Backend is running. Visit /docs for the Swagger API.",
    }
