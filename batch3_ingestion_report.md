# Implementation Report: Batch 3 — Ingestion Pipeline Hardening

## 1. Changes Made

*   **Priority 21 & 22 (Document Lifecycle & Partial Cleanup):** 
    *   Removed the special exception block for `PartialIngestionError` inside `ingestion_service.py` so that **all** ingestion failures fall into a single, centralized cleanup block. 
    *   On failure, `self.db.delete_chunks_by_document(document_id)` is deterministically called to wipe out any partial chunks, guaranteeing no "half-ingested" state.
    *   The `Exception` bubbles up to the wrapper `_process_upload_safely` in `backend/app/api/upload.py`, which catches it and deterministically updates the document row: `status = "failed"` and sets the `error_message`. 
    *   Updated `test_ingestion_service.py` to assert that partial chunks are cleaned up rather than preserved.

*   **Priority 23 (Resumable Ingestion):**
    *   **Full resumable ingestion is not implemented in Batch 3.** Instead, the pipeline was structured to be safely **idempotent/retryable**. 
    *   Because partial chunks are definitively deleted on failure (Priority 22), a future retry operation can safely re-run ingestion from the beginning without producing duplicate chunks. The document row is preserved with its `error_message`, waiting for a potential retry trigger.

*   **Priority 24 (OCR Decision):**
    *   Modified `_process_pdf_streaming` and `_process_small_file` to detect when zero chunks of text are extracted.
    *   If no text is found (e.g. image-only scanned PDFs), the pipeline raises a specific `ValueError: No extractable text was found... The document may be scanned/image-only and requires OCR. (OCR can be introduced as a future ingestion capability.)`
    *   This gracefully fails the document and records this exact limitation in the UI via the `error_message` column.

*   **Priority 25 (Improve DOCX Extraction):**
    *   Created `_extract_docx()` in `ingestion_service.py` using `python-docx`'s element tree instead of just paragraphs.
    *   The extractor iterates through the body elements to extract both `CT_P` (paragraphs/headings) and `CT_Tbl` (tables) in document order.
    *   Headings are mapped to Markdown (`#`, `##`), and tables are mapped to a deterministic `[TABLE]` row-by-row structure separated by pipes (`|`).
    *   Added a fixture-based unit test in `test_docx_extraction.py` that fully covers headings, paragraphs, and tables.

## 2. Files Changed
*   `backend/app/services/ingestion_service.py`
*   `backend/tests/test_ingestion_service.py`
*   `backend/tests/test_docx_extraction.py` (New)

## 3. Files Removed
None.

## 4. Tests Run
*   `pytest tests/test_ingestion_service.py` (10 passed)
*   `pytest tests/test_docx_extraction.py` (1 passed)

## 5. Remaining Issues
None identified in this batch scope.

## 6. Security Notes
*   Ingestion continues to enforce Box ID isolation during processing. Cleanup operations are bound strictly by `document_id`.
