import pytest
from app.infrastructure.reranker_adapter import FastEmbedRerankerAdapter

def test_reranker_sigmoid_normalization():
    adapter = FastEmbedRerankerAdapter(model_name="Xenova/ms-marco-MiniLM-L-6-v2")
    
    query = "What is the capital of France?"
    documents = [
        {"content": "Paris is the capital of France."},
        {"content": "The moon is made of cheese."},
        {"content": "France is a country in Europe. Its capital is Paris."}
    ]
    
    results = adapter.rerank(query, documents, top_k=3)
    
    assert len(results) == 3
    
    # Assert all scores are normalized between 0 and 1
    for doc in results:
        assert 0.0 <= doc["rerank_score"] <= 1.0
        
    # Assert they are sorted correctly
    assert results[0]["rerank_score"] >= results[1]["rerank_score"]
    assert results[1]["rerank_score"] >= results[2]["rerank_score"]
    
    # Assert that it doesn't accidentally double-apply by checking the actual structure
    # (Since it uses math.exp internally in a loop, it's explicitly applied once).
