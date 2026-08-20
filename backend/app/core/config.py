"""
Centralized, type-safe configuration.

To swap models for production, just edit your .env:
    LLM_MODEL_NAME=llama-3.3-70b-versatile
    EMBEDDING_MODEL_NAME=BAAI/bge-large-en-v1.5
    RATE_LIMIT=200/minute
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── External Service Keys ──
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str
    GROQ_API_KEY: str

    # ── Model Configuration (swap via .env) ──
    LLM_MODEL_NAME: str = "llama-3.1-8b-instant"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-large-en-v1.5"
    LLM_TEMPERATURE: float = 0.0

    # ── Resilience ──
    REQUEST_TIMEOUT: int = 120         # seconds for external API calls (large file downloads need time)
    LLM_MAX_RETRIES: int = 3           # retry attempts on Groq failures
    DB_MAX_RETRIES: int = 3            # retry attempts on Supabase failures

    # ── Rate Limiting ──
    RATE_LIMIT_CHAT: str = "20/minute"

    # ── Security ──
    # Keep the default safe for local development. Add deployed frontend URLs in .env.
    CORS_ORIGINS: str = "http://localhost:3000"

    # Upload guardrails. These can be increased in .env when needed.
    MAX_UPLOAD_SIZE_MB: int = 25

    # ── RAG Retrieval & Accuracy ──
    RERANKER_MODEL_NAME: str = "Xenova/ms-marco-MiniLM-L-12-v2"
    RETRIEVAL_TOP_K: int = 20          # faster default; can override in .env for max-accuracy mode
    RERANKER_TOP_K: int = 5            # faster default; can override in .env
    MIN_RELEVANCE_SCORE: float = 0.3   # keep balanced precision by default
    MIN_RELEVANCE_SCORE_LOW: float = 0.1  # dynamic floor when few results survive
    # A question must meet this score before the assistant is allowed to answer.
    # Keep this higher than the retrieval fallback floor to prevent off-topic answers.
    ANSWER_MIN_RELEVANCE_SCORE: float = 0.3
    ENABLE_QUERY_REWRITE: bool = True  # LLM-based query rewriting for multi-turn
    ENABLE_HYDE: bool = False          # expensive; enable in .env when needed
    ENABLE_MULTI_QUERY: bool = False   # expensive; enable in .env when needed
    ENABLE_NEIGHBOR_CONTEXT: bool = False  # extra DB calls; enable in .env when needed

    # ── Ingestion ──
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 300
    INGESTION_BATCH_SIZE: int = 10     # keep small to avoid OOM with large embedding models

    # ── Google Drive ──
    GOOGLE_DRIVE_FOLDER_ID: str = ""  # set in .env

    # ── Answer Formatting & Structure ──
    ENABLE_STRUCTURED_ANSWERS: bool = True  # Enable hierarchical answer structure
    ENABLE_KEY_TAKEAWAYS: bool = False  # extra LLM call; enable in .env when needed
    ENABLE_RELATED_QUESTIONS: bool = False  # extra LLM call; enable in .env when needed
    RELATED_QUESTIONS_COUNT: int = 3  # Number of related questions to generate
    KEY_TAKEAWAYS_COUNT: int = 3  # Number of key takeaways to extract
    ANSWER_DETAIL_LEVEL: str = "comprehensive"  # or "detailed", "standard"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # don't crash on unknown .env vars


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton — settings are loaded once and reused."""
    return Settings()


# Convenience alias so existing imports still work
settings = get_settings()
