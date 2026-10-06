# Implementation Report: Batch 3 — Cleanup, RLS, Cascade & Contracts

## 1. Changes Made
*   **Priority 16 (Standardize Chat API models):** Audited `backend/app/api/chat.py`, `backend/app/services/chat_service.py`, `frontend/src/app/workspace/chat/ChatDashboard.tsx`, and `frontend/src/components/StreamingChat.tsx`. The API is consistently using `box_id`, maintaining proper Box-level RLS authorization and session -> Box checks. No obsolete `tenant_id` or workspace identifiers exist in active API endpoints.
*   **Priority 17 (Clarify vector-store abstraction):** Audited `backend/app/interfaces/vector_store.py`. Added class-level docstrings outlining its actual responsibilities (acting as a Repository for Documents, Chunks, and Chat Sessions). Deleted the legacy unused method `save_documents`. Verified `search_similar` explicitly declares its `rrf_score` contract, and `delete_document` formally accepts `document_id`.
*   **Priority 18 & 19 (RLS & Cascade Verifications):** Audited SQL schema (`schema_phase1b.sql`). 
    *   **RLS verified:** `boxes`, `documents`, `document_chunks`, `chat_sessions`, and `chat_messages` are fully isolated to the user who owns the Box (via strict subqueries and `SECURITY INVOKER` functions). 
    *   **Cascades verified:** `ON DELETE CASCADE` is set identically across `boxes -> documents -> document_chunks` and `boxes -> chat_sessions -> chat_messages`.
    *   **Integration tests:** Created `test_rls_cascade.py` detailing the properties checked, but flagged them with `@pytest.mark.skip(reason="Requires live Supabase DB with RLS")` to avoid producing false passes in a local mock environment.
*   **Priority 20 (Remove obsolete/duplicate active contracts):** 
    *   Deleted `backend/app/services/chat_service_optimized.py`, which was dead code referencing the old `tenant_id` architecture.
    *   Removed `similarity` fallback logic from `retrieval_engine.py` and `evidence_engine.py`. They now correctly only expect `rrf_score`, `embedding_score`, `lexical_score`, or `rerank_score`.

## 2. Files Changed
*   `backend/app/interfaces/vector_store.py`
*   `backend/app/infrastructure/supabase_adapter.py`
*   `backend/app/services/evidence_engine.py`
*   `backend/app/services/retrieval_engine.py`
*   `backend/tests/test_rls_cascade.py` (New)

## 3. Files Removed
*   `backend/app/services/chat_service_optimized.py`

## 4. Tests Run
*   `pytest backend/tests/test_citation_schema.py` (Passes)
*   `pytest backend/tests/test_box_counts.py` (Passes)
*   `pytest backend/tests/test_upload_extensions.py` (Passes)
*   Verified RLS structures inside `schema_phase1b.sql`.

## 5. Remaining Issues
*   Dynamic "Good morning" Dashboard task from previous batches.

## 6. Security Notes
*   Confirmed `match_documents_hybrid_box` uses `SECURITY INVOKER` inside Supabase to securely limit embeddings returned to the logged-in user.
