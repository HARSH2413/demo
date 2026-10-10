# Master RAG Architecture Audit Report
*End-to-End System Breakdown from Upload to Answer Generation*

## 1. Ingestion Phase (Memory-Safe Streaming)
**Goal:** Process massive documents without crashing the server or losing structural context.

* **Batching:** Instead of loading whole PDFs into RAM, the system loads pages in batches (`PDF_PAGE_BATCH_SIZE = 50`).
* **Block Extraction:** Uses PyMuPDF's block extraction, explicitly ignoring images and sorting text structurally (Y-coordinate then X-coordinate) to preserve multi-column reading order.
* **Smart Splitting:** Uses a `RecursiveCharacterTextSplitter` configured with hierarchical Markdown separators (`##`, `###`, `\n\n`) to ensure chunks don't split mid-sentence or mid-paragraph.
* **Contextual Enrichment (Crucial):** Before a chunk is embedded, it gets a header: `[Document: filename.pdf | Pages: 1-50 | Chunk: 12]`. This locks the vector into a semantic location, preventing the retrieval model from losing context on isolated sentences.
* **Parallel Embedding:** The chunks are batched (`INGESTION_BATCH_SIZE = 32`) to fully saturate the multi-core CPU using ONNX/FastEmbed before being flushed to the Supabase `pgvector` store.

## 2. Retrieval Phase (Hybrid & Re-Ranking)
**Goal:** Find the absolute best evidence with zero bias toward keyword-only or semantic-only matching.

* **Query Rewriting:** (If enabled) Rewrites user queries to resolve conversational context (e.g., "what did it say" -> "what did the financial report say").
* **Dual-Track Search:** 
   1. **Dense Search:** Vector similarity search using `BAAI/bge-large-en-v1.5` against Supabase.
   2. **Lexical Search (BM25):** Keyword search against a local BM25S index, using term expansion (e.g., "gst" -> "Goods and Services Tax").
* **Reciprocal Rank Fusion (RRF):** The results of both searches are merged mathematically (`rrf_k = 60`). This algorithm rewards chunks that rank highly in both keyword and semantic matches.
* **Cross-Encoder Re-Ranking:** RRF is fast but context-blind. The top 20 fused results are passed to `ms-marco-MiniLM-L-12-v2`, which reads the actual query alongside the chunk to score deep contextual relevance, slicing the final list down to the Top 5.

## 3. Quality Control (Evidence Engine)
**Goal:** Prevent hallucinations by aggressively filtering out bad data *before* the LLM sees it.

* **Dynamic Thresholding:** Any chunk with a re-rank score below `0.3` is instantly deleted. (If this deletes too much, it safely lowers the threshold to `0.1` to salvage partial answers).
* **Neighbor Expansion:** For surviving chunks, the engine fetches `chunk_index - 1` and `chunk_index + 1` from the database. This gives the LLM the surrounding paragraphs so it doesn't misunderstand isolated facts.
* **Accuracy Rescue:** If the highest-scoring chunk across the whole database is still below `0.12`, the system assumes it missed. It triggers a "rescue pass"—rewriting the query 3 different ways, running 3 parallel hybrid searches, deduplicating them, and re-ranking the massive merged list.

## 4. Generation & Citation Phase (Anti-Hallucination)
**Goal:** Synthesize a coherent answer and rigidly enforce real citations.

* **Context Building:** The surviving, re-ranked chunks are formatted into a rigid block:
  ```text
  --- EVIDENCE [E1] ---
  [chunk text...]
  ```
* **Strict Prompting:** The LLM is commanded to answer using *only* the provided evidence and must cite using the exact `[E1]`, `[E2]` format.
* **Citation Integrity Check (The Firewall):** Before the user sees the answer, a Regex parser scrubs it. 
  1. It extracts every `[E#]` citation the LLM typed.
  2. It checks if `[E#]` was actually in the provided context block.
  3. If the LLM hallucinated a citation (e.g., `[E99]`), the Regex aggressively strips it out.
  4. If the LLM answered but failed to use *any* valid citations, the system deletes the answer and replaces it with the fallback phrase: *"I don't have enough information in the documents to answer that."*

## Summary
This RAG pipeline sacrifices a small amount of speed to guarantee **enterprise-grade accuracy**. By relying on Cross-Encoders, RRF, Contextual Enrichment, and aggressive post-generation Citation scrubbing, it virtually eliminates hallucinations.
