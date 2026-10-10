import fitz
from app.services.ingestion_service import IngestionService
from app.core.config import settings
from unittest.mock import MagicMock

def run():
    # Create a 2 page PDF
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((50, 50), "This is the very first page of our test PDF document.\nWe will add enough text here so that it spans into a second chunk. " * 20)
    page2 = doc.new_page()
    page2.insert_text((50, 50), "This is the second page. " * 20)
    doc.save("test_mapping.pdf")
    doc.close()

    # Mock DB and Embedder
    db_mock = MagicMock()
    embedder_mock = MagicMock()
    
    # We just want to capture the records passed to save_document_chunks
    captured_records = []
    def mock_save(records):
        captured_records.extend(records)
        
    db_mock.save_document_chunks.side_effect = mock_save
    
    service = IngestionService(db=db_mock, lexical_store=MagicMock(), embedder=embedder_mock, chunk_size=300, chunk_overlap=50)
    
    service._process_pdf_streaming(
        "test_mapping.pdf", "test_mapping.pdf", "hash123", "box123", "doc123"
    )
    
    for i, r in enumerate(captured_records):
        if r['page_start'] != r['page_end']:
            print(f"--- Chunk {i+1} (SPANNING) ---")
            print(f"Pages: {r['page_start']}-{r['page_end']}")
            print(f"Header: {r['metadata']['context_header']}")
            print(f"Text Preview: {r['content'][:100]}...\n")
        elif i < 2:
            print(f"--- Chunk {i+1} ---")
            print(f"Pages: {r['page_start']}-{r['page_end']}")
            print(f"Header: {r['metadata']['context_header']}")
            print(f"Text Preview: {r['content'][:100]}...\n")

if __name__ == "__main__":
    run()
