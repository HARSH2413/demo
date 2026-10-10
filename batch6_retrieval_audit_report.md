# Retrieval Engine Audit Report

## 1. Architectural Overview

The Retrieval system in DocIntel is highly robust, using a multi-stage **Hybrid Retrieval + Re-ranking pipeline** coordinated between the `RetrievalEngine` and the `EvidenceEngine`.

The primary flow for a user query is:
1. **Cache Check:** Avoids redundant searches.
2. **Hybrid Search:** Runs Dense (Vector) and Lexical (BM25) search simultaneously.
3. **RRF Merge:** Fuses vector ranks and keyword ranks using Reciprocal Rank Fusion.
4. **Re-ranking:** A cross-encoder model evaluates the merged chunks and re-sorts them.
5. **Dynamic Filtering:** `EvidenceEngine` drops low-quality chunks based on absolute scores.
6. **Neighbor Expansion:** Grabs the surrounding context (previous/next chunks) for surviving chunks.

---

## 2. Hybrid Search & Lexical Expansion

In `retrieval_engine.py`, search is fundamentally hybrid. 

**Dense Search:** 
- The query is embedded using `BAAI/bge-large-en-v1.5`.
- A similarity search is performed against Supabase (`pgvector`), retrieving `Top-K = 20`.

**Lexical Search (BM25):**
- The query is first run through `_expand_lexical_variants()` (e.g., expanding "gst" to "Goods and Services Tax", "pf" to "Provident Fund").
- It then searches the local BM25S index, grabbing `Top-K = 20`.

**Reciprocal Rank Fusion (RRF):**
- The system merges the two sets of 20 using `rrf_k = 60`. 
- RRF is mathematically score-agnostic; it only cares about rank. A chunk that ranks #2 in Dense and #10 in Lexical gets an RRF score of:
  `1/(60+2) + 1/(60+10)` = `0.0304`
- This ensures that chunks containing exact keyword matches and chunks with deep semantic meaning bubble to the top.

---

## 3. Cross-Encoder Re-Ranking

The RRF output is mathematically robust but context-blind. The pipeline passes the top 20 chunks to the **Cross-Encoder Re-ranker** (`Xenova/ms-marco-MiniLM-L-12-v2`).

* **Why?** Dense embeddings compress a chunk into a single point in space. A cross-encoder reads the `[Query] + [Chunk]` together, understanding the deep relationship between the specific question and the paragraph.
* **Output:** It aggressively re-scores the chunks from 0.0 to 1.0, and slices the list down to the final `Top-K = 5` chunks.

---

## 4. Evidence Engine (Quality Control)

Before handing the chunks to the LLM, the `EvidenceEngine` applies strict quality control:

**Dynamic Relevance Thresholding:**
- It reads the `rerank_score`. If a chunk is below `min_relevance_score` (0.3), it is dropped.
- *Safety Net:* If strict filtering leaves fewer than 2 chunks, it dynamically lowers the threshold to `min_relevance_score_low` (0.1) to prevent "I don't know" responses when the answer is partially there.
- *Note:* It explicitly ignores `rrf_score` for thresholding because RRF is an arbitrary rank fraction, not an absolute similarity distance.

**Neighbor Context Expansion:**
- For chunks that survive the filter, the engine looks at their `chunk_index`.
- It executes `get_multi_neighboring_chunks()` to pull `chunk_index - 1` and `chunk_index + 1`.
- It stitches these into a `neighbor_context` field. This prevents the LLM from hallucinating when a chunk starts with "He did it..." by providing the previous paragraph to clarify who "He" is.

**Accuracy Rescue (Multi-Query Expansion):**
- If the top chunk scores below `0.12` (a complete miss), the engine flags `should_run_accuracy_rescue = True`.
- This triggers `retrieve_documents_multi()`, which generates 3 rewritten variations of the query, executes hybrid search for *all three*, deduplicates them by highest score, merges via RRF, and reranks them.
