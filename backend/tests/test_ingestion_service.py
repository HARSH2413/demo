import pytest
import os
from unittest.mock import MagicMock, patch
from app.services.ingestion_service import IngestionService, PartialIngestionError
from app.api.upload import _process_upload_safely

@pytest.fixture
def ingestion_service():
    db_mock = MagicMock()
    embedder_mock = MagicMock()
    service = IngestionService(db=db_mock, embedder=embedder_mock, lexical_store=MagicMock())
    # mock split_text so we don't need real text splitting
    service.text_splitter = MagicMock()
    service.text_splitter.split_text.return_value = ["chunk1", "chunk2"]
    mock_doc = MagicMock()
    mock_doc.page_content = "chunk1"
    mock_doc.metadata = {"start_index": 0}
    service.text_splitter.create_documents.return_value = [mock_doc]
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
    test_file.write_text("chunk 1 text\n\nchunk 2 text")
    
    ingestion_service._extract_text_from_disk = MagicMock(return_value="chunk 1 text\n\nchunk 2 text")
    # Force 2 chunks
    ingestion_service.text_splitter.split_text = MagicMock(return_value=["chunk 1 text", "chunk 2 text"])
    # Force batch size of 1
    ingestion_service.batch_size = 1
    
    # Batch 1 passes, Batch 2 fails all retries
    def mock_embed_text(texts):
        if "chunk 1" in texts[0]:
            return [[0.1, 0.2]]
        raise Exception("Embedding failed")
        
    ingestion_service.embedder.embed_text.side_effect = mock_embed_text
    
    with pytest.raises(PartialIngestionError) as exc_info:
        ingestion_service.process_file_background(
            file_path=str(test_file),
            filename="test.txt",
            file_hash="dummyhash",
            box_id="box-123",
            document_id="doc-123"
        )
        
    assert "failed batches" in str(exc_info.value)
    
    # Assert partial chunks cleanup WAS called
    assert ingestion_service.db.delete_chunks_by_document.called
    
    # Verify save_document_chunks was called at least once (for chunk 1)
    assert ingestion_service.db.save_document_chunks.called
    
    # Assert partial chunks cleanup WAS called (we no longer preserve chunks)
    assert ingestion_service.db.delete_chunks_by_document.called
    
    # Ensure document status was NOT updated to 'completed'
    assert not ingestion_service.db.update_document_status.called
    
    # Assert file cleanup happened anyway
    assert not test_file.exists()

