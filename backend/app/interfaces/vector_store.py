from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class IVectorStore(ABC):
    """
    Interface for database and vector operations.
    Despite the name 'IVectorStore', this interface currently serves as the 
    primary data access layer (Repository) for:
    - Document management (upload, metadata, deletion)
    - Vector search (hybrid RRF search, neighboring chunks)
    - Chat session management (history, conversations, metadata)
    """
    @abstractmethod
    def create_document(self, document: Dict[str, Any]) -> str:
        """Creates a parent document and returns its ID."""
        pass

    @abstractmethod
    def update_document_status(self, document_id: str, status: str, error_message: Optional[str] = None) -> None:
        """Updates the status and optional error message of a document."""
        pass
        
    @abstractmethod
    def save_document_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Saves a batch of chunks for a document."""
        pass

    @abstractmethod
    def search_similar(self, query_vector: list[float], query_text: str, box_id: str, limit: int = 5) -> list[dict]:
        """
        Executes a hybrid search (vector similarity + lexical BM25) and orders by Reciprocal Rank Fusion (RRF).
        Returns list of dicts containing chunk data and retrieval scores (embedding_score, lexical_score, rrf_score).
        """
        pass

    # 🛡️ THE NEW RULES
    @abstractmethod
    def document_exists(self, file_hash: str, box_id: str) -> bool:
        """Checks if a document with this exact content hash already exists."""
        pass

    @abstractmethod
    def delete_document(self, document_id: str, box_id: str) -> bool:
        """Deletes a document and its chunks via cascading delete."""
        pass
        
    @abstractmethod
    def delete_chunks_by_document(self, document_id: str) -> None:
        """Deletes all chunks belonging to a specific document without deleting the document itself."""
        pass

    @abstractmethod
    def get_all_documents(self, box_id: str) -> List[str]:
        """Fetches a list of all unique filenames for a box."""
        pass

    @abstractmethod
    def get_document_metadata(self, box_id: str) -> List[Dict[str, Any]]:
        """Returns one record per document for the library UI."""
        pass
        
    @abstractmethod
    def get_neighboring_chunks(self, document_id: str, chunk_index: int, limit: int = 5) -> list[dict]:
        """Fetches neighboring chunks purely based on chunk_index."""
        pass

    @abstractmethod
    def get_multi_neighboring_chunks(self, requests: list[dict], limit: int = 5) -> dict[str, list[dict]]:
        """Bulk fetches neighboring chunks for multiple documents to avoid N+1 queries."""
        pass

    # ── Chat Session Operations ──

    @abstractmethod
    def create_chat_session(self, box_id: str, title: str = "New Conversation") -> str:
        pass

    @abstractmethod
    def list_chat_sessions(self, box_id: str, limit: int = 50) -> list:
        pass

    @abstractmethod
    def rename_chat_session(self, session_id: str, box_id: str, title: str) -> bool:
        pass

    @abstractmethod
    def delete_chat_session(self, session_id: str, box_id: str) -> bool:
        pass

    @abstractmethod
    def get_chat_history(self, session_id: str, box_id: str) -> list:
        pass

    @abstractmethod
    def session_belongs_to_box(self, session_id: str, box_id: str) -> bool:
        pass

    @abstractmethod
    def save_chat_message(self, session_id: str, role: str, content: str):
        pass