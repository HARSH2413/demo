# Implementation Report: Batch 2 — Database & API Contract Cleanup

## 1. Changes Made
*   **Priority 11 (Add efficient Box document counts):** Implemented efficient `count` using Supabase relations in `supabase_adapter.py` for both `list_boxes` and `get_box`. Added tests for it.
*   **Priority 12 (Delete documents by document_id):** Modified `delete_document` in `IVectorStore` and `supabase_adapter.py` to require `document_id`. Updated the Documents API endpoints to use `document_id` and handle deletion properly. Updated frontend `ChatDashboard.tsx` and `KnowledgeBaseView.tsx`.
*   **Priority 13 (Resolve .xls inconsistency):** Identified that the `.xls` format (Excel 97-2003) is completely unsupported by `openpyxl`. Removed `.xls` extension support from `ingestion_service.py` to match the REST API. Added `test_upload_extensions.py` to enforce consistency.
*   **Priority 14 (Standardize Documents API):** Cleaned up the `get_documents` endpoint in `documents.py` to return a flat list under `data`. Handled this change safely in `ChatDashboard.tsx` by using `.data || .documents || .files`.
*   **Priority 15 (Citation API Contract):** Expanded the `Citation` Pydantic model in `chat.py` to reflect actual `ChatService` output (`evidence_id`, `chunk_index`, etc.). Migrated away from legacy `similarity` to output proper `embedding_score`, `lexical_score`, and `rrf_score`. Updated `frontend` interfaces across the board. Also addressed the `IVectorStore` missing interface mismatches.

## 2. Files Changed
*   `backend/app/infrastructure/supabase_adapter.py`
*   `backend/app/services/ingestion_service.py`
*   `backend/app/services/chat_service.py`
*   `backend/app/services/chat_service_optimized.py`
*   `backend/app/api/documents.py`
*   `backend/app/api/chat.py`
*   `backend/app/interfaces/vector_store.py`
*   `frontend/src/app/workspace/chat/ChatDashboard.tsx`
*   `frontend/src/components/chat/KnowledgeBaseView.tsx`
*   `frontend/src/components/StreamingChat.tsx`
*   `backend/tests/test_box_counts.py` (New)
*   `backend/tests/test_upload_extensions.py` (New)
*   `backend/tests/test_citation_schema.py` (New)

## 3. Files Removed
None in this batch (Drive API removal was Batch 1).

## 4. Tests Run
*   `$env:PYTHONPATH="."; pytest tests/test_box_counts.py` — Passed.
*   `$env:PYTHONPATH="."; pytest tests/test_upload_extensions.py` — Passed.
*   `$env:PYTHONPATH="."; pytest tests/test_citation_schema.py` — Passed.
*   `mypy backend/app` — Verified reduction in typing errors (specifically addressed the IVectorStore mismatch).

## 5. Remaining Issues
*   Mypy/Type-hinting errors primarily related to complex `JSON` dict structures within `supabase_adapter.py` and `Settings` initialization in `config.py`.
*   Dashboard dynamic greeting ("Good morning") UI task is still in backlog.

## 6. Security Notes
*   Properly constrained file deletions by verifying `box_id` along with `document_id` via Supabase RLS policies (cascade rules).
