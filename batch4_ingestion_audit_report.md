# Ingestion Service Audit Report

## 1. Architectural Overview

The **Ingestion Service** (`backend/app/services/ingestion_service.py`) is the core engine responsible for processing uploaded files, extracting text, generating vector embeddings, and storing them in Supabase. 

It is designed primarily for **memory safety** and **contextual accuracy**, routing files into two distinct pipelines:
- `_process_small_file()`: For standard files (DOCX, TXT, CSV, XLSX).
- `_process_pdf_streaming()`: For large PDFs. Uses a memory-safe, streaming approach to avoid `OOM` (Out-of-Memory) crashes on servers with limited resources.

## 2. The PDF Streaming Pipeline (Step-by-Step)

When a large PDF is processed, the system executes the following steps:

1. **Table of Contents Extraction:** It first parses the PDF's native Table of Contents (`doc.get_toc()`) to map every page to its respective Section Title.
2. **Page Batching:** It loops through the PDF in chunks of `PDF_PAGE_BATCH_SIZE` (currently set to **50** pages).
3. **Block-Based Text Extraction:** Using `PyMuPDF` (`fitz`), it extracts text in structural blocks rather than raw text. It sorts these blocks vertically and horizontally to preserve the natural reading order (crucial for multi-column PDFs).
4. **Smart Splitting:** The text is passed to `RecursiveCharacterTextSplitter`. Instead of blindly cutting text at 1000 characters, it respects markdown boundaries (e.g., `## `, `### `), paragraph boundaries (`\n\n`), and sentence boundaries.
5. **Contextual Enrichment:** Before embedding, a header is prepended to *every single chunk*:
   `[Document: filename | Type: PDF | Pages X-Y | Chunk Z]`
   This ensures that the embedding model understands the global context of an isolated sentence.
6. **Batch Embedding:** Chunks are grouped into `INGESTION_BATCH_SIZE` (currently **32**) and sent to the FastEmbed/ONNX engine.
7. **Database Persistence:** The vectors are stored in Supabase (`document_chunks`).

## 3. Performance & Bottlenecks

### The 15-Minute Bottleneck (Fixed)
During the audit of a 184-page document, the ingestion took **939.68 seconds** (15.6 minutes). The timing breakdown revealed:
- **Extraction:** 1.46s
- **Splitting:** 0.02s
- **Database (Supabase):** 83.88s
- **Embedding:** **850.30s**

**Root Cause:** The `INGESTION_BATCH_SIZE` was configured to `10`, and `PDF_PAGE_BATCH_SIZE` was `10`. This forced the system to execute **121 separate tiny embedding calls** averaging 4.8 chunks each. The CPU/ONNX runtime could not parallelize efficiently.

### Target Optimization Applied
The configuration was updated to allow aggressive parallelization without breaching memory limits:
* `PDF_PAGE_BATCH_SIZE` = **50** (gathers more chunks before processing).
* `INGESTION_BATCH_SIZE` = **32** (optimizes multi-core CPU usage via FastEmbed).

**Expected Outcome:** The 579 chunks will now execute in ~19 parallelized batches instead of 121 micro-batches, slashing the 850-second embedding time dramatically.

## 4. Reliability & Error Handling

The service implements strict data-integrity protocols:
* **Orphan Chunk Prevention:** If any batch fails after `MAX_RETRIES`, the system throws a `PartialIngestionError`. The global `finally/except` block triggers `delete_chunks_by_document()`, wiping all inserted chunks from the database so the user can cleanly retry without duplicating data.
* **Deletion Mid-Ingestion:** Catches PostgreSQL `23503` (Foreign Key Violation). If a user deletes the document from the UI while ingestion is running in the background, the pipeline detects the missing foreign key and aborts gracefully (`DocumentDeletedError`) without spamming errors.
* **Memory Cleanup:** Enforces aggressive garbage collection (`gc.collect()`) and explicit variable deletion (`del chunks`, `del batch_text`) at the end of every page batch to prevent RAM bloat during 1000+ page ingestion.

## 5. Next Steps / Recommendations

1. **Supabase Bulk Inserts:** DB persistence currently takes ~83 seconds. We should verify if Supabase's `postgrest-py` client is utilizing single HTTP requests per chunk batch. If not, batching the DB inserts across multiple PDF batches could reduce network round-trips.
2. **Summarization:** LLM Summarization currently takes `0.00s` because it is disabled in `dependencies.py` to save tokens and time. When re-enabled, it should be processed asynchronously or decoupled from the main embedding pipeline.
