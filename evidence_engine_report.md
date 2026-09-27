# Phase 3: Evidence Engine Architecture Inspection

## 1. Current Chat/RAG Flow

**Execution Path** (`backend/app/api/chat.py` → `backend/app/services/chat_service.py`):
1. **API Endpoint** (`chat_with_documents`): Validates request and verifies box access (Synchronous).
2. **ChatService.ask_question()**:
   - `db.save_chat_message()`: Saves user message.
   - `db.get_chat_history()`: Retrieves history.
   - `_build_search_queries()`: Uses LLM to generate HyDE and Multi-query variants (Sync).
   - `_multi_query_search()`: Executes hybrid semantic+lexical search via Supabase RPC (Sync).
   - `reranker.rerank()`: Cross-encoder re-ranking (Sync).
   - `_dynamic_relevance_filter()`: Drops low-relevance chunks (Sync).
   - `_expand_with_neighbors()`: Fetches adjacent DB chunks (Sync).
   - `_determine_confidence()`: Multi-source confidence detection (Sync).
   - `_should_run_accuracy_rescue()`: Triggers a second aggressive retrieval pass if confidence is weak.
   - **Grounded-Answer Gate**: Aborts generation if `top_score < ANSWER_MIN_RELEVANCE_SCORE`.
   - **Context Builder**: Formats docs into a single text block.
   - `_build_system_prompt()`: Adjusts prompt strictness based on confidence.
   - `llm.chat_with_messages()`: Generates the answer (Sync).
   - `_extract_key_takeaways()` & `_generate_related_questions()`: Uses LLM/Regex to extract meta-data.
   - **Citation Builder**: Copies *all* retrieved docs into the response payload.

## 2. Retrieved Evidence Structure

The Supabase RPC `match_documents_hybrid_box` returns the following structure:
```json
{
    "id": "uuid",
    "document_id": "uuid",
    "content": "text",
    "embedding_score": "float",
    "lexical_score": "float",
    "chunk_index": "int",
    "page_start": "int",
    "page_end": "int",
    "section_title": "text",
    "metadata": "jsonb"
}
```
**Critical Gap**: `filename` is *not* returned by the current hybrid search RPC! However, `chat_service.py` heavily relies on `doc.get("filename")`. Immediately before context construction, the objects lack explicit filenames unless they are injected elsewhere (which they currently are not). Page numbers, section titles, and chunk indices are preserved in the dictionary but are **dropped** before being passed to the LLM.

## 3. Current Confidence & Abstention Logic

- **Relevance Score**: Prefers `rerank_score` over vector `similarity`.
- **Confidence Detection** (`_determine_confidence`): Solely based on *retrieval evidence*, not answer quality.
  - `high`: `top_score >= 0.7`
  - `multi_source`: ≥3 unique files with `top_score >= 0.5` and high score spread.
  - `medium`: `top_score >= 0.3`
  - `low`: otherwise
- **Abstention Gate**: If the best chunk's score is `< settings.ANSWER_MIN_RELEVANCE_SCORE` (usually 0.3), the system hard-aborts and returns a fallback phrase *without calling the LLM*.
- **Weakness**: The LLM can still hallucinate an answer if a chunk clears the threshold but doesn't actually contain the answer to the specific question.

## 4. Current Citation Architecture

- **How they are produced**: Citations are entirely **retrieval-based**. In `ask_question()` (line 241), the system iterates over `retrieved_docs` and blindly appends them to the `citations` list.
- **Can it answer "Which exact evidence chunk supports this statement?"**: **NO**.
  - The citations merely reflect *what was retrieved*, not *what the LLM used*.
  - There is no mapping between the LLM's claims and the source chunks.

## 5. Main Evidence-Grounding Gaps

1. **Retrieval-Citation Disconnect**: The response lists all retrieved documents as citations, even if the LLM completely ignored them.
2. **Missing Granularity**: The frontend groups citations by `filename` and only displays the first matching chunk. If multiple chunks from the same document are used, the user cannot see the others.
3. **Missing Filename Bug**: The Phase 1B RPC `match_documents_hybrid_box` fails to SELECT `d.filename`, meaning all current context headers and citations are likely rendering as `None` or empty strings.
4. **Wasted Metadata**: `page_start`, `page_end`, and `section_title` are returned by the DB but never passed into the LLM context.
5. **No Inline Citations**: The generated text does not contain inline reference markers (e.g., `[1]`), making claim verification impossible.

