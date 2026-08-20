"""
Reranker Interface — contract for cross-encoder re-ranking adapters.

Re-rankers score each (query, document) pair with full cross-attention,
producing far more accurate relevance scores than vector cosine similarity.
"""
from abc import ABC, abstractmethod
from typing import List


class IReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """
        Re-scores and re-orders retrieved documents by relevance to the query.

        Args:
            query: The user's search query.
            documents: List of dicts with at least a 'content' key.
            top_k: Number of top results to return after re-ranking.

        Returns:
            The top_k documents sorted by cross-encoder relevance score,
            each enriched with a 'rerank_score' key.
        """
        pass