def test_process_file_background_ocr_detection(ingestion_service, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("   \n  \t  ") # Empty/whitespace only
    
    with pytest.raises(ValueError) as exc_info:
        ingestion_service.process_file_background(
            file_path=str(test_file),
            filename="test.txt",
            file_hash="dummyhash",
            box_id="box-123",
            document_id="doc-123"
        )
        
    assert "requires OCR" in str(exc_info.value)

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

class MockDocument:
    def __init__(self, pages):
        self.pages = pages
        self.page_count = len(pages)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def get_toc(self):
        return []
        
    def load_page(self, i):
        return self.pages[i]
        
class MockPage:
    def __init__(self, blocks):
        self.blocks = blocks
        
    def get_text(self, mode):
        return self.blocks
        
class MockSplitter:
    def __init__(self, chunks_with_offsets):
        self.chunks_with_offsets = chunks_with_offsets
        
    def create_documents(self, text_list):
        docs = []
        for text in text_list:
            for chunk_text, start_idx in self.chunks_with_offsets:
                doc = MagicMock()
                doc.page_content = chunk_text
                doc.metadata = {"start_index": start_idx}
                docs.append(doc)
        return docs


def test_small_pdf_chunk_merge_preserves_a_contiguous_source_span():
    source = "A" * 300 + " " + "B" * 100
    first = MagicMock()
    first.page_content = source[:300]
    first.metadata = {"start_index": 0}
    small_overlapping = MagicMock()
    small_overlapping.page_content = source[250:]
    small_overlapping.metadata = {"start_index": 250}

    merged = IngestionService._merge_small_pdf_chunks(
        [first, small_overlapping], source, min_chunk_size=200
    )

    assert len(merged) == 1
    assert merged[0].page_content == source

def test_ingestion_phase3_offsets(monkeypatch):
    import fitz

    long_text_1 = "This is page one. " * 20
    long_text_2 = "It has some text. " * 20
    long_text_3 = "This is page two. " * 20
    
    blocks_page1 = [
        (10, 10, 100, 20, long_text_1, 1, 0),
        (10, 30, 100, 40, long_text_2, 2, 0)
    ]
    blocks_page2 = [
        (10, 10, 100, 20, long_text_3, 1, 0)
    ]

    mock_doc = MockDocument([MockPage(blocks_page1), MockPage(blocks_page2)])
    monkeypatch.setattr(fitz, "open", lambda *args, **kwargs: mock_doc)

    chunk1 = (long_text_1 + "\n" + long_text_2)[:250].lower()
    chunk2 = long_text_3[:250].lower()
    chunk3 = ("Bad offset chunk " * 20)[:250].lower()
    
    mock_splitter = MockSplitter([
        (chunk1, 0),
        (chunk2, 31), # offset in normalized string
        (chunk3, 999) # This should trigger the fallback
    ])

    db_mock = MagicMock()
    service = IngestionService(db=db_mock, lexical_store=MagicMock(), embedder=MagicMock())
    service.text_splitter = mock_splitter

    saved_chunks = []
    def mock_save(chunks):
        saved_chunks.extend(chunks)
        
    db_mock.save_document_chunks.side_effect = mock_save

    monkeypatch.setattr("builtins.open", MagicMock())
    monkeypatch.setattr("os.path.getsize", lambda *args: 1000)

    service._process_pdf_streaming("dummy.pdf", "dummy.pdf", "hash", "box1", "doc1")

    assert len(saved_chunks) == 3
    
    assert saved_chunks[0]["content"] == chunk1
    assert saved_chunks[0]["page_start"] == 1
    assert saved_chunks[0]["page_end"] == 1
    assert "Pages 1-1" in saved_chunks[0]["metadata"]["context_header"]
    
    assert saved_chunks[1]["content"] == chunk2
    assert saved_chunks[1]["page_start"] == 2
    assert saved_chunks[1]["page_end"] == 2
    assert "Pages 2-2" in saved_chunks[1]["metadata"]["context_header"]
    
    assert saved_chunks[2]["content"] == chunk3
    assert saved_chunks[2]["page_start"] == 1
    assert saved_chunks[2]["page_end"] == 2
    assert "Pages 1-2" in saved_chunks[2]["metadata"]["context_header"]

def test_ingestion_whitespace_preservation(monkeypatch):
    import fitz
    
    blocks_page1 = [
        (10, 10, 100, 20, "Line 1   with   spaces.\n\nLine 2.", 1, 0)
    ]
    
    mock_doc = MockDocument([MockPage(blocks_page1)])
    monkeypatch.setattr(fitz, "open", lambda *args, **kwargs: mock_doc)
    
    # "Line 1   with   spaces.\n\nLine 2." should become "Line 1 with spaces.\n\nLine 2."
    mock_splitter = MockSplitter([
        ("Line 1 with spaces.\n\nLine 2.", 0)
    ])
    
    db_mock = MagicMock()
    service = IngestionService(db=db_mock, lexical_store=MagicMock(), embedder=MagicMock())
    service.text_splitter = mock_splitter
    
    saved_chunks = []
    db_mock.save_document_chunks.side_effect = lambda chunks: saved_chunks.extend(chunks)
    
    monkeypatch.setattr("builtins.open", MagicMock())
    monkeypatch.setattr("os.path.getsize", lambda *args: 1000)
    
    service._process_pdf_streaming("dummy.pdf", "dummy.pdf", "hash", "box1", "doc1")
    
    assert len(saved_chunks) == 1
    assert saved_chunks[0]["content"] == "Line 1 with spaces.\n\nLine 2."