## 6. Recommended Evidence Engine Insertion Points

### A. Evidence Selection
- **Exact File**: `backend/app/services/chat_service.py`
- **Insertion Location**: Inside the LLM call (`llm.chat_with_messages`).
- **Why**: We should prompt the LLM to actively select and cite evidence by embedding IDs directly into its output text (e.g., "The revenue was $5M [E1]."). This avoids a second expensive LLM call for post-hoc selection.

### B. Evidence Sufficiency
- **Exact File**: `backend/app/services/chat_service.py`
- **Insertion Location**: Immediately after the LLM generation (around line 214).
- **Why**: The existing retrieval gate handles gross irrelevance, but we need a post-generation check to verify if the LLM actually utilized the evidence IDs or if it fell back to the "I could not find the answer" shield.

### C. Evidence ID Assignment
- **Exact File**: `backend/app/services/chat_service.py`
- **Insertion Location**: Inside the Context Builder loop (around line 172).
- **Why**: We must assign a deterministic ID (e.g., `[E1]`, `[E2]`) to each chunk as it is converted to text, allowing the LLM to reference it unequivocally.

### D. Citation Mapping
- **Exact File**: `backend/app/services/chat_service.py`
- **Insertion Location**: Inside the Citation Builder (around line 240).
- **Why**: Instead of blinding appending all `retrieved_docs`, we parse the generated `answer` for `[E#]` markers, and only attach the corresponding chunks to the `citations` array.

## 7. Minimal API Contract Change

We can extend the existing `Citation` model to include an `evidence_id`, `page_start`, and `page_end`. 

```json
{
  "answer": "The company was founded in 2020 [E1]. It later expanded to Europe [E2].",
  "key_takeaways": [],
  "related_questions": [],
  "session_id": "uuid-1234",
  "confidence": "high",
  "citations": [
    {
      "evidence_id": "[E1]",
      "filename": "company_history.pdf",
      "content": "Founded in 2020 in San Francisco...",
      "page_start": 2,
      "page_end": 2,
      "similarity": 0.89,
      "rerank_score": 0.95
    },
    {
      "evidence_id": "[E2]",
      "filename": "expansion_memo.docx",
      "content": "We expanded to Europe in late 2022...",
      "page_start": null,
      "page_end": null,
      "similarity": 0.81,
      "rerank_score": 0.88
    }
  ]
}
```

## 8. Frontend Impact

**Files that will need changes:**
- `frontend/src/app/workspace/chat/ChatDashboard.tsx`
- `frontend/src/components/StreamingChat.tsx` (if streaming is adapted)

**Impact:**
1. We must parse the `answer` string to convert `[E1]` markers into clickable inline badges.
2. The citation pill rendering must be updated to map from `evidence_id` rather than blindly deduplicating by `filename`.

## 9. Performance Considerations

- **LLM Calls**: Generating an answer is expensive. Post-processing the answer with a second LLM to map citations would double latency. The Evidence Engine **must** be implemented deterministically within the *single* existing generation pass (via strict prompting) and fast Regex parsing post-generation.
- **Retrieval Integrity**: The `_should_run_accuracy_rescue` logic is already highly optimized. We should not tamper with it. 

## 10. Implementation Plan (Minimal 2-Day Sequence)

1. **Fix Retrieval Bug**: Modify `schema_phase1b.sql` (or adapter) to properly return `filename` in the RPC.
2. **Context Enrichment (Evidence IDs)**: Update `chat_service.py` Context Builder to inject `[E#]`, `page_start`, and `section_title` into the context blocks.
3. **Prompt Engineering (Evidence Selection)**: Update `_build_system_prompt()` to strictly mandate the use of `[E#]` inline citations for every factual claim.
4. **Citation Mapping**: Update the Citation Builder loop to parse the generated answer using regex, discarding retrieved chunks that lack a corresponding `[E#]` in the text.
5. **API Update**: Update the `Citation` Pydantic model in `chat.py`.
6. **Frontend Update**: Modify `ChatDashboard.tsx` to render inline citations and update the source drawer to show exact mapped chunks.
7. **Testing**: Run against real documents to tune prompt adherence.
