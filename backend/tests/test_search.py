import pytest
from unittest.mock import MagicMock
from app.infrastructure.supabase_adapter import SupabaseAdapter

@pytest.fixture
def supabase_adapter():
    mock_client = MagicMock()
    adapter = SupabaseAdapter(url="http://dummy", service_key="dummy")
    adapter.client = mock_client
    return adapter

def test_search_dense_calls_rpc(supabase_adapter):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.data = [{"id": "chunk1", "content": "text1", "embedding_score": 0.9}]
    supabase_adapter.client.rpc.return_value.execute.return_value = mock_response

    results = supabase_adapter.search_dense(
        query_vector=[0.1]*1024,
        box_id="test-box-id",
        limit=5
    )

    # Verify RPC was called correctly
    supabase_adapter.client.rpc.assert_called_once_with(
        "match_documents_dense_box",
        {
            "query_embedding": [0.1]*1024,
            "match_box_id": "test-box-id",
            "match_count": 5
        }
    )
    assert len(results) == 1
    assert results[0]["id"] == "chunk1"

