import pytest
import os
from unittest.mock import MagicMock, patch
from app.services.ingestion_service import IngestionService
from app.api.upload import _process_upload_safely

@pytest.fixture
def ingestion_service():
    db_mock = MagicMock()
    embedder_mock = MagicMock()
    service = IngestionService(db=db_mock, embedder=embedder_mock)
    # mock split_text so we don't need real text splitting
    service.text_splitter = MagicMock()
    service.text_splitter.split_text.return_value = ["chunk1", "chunk2"]
    return service

def test_process_file_background_success(ingestion_service, tmp_path):
    # Setup temp file
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy text")
    
    # Mock extract text
    ingestion_service._extract_text_from_disk = MagicMock(return_value="dummy text")
    
    ingestion_service.process_file_background(
        file_path=str(test_file),
        filename="test.txt",
        file_hash="dummyhash",
        box_id="box-123",
        document_id="doc-123"
    )
    
    # Assert successful completion
    ingestion_service.db.update_document_status.assert_called_once_with("doc-123", "completed")
    
    # Assert chunks saved
    assert ingestion_service.db.save_document_chunks.called
    
    # Assert file cleanup
    assert not test_file.exists()

def test_process_file_background_failure_cleanup(ingestion_service, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy text")
    
    ingestion_service._extract_text_from_disk = MagicMock(return_value="dummy text")
    
    # Simulate a failure during embedding
    ingestion_service.embedder.embed_text.side_effect = Exception("Embedding failed")
    
    with pytest.raises(Exception) as exc_info:
        ingestion_service.process_file_background(
            file_path=str(test_file),
            filename="test.txt",
            file_hash="dummyhash",
            box_id="box-123",
            document_id="doc-123"
        )
        
    assert "Embedding failed" in str(exc_info.value)
    
    # Assert partial chunks cleanup was called
    ingestion_service.db.delete_chunks_by_document.assert_called_once_with("doc-123")
    
    # Ensure document status was NOT updated to 'completed'
    assert not ingestion_service.db.update_document_status.called
    
    # Assert file cleanup happened anyway
    assert not test_file.exists()

def test_process_upload_safely_marks_failed(ingestion_service):
    # Test the wrapper function in upload.py
    ingestion_service.process_file_background = MagicMock(side_effect=Exception("Ingestion crash"))
    
    # Should not raise exception
    _process_upload_safely(
        ingestion_service=ingestion_service,
        file_path="/dummy/path.txt",
        filename="test.txt",
        file_hash="hash",
        box_id="box1",
        document_id="doc1"
    )
    
    # Instead, it should catch and update status to failed
    ingestion_service.db.update_document_status.assert_called_once_with("doc1", "failed", "Ingestion crash")

def test_process_upload_safely_cleanup_error_does_not_hide_original(ingestion_service):
    # Simulate ingestion crashing, AND the cleanup (updating status) crashing
    ingestion_service.process_file_background = MagicMock(side_effect=Exception("Ingestion crash"))
    ingestion_service.db.update_document_status.side_effect = Exception("DB offline")
    
    # Should not raise exception, but still safely log and end
    _process_upload_safely(
        ingestion_service=ingestion_service,
        file_path="/dummy/path.txt",
        filename="test.txt",
        file_hash="hash",
        box_id="box1",
        document_id="doc1"
    )
    
    # Verify we attempted to set failed status
    ingestion_service.db.update_document_status.assert_called_once_with("doc1", "failed", "Ingestion crash")
