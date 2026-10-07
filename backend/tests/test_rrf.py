import pytest
from app.services.retrieval_engine import RetrievalEngine

def test_rrf_merge_basic():
    engine = RetrievalEngine(db=None, lexical_store=None, embedder=None, reranker=None)
    
    dense = [
        {"document_id": "doc1", "chunk_index": 0, "embedding_score": 0.9},
        {"document_id": "doc2", "chunk_index": 0, "embedding_score": 0.8},
    ]
    
    lexical = [
        {"document_id": "doc2", "chunk_index": 0, "lexical_score": 10.5},
        {"document_id": "doc3", "chunk_index": 0, "lexical_score": 8.0},
    ]
    
    # RRF K is 60. 
    # doc1: dense rank 0 (1/61), lexical rank None
    # doc2: dense rank 1 (1/62), lexical rank 0 (1/61) -> total = 1/62 + 1/61
    # doc3: dense rank None, lexical rank 1 (1/62)
    
    # Expected order: doc2 (highest), doc1 (1/61 = 0.01639), doc3 (1/62 = 0.01612)
    # Since doc1 > doc3, order should be doc2, doc1, doc3
    
    merged = engine._rrf_merge(dense, lexical, limit=3)
    
    assert len(merged) == 3
    assert merged[0]["document_id"] == "doc2"
    assert merged[1]["document_id"] == "doc1"
    assert merged[2]["document_id"] == "doc3"
    
def test_rrf_merge_tiebreaker():
    engine = RetrievalEngine(db=None, lexical_store=None, embedder=None, reranker=None)
    
    # Both have exactly one rank (e.g. dense only)
    # Because they have same RRF score, tiebreaker should use embedding_score, then doc_id
    dense = [
        {"document_id": "docB", "chunk_index": 0, "embedding_score": 0.9},
        {"document_id": "docA", "chunk_index": 0, "embedding_score": 0.9},
    ]
    
    merged = engine._rrf_merge(dense, [], limit=2)
    # docB was 0, docA was 1, so docB gets 1/61, docA gets 1/62.
    # Therefore docB wins normally.
    assert merged[0]["document_id"] == "docB"
    assert merged[1]["document_id"] == "docA"
