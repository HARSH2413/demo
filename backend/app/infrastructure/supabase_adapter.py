"""
Supabase Adapter — all DB operations with retry resilience.

Wraps every call with tenacity retries so transient network errors
(connection resets, timeouts) don't crash the entire request.
"""
import httpx
from typing import List, Dict, Any
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.interfaces.vector_store import IVectorStore
from app.core.logger import logger

# Define a tuple of exceptions that are safe to retry.
# Retrying on all `Exception` types can be dangerous, as it might hide
# permanent errors (like auth issues or bad SQL) and lead to repeated,
# failing requests. We should only retry on transient network-related issues.
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
)

class SupabaseAdapter(IVectorStore):
    def __init__(self, url: str, service_key: str, max_retries: int = 3):
        if not url or not service_key:
            raise ValueError("Missing Supabase credentials — set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        self.client: Client = create_client(url, service_key)
        self.max_retries = max_retries
        logger.info("Supabase adapter initialized")

    # ── Document Operations ──

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase save_documents retry (attempt {rs.attempt_number})"),
    )
    def save_documents(self, records: List[Dict[str, Any]]) -> int:
        response = self.client.table("documents").insert(records).execute()
        return len(response.data)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase search_similar retry (attempt {rs.attempt_number})"),
    )
    def search_similar(self, query_vector: list[float], query_text: str, tenant_id: str, limit: int = 10) -> list[dict]:
        """Runs the Hybrid Search RPC in Supabase."""
        try:
            response = self.client.rpc(
                "match_documents_hybrid",
                {
                    "query_embedding": query_vector,
                    "query_text": query_text,
                    "match_tenant_id": tenant_id,
                    "match_count": limit,
                },
            ).execute()
            logger.info(f"Hybrid search returned {len(response.data)} docs for tenant={tenant_id}")
            return response.data
        except Exception as e:
            logger.error(f"Hybrid search failed for tenant={tenant_id}, query='{query_text[:80]}': {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase document_exists retry (attempt {rs.attempt_number})"),
    )
    def document_exists(self, file_hash: str, tenant_id: str) -> bool:
        """Checks if a file with this exact SHA-256 fingerprint already exists."""
        response = (
            self.client.table("documents")
            .select("id")
            .eq("file_hash", file_hash)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        return len(response.data) > 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase delete_document retry (attempt {rs.attempt_number})"),
    )
    def delete_document(self, filename: str, tenant_id: str) -> bool:
        response = (
            self.client.table("documents")
            .delete()
            .eq("tenant_id", tenant_id)
            .eq("filename", filename)
            .execute()
        )
        return len(response.data) > 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase get_all_documents retry (attempt {rs.attempt_number})"),
    )
    def get_all_documents(self, tenant_id: str) -> List[str]:
        """Fetches a list of all unique filenames for a tenant."""
        response = self.client.table("documents").select("filename").eq("tenant_id", tenant_id).execute()
        unique_files = list(set([row["filename"] for row in response.data]))
        return unique_files

    def get_document_metadata(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Returns one record per document for the library UI."""
        response = (
            self.client.table("documents")
            .select("filename, file_hash, created_at")
            .eq("tenant_id", tenant_id)
            .order("created_at", desc=True)
            .execute()
        )
        documents: Dict[str, Dict[str, Any]] = {}
        for row in response.data:
            filename = row["filename"]
            if filename not in documents:
                documents[filename] = {
                    "filename": filename,
                    "file_hash": row.get("file_hash"),
                    "created_at": row.get("created_at"),
                }
        return list(documents.values())

    # ── Chat Session Operations ──

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase create_chat_session retry (attempt {rs.attempt_number})"),
    )
    def create_chat_session(self, tenant_id: str, title: str = "New Conversation") -> str:
        """Creates a new blank chat room and returns the session_id."""
        response = self.client.table("chat_sessions").insert({
            "tenant_id": tenant_id,
            "title": title,
        }).execute()
        return response.data[0]["id"]

    def list_chat_sessions(self, tenant_id: str, limit: int = 50) -> list:
        """Lists the most recent conversations for one tenant."""
        response = self.client.table("chat_sessions").select("id, title, created_at").eq("tenant_id", tenant_id).order("created_at", desc=True).limit(limit).execute()
        return response.data

    def rename_chat_session(self, session_id: str, tenant_id: str, title: str) -> bool:
        response = self.client.table("chat_sessions").update({"title": title}).eq("id", session_id).eq("tenant_id", tenant_id).execute()
        return bool(response.data)

    def delete_chat_session(self, session_id: str, tenant_id: str) -> bool:
        """Deletes a conversation; chat_messages must cascade at the database level."""
        response = self.client.table("chat_sessions").delete().eq("id", session_id).eq("tenant_id", tenant_id).execute()
        return bool(response.data)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase get_chat_history retry (attempt {rs.attempt_number})"),
    )
    def get_chat_history(self, session_id: str, tenant_id: str) -> list:
        """Fetches history only when the session belongs to the requested tenant."""
        session = (
            self.client.table("chat_sessions")
            .select("id")
            .eq("id", session_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        if not session.data:
            return []
        response = (
            self.client.table("chat_messages")
            .select("role, content")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
        return response.data

    def session_belongs_to_tenant(self, session_id: str, tenant_id: str) -> bool:
        """Checks ownership before a request can read from or write to a chat session."""
        response = (
            self.client.table("chat_sessions")
            .select("id")
            .eq("id", session_id)
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )
        return bool(response.data)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase save_chat_message retry (attempt {rs.attempt_number})"),
    )
    def save_chat_message(self, session_id: str, role: str, content: str):
        """Saves a single message (either 'user' or 'assistant') to the database."""
        self.client.table("chat_messages").insert({
            "session_id": session_id,
            "role": role,
            "content": content,
        }).execute()

    # ── Neighbor Context (Parent-Child Retrieval) ──

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=lambda rs: logger.warning(f"Supabase get_neighboring_chunks retry (attempt {rs.attempt_number})"),
    )
    def get_neighboring_chunks(self, filename: str, content_snippet: str, tenant_id: str, limit: int = 5) -> list[dict]:
        """
        Fetches chunks from the same document to provide surrounding context.

        Used for parent-child retrieval — when a matched chunk is small,
        we expand context by including adjacent chunks from the same file.
        Returns chunks ordered by their database insertion order (proxy for position).
        """
        try:
            response = (
                self.client.table("documents")
                .select("id, filename, content")
                .eq("tenant_id", tenant_id)
                .eq("filename", filename)
                .order("created_at")
                .limit(limit)
                .execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch neighboring chunks for '{filename}': {e}")
            return []
