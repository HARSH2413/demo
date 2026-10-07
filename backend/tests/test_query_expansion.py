import pytest
from unittest.mock import MagicMock
from app.services.query_expansion import QueryExpansionService

def test_query_expansion_success():
    mock_llm = MagicMock()
    mock_llm.generate_response.return_value = '{"rewritten_query": "What is the revenue for Q3?", "variants": ["Q3 revenue", "Earnings in Q3"]}'
    
    service = QueryExpansionService(llm=mock_llm)
    
    res = service.expand("what is it?", [{"role": "user", "content": "Tell me about Q3 revenue."}])
    
    assert res["rewritten_query"] == "What is the revenue for Q3?"
    assert len(res["variants"]) == 2
    assert "Q3 revenue" in res["variants"]

def test_query_expansion_fallback():
    mock_llm = MagicMock()
    # Invalid JSON should trigger fallback
    mock_llm.generate_response.return_value = 'This is not JSON'
    
    service = QueryExpansionService(llm=mock_llm)
    
    res = service.expand("fallback test", [])
    
    assert res["rewritten_query"] == "fallback test"
    assert len(res["variants"]) == 0

def test_query_expansion_deduplicates():
    mock_llm = MagicMock()
    # Should deduplicate case-insensitively and remove variants identical to rewritten query
    mock_llm.generate_response.return_value = '{"rewritten_query": "Test", "variants": ["test", "TEST", "Another", "another"]}'
    
    service = QueryExpansionService(llm=mock_llm)
    
    res = service.expand("test", [])
    
    assert res["rewritten_query"] == "Test"
    assert len(res["variants"]) == 1
    assert res["variants"][0] == "Another"
