import pytest
import os
from unittest.mock import MagicMock, patch
from app.services.ingestion_service import IngestionService, PartialIngestionError
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

def test_process_file_background_partial_failure_cleans_up(ingestion_service, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy text")
    
    ingestion_service._extract_text_from_disk = MagicMock(return_value="dummy text")
    
    # Simulate a failure during embedding that fails all 3 retries
    ingestion_service.embedder.embed_text.side_effect = Exception("Embedding failed")
    
    with pytest.raises(PartialIngestionError) as exc_info:
        ingestion_service.process_file_background(
            file_path=str(test_file),
            filename="test.txt",
            file_hash="dummyhash",
            box_id="box-123",
            document_id="doc-123"
        )
        
    assert "failed batches" in str(exc_info.value)
    
    # Assert partial chunks cleanup WAS called (we no longer preserve chunks)
    assert ingestion_service.db.delete_chunks_by_document.called
    
    # Ensure document status was NOT updated to 'completed'
    assert not ingestion_service.db.update_document_status.called
    
    # Assert file cleanup happened anyway
    assert not test_file.exists()

def test_process_file_background_fatal_failure_cleans_up(ingestion_service, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy text")
    
    # Simulate a fatal failure OUTSIDE the batch loop (e.g. extraction fails)
    ingestion_service._extract_text_from_disk = MagicMock(side_effect=Exception("Fatal extraction error"))
    
    with pytest.raises(Exception) as exc_info:
        ingestion_service.process_file_background(
            file_path=str(test_file),
            filename="test.txt",
            file_hash="dummyhash",
            box_id="box-123",
            document_id="doc-123"
        )
        
    assert "Fatal extraction error" in str(exc_info.value)
    
    # Assert partial chunks cleanup WAS called
    ingestion_service.db.delete_chunks_by_document.assert_called_once_with("doc-123")
    
    # Assert file cleanup happened anyway
    assert not test_file.exists()

def test_process_file_background_batch_retry_success(ingestion_service, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy text")
    
    ingestion_service._extract_text_from_disk = MagicMock(return_value="dummy text")
    
    # Simulate first attempt failing, second succeeding
    ingestion_service.embedder.embed_text.side_effect = [
        Exception("Temporary network glitch"),
        [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]] # Two mock embeddings for "chunk1" and "chunk2"
    ]
    
    # Should not raise exception
    ingestion_service.process_file_background(
        file_path=str(test_file),
        filename="test.txt",
        file_hash="dummyhash",
        box_id="box-123",
        document_id="doc-123"
    )
    
    # Assert successful completion
    ingestion_service.db.update_document_status.assert_called_once_with("doc-123", "completed")
    
    # Assert chunks saved successfully
    assert ingestion_service.db.save_document_chunks.called

@patch('os.remove')
def test_process_file_background_ingestion_failure_and_temp_cleanup_failure(mock_remove, ingestion_service, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy text")
    
    # Fatal failure
    ingestion_service._extract_text_from_disk = MagicMock(side_effect=Exception("Fatal Ingestion Error"))
    
    # Simulate os.remove failure
    mock_remove.side_effect = Exception("File deletion error")
    
    with pytest.raises(Exception) as exc_info:
        ingestion_service.process_file_background(
            file_path=str(test_file),
            filename="test.txt",
            file_hash="dummyhash",
            box_id="box-123",
            document_id="doc-123"
        )
        
    # The original ingestion exception should be preserved!
    assert "Fatal Ingestion Error" in str(exc_info.value)
    
    mock_remove.assert_called_once_with(str(test_file))

@patch('os.remove')
def test_process_file_background_success_but_temp_cleanup_failure(mock_remove, ingestion_service, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy text")
    
    ingestion_service._extract_text_from_disk = MagicMock(return_value="dummy text")
    ingestion_service.embedder.embed_text.return_value = [[0.1, 0.2], [0.3, 0.4]]
    
    # Simulate os.remove failure
    mock_remove.side_effect = Exception("File deletion error")
    
    # Should not raise exception
    ingestion_service.process_file_background(
        file_path=str(test_file),
        filename="test.txt",
        file_hash="dummyhash",
        box_id="box-123",
        document_id="doc-123"
    )
    
    # Document marked completed despite cleanup failure
    ingestion_service.db.update_document_status.assert_called_once_with("doc-123", "completed")
    mock_remove.assert_called_once_with(str(test_file))

def test_process_upload_safely_marks_failed(ingestion_service):
    # Test the wrapper function in upload.py
    ingestion_service.process_file_background = MagicMock(side_effect=PartialIngestionError("Completed with 1 failed batches"))
    
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
    ingestion_service.db.update_document_status.assert_called_once_with("doc1", "failed", "Completed with 1 failed batches")

def test_process_upload_safely_cleanup_error_does_not_hide_original(ingestion_service):
    # Simulate ingestion crashing, AND the cleanup (updating status) crashing
    ingestion_service.process_file_background = MagicMock(side_effect=Exception("Fatal ingestion crash"))
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
    ingestion_service.db.update_document_status.assert_called_once_with("doc1", "failed", "Fatal ingestion crash")

@patch('fitz.open')
def test_process_pdf_streaming_closes_resource_on_success(mock_fitz_open, ingestion_service):
    mock_doc = MagicMock()
    mock_doc.__enter__.return_value = mock_doc
    mock_doc.page_count = 1
    mock_page = MagicMock()
    mock_page.get_text.return_value = [[0, 0, 0, 0, "mock text", 0, 0]]
    mock_doc.load_page.return_value = mock_page
    mock_fitz_open.return_value = mock_doc
    
    ingestion_service._process_pdf_streaming(
        file_path="dummy.pdf", filename="test.pdf", file_hash="hash",
        box_id="box-123", document_id="doc-123"
    )
    
    mock_doc.__exit__.assert_called_once()

@patch('fitz.open')
def test_process_pdf_streaming_closes_resource_on_exception(mock_fitz_open, ingestion_service):
    mock_doc = MagicMock()
    mock_doc.__enter__.return_value = mock_doc
    mock_doc.page_count = 1
    mock_doc.load_page.side_effect = Exception("Failed to load page")
    mock_fitz_open.return_value = mock_doc
    
    with pytest.raises(Exception, match="Failed to load page"):
        ingestion_service._process_pdf_streaming(
            file_path="dummy.pdf", filename="test.pdf", file_hash="hash",
            box_id="box-123", document_id="doc-123"
        )
        
    mock_doc.__exit__.assert_called_once()
