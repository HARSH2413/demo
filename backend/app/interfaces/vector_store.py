from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IVectorStore(ABC):
    @abstractmethod
    def create_document(self, document: Dict[str, Any]) -> str:
        """Creates a parent document and returns its ID."""
        pass
        
    @abstractmethod
    def save_document_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Saves a batch of chunks for a document."""
        pass

    @abstractmethod
    def search_similar(self, query_vector: list[float], query_text: str, box_id: str, limit: int = 5) -> list[dict]:
        pass

    # 🛡️ THE NEW RULES
    @abstractmethod
    def document_exists(self, file_hash: str, box_id: str) -> bool:
        """Checks if a document with this exact content hash already exists."""
        pass

    @abstractmethod
    def delete_document(self, filename: str, box_id: str) -> bool:
        """Deletes a document and its chunks via cascading delete."""
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