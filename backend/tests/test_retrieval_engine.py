import pytest
from unittest.mock import MagicMock
from app.services.retrieval_engine import RetrievalEngine

@pytest.fixture
def retrieval_engine():
    db = MagicMock()
    embedder = MagicMock()
    llm = MagicMock()
    reranker = MagicMock()
    return RetrievalEngine(
        db=db,
        embedder=embedder,
        llm=llm,
        reranker=reranker,
        retrieval_top_k=5,
        reranker_top_k=5,
        enable_hyde=False,
        enable_multi_query=False
    )

def test_deduplication_same_prefix(retrieval_engine):
    """
    Test that two chunks with the identical first 100 characters but from different 
    locations are NOT deduplicated incorrectly.
    """
    retrieval_engine.embedder.embed_text.return_value = [[0.1, 0.2]]
    
    # Simulate DB returning two different chunks that happen to start with the same 100 characters.
    long_prefix = "A" * 105
    
    docs_returned = [
        {
            "document_id": "doc-1",
            "chunk_index": 0,
            "content": long_prefix + " chunk 1",
            "rrf_score": 0.9,
        },
        {
            "document_id": "doc-1",
            "chunk_index": 1,
            "content": long_prefix + " chunk 2",
            "rrf_score": 0.8,
        }
    ]
    
    retrieval_engine.db.search_similar.return_value = docs_returned
    
    # We call multi_query_search manually or via retrieve_documents
    results = retrieval_engine._multi_query_search(
        queries=["test query"],
        original_query="test query",
        box_id="box-123"
    )
    
    # Before #39, this would return 1 document because the prefix was identical.
    # Now it should return both because (document_id, chunk_index) are different.
    assert len(results) == 2
    assert results[0]["chunk_index"] == 0
    assert results[1]["chunk_index"] == 1

def test_deduplication_same_document_same_chunk(retrieval_engine):
    """
    Test that if multi-query returns the EXACT SAME chunk from multiple queries, 
    it correctly deduplicates and keeps the highest score.
    """
    retrieval_engine.embedder.embed_text.return_value = [[0.1, 0.2]]
    
    # Query 1 results
    docs_q1 = [
        {
            "document_id": "doc-1",
            "chunk_index": 0,
            "content": "Short text",
            "rrf_score": 0.5,
        }
    ]
    
    # Query 2 results
    docs_q2 = [
        {
            "document_id": "doc-1",
            "chunk_index": 0,
            "content": "Short text",
            "rrf_score": 0.9, # Higher score
        }
    ]
    
    # Mocking side_effect for search_similar to return different results for different queries
    retrieval_engine.db.search_similar.side_effect = [docs_q1, docs_q2]
    
    results = retrieval_engine._multi_query_search(
        queries=["query 1", "query 2"],
        original_query="test query",
        box_id="box-123"
    )
    
    # Should deduplicate down to 1
    assert len(results) == 1
    # Should keep the higher score (0.9)
    assert results[0]["rrf_score"] == 0.9
