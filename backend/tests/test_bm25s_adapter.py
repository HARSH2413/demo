import pytest
import os
import shutil
from unittest.mock import MagicMock
from app.infrastructure.bm25s_adapter import BM25SAdapter

@pytest.fixture
def bm25s_adapter(tmp_path):
    # Use a temporary directory for BM25 indexes
    index_dir = str(tmp_path / "bm25")
    adapter = BM25SAdapter(data_dir=index_dir)
    yield adapter
    # Cleanup done automatically by tmp_path

def test_bm25s_build_and_search(bm25s_adapter):
    mock_db = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [
        {"id": "c1", "document_id": "doc1", "chunk_index": 0, "content": "The quick brown fox jumps over the lazy dog", "documents": {"filename": "file1.txt"}},
        {"id": "c2", "document_id": "doc2", "chunk_index": 0, "content": "Fast brown foxes leap across sleepy dogs", "documents": {"filename": "file2.txt"}},
        {"id": "c3", "document_id": "doc3", "chunk_index": 0, "content": "A completely unrelated document about quantum physics", "documents": {"filename": "file3.txt"}},
    ]
    mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
    
    box_id = "test-box-1"
    
    # Ensure index builds
    bm25s_adapter.ensure_box_index(box_id, mock_db)
    mock_db.client.table.assert_called_once_with("document_chunks")
    
    # Search for fox
    results = bm25s_adapter.search("brown fox", box_id, limit=2)
    assert len(results) == 2
    assert "fox" in results[0]["content"].lower()
    
    # Search for physics
    results_physics = bm25s_adapter.search("quantum physics", box_id, limit=1)
    assert len(results_physics) == 1
    assert "physics" in results_physics[0]["content"]
    
def test_bm25s_invalidate(bm25s_adapter):
    mock_db = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [
        {"id": "c1", "document_id": "doc1", "chunk_index": 0, "content": "test document", "documents": {"filename": "file1.txt"}},
    ]
    mock_db.client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
    box_id = "test-box-2"
    
    bm25s_adapter.ensure_box_index(box_id, mock_db)
    
    # Invalidate
    bm25s_adapter.invalidate_box(box_id)
    
    # Should be removed from cache and disk
    assert box_id not in bm25s_adapter.indexes
    index_path = os.path.join(bm25s_adapter.data_dir, box_id)
    assert not os.path.exists(index_path)
