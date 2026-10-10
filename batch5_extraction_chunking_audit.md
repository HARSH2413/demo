# Extraction and Chunking Audit Report

## 1. Text Extraction (PyMuPDF Block-Based Extraction)

The text extraction logic in `_process_pdf_streaming` is highly optimized to handle complex PDF layouts (such as double columns, sidebars, and nested headers) without scrambling the reading order.

### Step-by-Step Breakdown:
1. **Streaming Load**: Instead of parsing the entire document, it loads only `PDF_PAGE_BATCH_SIZE` (50 pages) into memory at a time using `doc.load_page(page_num)`.
2. **Block-Based Parsing**: Instead of `page.get_text("text")` (which reads naively from left-to-right ignoring structure), it uses `page.get_text("blocks")`. This returns a list of structural elements (paragraphs, tables, images) alongside their exact Cartesian coordinates on the page.
3. **Filtering**: It explicitly filters out non-text blocks (like images or vector paths) by checking `b[6] == 0` (where `0` denotes a text block in PyMuPDF).
4. **Coordinate Sorting**: This is the most critical step for accuracy. It sorts the blocks by `b[1]` (y-coordinate/vertical), then `b[0]` (x-coordinate/horizontal). 
   ```python
   blocks.sort(key=lambda b: (b[1], b[0]))
   ```
   This guarantees that text is read naturally from top-to-bottom. If there is a two-column layout, it will process the first column completely before the second (or top-to-bottom depending on the exact PDF rendering layer), preserving sentence flow.
5. **Reassembly**: The blocks are rejoined with `\n` to maintain paragraph structures for the chunker.

## 2. Text Chunking (Hierarchical Splitting)

Once the 50-page batch is extracted into a single string (`batch_text`), it is handed over to the chunking pipeline. The chunking strategy prioritizes semantic boundaries over strict character limits.

### The Separator Hierarchy
The `RecursiveCharacterTextSplitter` is initialized with a specific hierarchy of separators:
```python
separators=[
    "\n## ",       # H2 headings (highest priority split)
    "\n### ",      # H3 headings
    "\n#### ",     # H4 headings
    "\n\n",        # Double newline (paragraph boundary)
    "\n",          # Single newline
    ". ",          # Sentence boundary
    " ",           # Word boundary (last resort)
]
```
* **Why this matters**: The chunker will *first* attempt to split the 50 pages precisely at Markdown headings (`## `). If a section between two headings exceeds the `CHUNK_SIZE` (1000 chars), it falls back to splitting at paragraphs (`\n\n`), then sentences (`. `). 
* **Result**: Chunks almost never cut off in the middle of a sentence or split a single cohesive paragraph into two different vector embeddings.

## 3. Contextual Enrichment (The Accuracy Multiplier)

Before the raw chunks are sent to the AI Embedding model, the service performs a critical enrichment step:

```python
headers = [
    f"[Document: {filename} | Type: {file_type} | Pages {page_start+1}-{page_end} | Chunk {i+j+1}]"
]
contextual_batch = [f"{headers[j]}\n\n{chunk}"]
```

### Why Context Enrichment is Used
If the LLM is asked a question about the document, a raw chunk like *"The revenue grew by 15% in Q3"* has zero context. The embedding model won't know *which* company or *which* document this belongs to.

By forcefully injecting the header, the embedding model sees:
`[Document: 2026_Financial_Report.pdf | Type: PDF | Pages 1-50 | Chunk 12]`
`The revenue grew by 15% in Q3.`

This anchors the vector embedding geographically within the document, significantly improving the semantic search retrieval accuracy when the user asks questions spanning multiple documents.

## 4. Metadata Alignment

Finally, when the chunk is saved to the Supabase Database (`document_chunks` table), it is saved with hard metadata:
- `page_start` & `page_end`: Used for UI citations.
- `section_title`: (Extracted from the PDF Table of Contents).
- `chunk_index`: Ensures the chunks can be retrieved and reconstructed in precise order.
