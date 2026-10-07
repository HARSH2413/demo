import pytest
from unittest.mock import MagicMock
from app.services.retrieval_engine import RetrievalEngine

@pytest.fixture
def retrieval_engine():
    db = MagicMock()
    lexical_store = MagicMock()
    embedder = MagicMock()
    reranker = MagicMock()
    return RetrievalEngine(
        db=db,
        lexical_store=lexical_store,
        embedder=embedder,
        reranker=None,
        retrieval_top_k=5,
        reranker_top_k=5
    )

def test_deduplication_different_document_same_prefix(retrieval_engine):
    """
    Test that two entirely different documents that happen to have identical chunks 
    are NOT deduplicated incorrectly during global RRF multi-query.
    """
    retrieval_engine.embedder.embed_text.return_value = [[0.1, 0.2]]
    
    docs_returned = [
        {
            "document_id": "doc-1",
            "chunk_index": 0,
            "content": "CONFIDENTIAL: Do not distribute.",
            "embedding_score": 0.9,
        },
        {
            "document_id": "doc-2",
            "chunk_index": 0,
            "content": "CONFIDENTIAL: Do not distribute.",
            "embedding_score": 0.9,
        }
    ]
    
    retrieval_engine.db.search_dense.return_value = docs_returned
    retrieval_engine.lexical_store.search.return_value = []
    
    results = retrieval_engine.retrieve_documents_multi(
        queries=["test query"],
        box_id="box-123",
        reranker_query="test query"
    )
    
    # Both should be preserved because document_id differs.
    assert len(results) == 2
    docs_ids = {r["document_id"] for r in results}
    assert "doc-1" in docs_ids
    assert "doc-2" in docs_ids

def test_rrf_tiebreaker(retrieval_engine):
    """
    Ensure stable tiebreaker when scores are exactly identical.
    """
    retrieval_engine.embedder.embed_text.return_value = [[0.1, 0.2]]
    
    docs_returned = [
        {"document_id": "b-doc", "chunk_index": 1, "content": "Text B", "embedding_score": 0.9},
        {"document_id": "a-doc", "chunk_index": 0, "content": "Text A", "embedding_score": 0.9},
    ]
    
    retrieval_engine.db.search_dense.return_value = docs_returned
    retrieval_engine.lexical_store.search.return_value = []
    
    results = retrieval_engine.retrieve_documents_multi(["query"], "box_id", "query")
    
    assert len(results) == 2
