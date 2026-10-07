import abc
from typing import List, Dict, Any, Optional

class ILexicalStore(abc.ABC):
    @abc.abstractmethod
    def search(self, query: str, box_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Searches the lexical index for the given box_id.
        Returns a list of dicts with at least:
        {
            "document_id": str,
            "chunk_index": int,
            "lexical_score": float,
            "filename": str,
            "content": str,
            "section_title": str,
            "page_start": int,
            ...
        }
        """
        pass

    @abc.abstractmethod
    def ensure_box_index(self, box_id: str, db_adapter) -> None:
        """
        Ensures the BM25 index for the given box_id is built and loaded.
        """
        pass

    @abc.abstractmethod
    def invalidate_box(self, box_id: str) -> None:
        """
        Invalidates and deletes the index for the given box_id.
        """
        pass
