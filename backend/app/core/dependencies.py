"""
Dependency Injection — wires config-driven adapters into services.

This is the ONLY place where adapters are instantiated.
All config values flow from Settings → adapters → services.
"""
from functools import lru_cache
from app.core.config import settings
from app.infrastructure.supabase_adapter import SupabaseAdapter
from app.infrastructure.fastembed_adapter import FastEmbedAdapter
from app.infrastructure.groq_adapter import GroqAdapter
from app.infrastructure.reranker_adapter import FastEmbedRerankerAdapter
from app.services.chat_service import ChatService
from app.services.ingestion_service import IngestionService
from app.services.query_rewriter import QueryRewriter


# ── Singleton Adapters (created once, reused across all requests) ──

@lru_cache()
def _get_db_adapter() -> SupabaseAdapter:
    return SupabaseAdapter(
        url=settings.SUPABASE_URL,
        service_key=settings.SUPABASE_SERVICE_KEY,
        max_retries=settings.DB_MAX_RETRIES,
    )


@lru_cache()
def _get_embedder_adapter() -> FastEmbedAdapter:
    return FastEmbedAdapter(model_name=settings.EMBEDDING_MODEL_NAME)


@lru_cache()
def _get_llm_adapter() -> GroqAdapter:
    return GroqAdapter(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.LLM_MODEL_NAME,
        timeout=settings.REQUEST_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )


@lru_cache()
def _get_reranker_adapter() -> FastEmbedRerankerAdapter:
    return FastEmbedRerankerAdapter(model_name=settings.RERANKER_MODEL_NAME)


# ── Service Factories (called by FastAPI Depends) ──

def get_chat_service() -> ChatService:
    """FastAPI will call this to get a fully configured ChatService."""
    llm = _get_llm_adapter()
    query_rewriter = QueryRewriter(llm=llm) if settings.ENABLE_QUERY_REWRITE else None

    return ChatService(
        db=_get_db_adapter(),
        embedder=_get_embedder_adapter(),
        llm=llm,
        reranker=_get_reranker_adapter(),
        query_rewriter=query_rewriter,
        retrieval_top_k=settings.RETRIEVAL_TOP_K,
        reranker_top_k=settings.RERANKER_TOP_K,
        min_relevance_score=settings.MIN_RELEVANCE_SCORE,
        min_relevance_score_low=settings.MIN_RELEVANCE_SCORE_LOW,
        enable_hyde=settings.ENABLE_HYDE,
        enable_multi_query=settings.ENABLE_MULTI_QUERY,
        enable_neighbor_context=settings.ENABLE_NEIGHBOR_CONTEXT,
    )


def get_ingestion_service() -> IngestionService:
    """FastAPI will call this to get a fully configured IngestionService."""
    return IngestionService(
        db=_get_db_adapter(),
        embedder=_get_embedder_adapter(),
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        batch_size=settings.INGESTION_BATCH_SIZE,
        llm=_get_llm_adapter(),  # For document summary generation
    )