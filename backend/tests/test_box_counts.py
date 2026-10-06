import pytest
from unittest.mock import MagicMock, patch
from app.infrastructure.supabase_adapter import SupabaseAdapter

@pytest.fixture
def mock_supabase_client():
    with patch('app.infrastructure.supabase_adapter.create_client') as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        yield mock_client

@pytest.fixture
def adapter(mock_supabase_client):
    return SupabaseAdapter("http://localhost", "dummy_key", max_retries=3)

def test_list_boxes_document_counts(adapter, mock_supabase_client):
    # Test zero documents, multiple documents, and multiple boxes
    mock_execute = MagicMock(return_value=MagicMock(data=[
        {"id": "box-1", "user_id": "user-1", "name": "Zero Docs Box", "documents": [{"count": 0}]},
        {"id": "box-2", "user_id": "user-1", "name": "Multi Docs Box", "documents": [{"count": 42}]},
        {"id": "box-3", "user_id": "user-1", "name": "Empty Docs Array Box", "documents": []},
        {"id": "box-4", "user_id": "user-1", "name": "No Docs Key Box"},
    ]))
    
    mock_supabase_client.table().select().eq().order().execute = mock_execute
    
    boxes = adapter.list_boxes("user-1")
    
    assert len(boxes) == 4
    
    # Test zero documents
    assert boxes[0]["id"] == "box-1"
    assert boxes[0]["document_count"] == 0
    assert "documents" not in boxes[0] # Assert it's popped off
    
    # Test multiple documents
    assert boxes[1]["id"] == "box-2"
    assert boxes[1]["document_count"] == 42
    
    # Test robustness against weird relations
    assert boxes[2]["document_count"] == 0
    assert boxes[3]["document_count"] == 0

def test_get_box_document_counts(adapter, mock_supabase_client):
    mock_execute = MagicMock(return_value=MagicMock(data=[
        {"id": "box-1", "user_id": "user-1", "name": "Single Box", "documents": [{"count": 5}]}
    ]))
    
    mock_supabase_client.table().select().eq().eq().execute = mock_execute
    
    box = adapter.get_box("box-1", "user-1")
    
    assert box is not None
    assert box["id"] == "box-1"
    assert box["document_count"] == 5
    assert "documents" not in box
