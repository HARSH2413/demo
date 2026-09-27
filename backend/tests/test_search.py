import pytest
from unittest.mock import MagicMock
from app.infrastructure.supabase_adapter import SupabaseAdapter

@pytest.fixture
def supabase_adapter():
    mock_client = MagicMock()
    adapter = SupabaseAdapter(url="http://dummy", service_key="dummy")
    adapter.client = mock_client
    return adapter

def test_search_similar_calls_rpc(supabase_adapter):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.data = [{"id": "chunk1", "content": "text1", "embedding_score": 0.9, "lexical_score": 0.8}]
    supabase_adapter.client.rpc.return_value.execute.return_value = mock_response

    results = supabase_adapter.search_similar(
        query_vector=[0.1]*1024,
        query_text="hello",
        box_id="test-box-id",
        limit=5
    )

    # Verify RPC was called correctly
    supabase_adapter.client.rpc.assert_called_once_with(
        "match_documents_hybrid_box",
        {
            "query_embedding": [0.1]*1024,
            "query_text": "hello",
            "match_box_id": "test-box-id",
            "match_count": 5
        }
    )
    assert len(results) == 1
    assert results[0]["id"] == "chunk1"

# Note: The actual exclusion of 'processing' and 'failed' documents 
# is enforced at the database level inside `match_documents_hybrid_box` 
# in schema_phase1b.sql via `AND d.status = 'completed'`.
# Since we cannot test live SQL without a database connection, 
# this test validates the boundary call parameters.
