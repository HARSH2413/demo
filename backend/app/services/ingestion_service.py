"""
Ingestion Service — memory-safe document processing with contextual chunking.

Processes PDF, DOCX, TXT, CSV, and XLSX files into vector chunks.
Each chunk is enriched with document metadata (filename, chunk position)
so embeddings capture document-level context, not just raw text.

MEMORY SAFETY: Large PDFs (150MB+) are processed in page batches
to avoid the OOM killer crashing VS Code / uvicorn. Text is never
held entirely in memory — it's extracted, chunked, embedded, and
flushed to DB in streaming fashion.

ACCURACY FEATURES (v2):
  - Heading-aware semantic chunking (splits at ## before fixed-size)
  - Document summary generation (LLM creates a summary stored as chunk #0)
  - Block-based PDF extraction (preserves document structure)
  - Richer contextual chunk headers (file type + position metadata)
"""
import csv
import fitz  # PyMuPDF

class PartialIngestionError(Exception):
    """Raised when one or more batches fail during ingestion, but some chunks succeeded."""
    pass

class DocumentDeletedError(Exception):
    """Raised when a document is deleted by the user while ingestion is still processing."""
    pass

import gc
import os
import time
import re
from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.interfaces.vector_store import IVectorStore
from app.interfaces.lexical_store import ILexicalStore
from app.interfaces.embedder import IEmbedder
from app.interfaces.llm import ILLM
from app.core.logger import logger
from app.services.hierarchical_chunking import HierarchicalChunker

# Number of PDF pages to process at a time (kept small for bge-large memory safety).
PDF_PAGE_BATCH_SIZE = 20


class IngestionService:
    def __init__(
        self,
        db: IVectorStore,
        lexical_store: ILexicalStore,
        embedder: IEmbedder,
        chunk_size: int = 1000,
        chunk_overlap: int = 300,
        batch_size: int = 50,
        llm: Optional[ILLM] = None,
    ):
        self.db = db
        self.lexical_store = lexical_store
        self.embedder = embedder
        self.batch_size = batch_size
        self.llm = llm  # Optional: used for document summary generation
        self.hierarchical_chunker = HierarchicalChunker(chunk_size=chunk_size)
        # Heading-aware separators — respects document structure before fixed-size splits
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n## ",       # H2 headings (highest priority split)
                "\n### ",      # H3 headings
                "\n#### ",     # H4 headings
                "\n\n",        # Double newline (paragraph boundary)
                "\n",          # Single newline
                ". ",          # Sentence boundary
                " ",           # Word boundary (last resort)
            ],
            add_start_index=True
        )

    def process_file_background(self, file_path: str, filename: str, file_hash: str, box_id: str, document_id: str):
        """
        Background worker for processing files of any size.

        Routes by file type:
          PDF  → streaming page-by-page (memory-safe)
          DOCX/TXT/CSV/XLSX → standard processing

        Also generates a document summary (if LLM is available).
        """
        try:
            filename_lower = filename.lower()
            file_type = self._detect_file_type(filename)

            if filename_lower.endswith(".pdf"):
                self._process_pdf_streaming(file_path, filename, file_hash, box_id, document_id, file_type)
            else:
                self._process_small_file(file_path, filename, file_hash, box_id, document_id, file_type)

            # Successfully completed ingestion
            self.db.update_document_status(document_id, "completed")
            self.lexical_store.invalidate_box(box_id)

        except DocumentDeletedError as e:
            logger.warning(f"Ingestion aborted for '{filename}': Document was deleted by the user.")
            # No cleanup needed in DB since the cascade delete handles it
        except Exception as e:
            logger.error(f"Ingestion failed for '{filename}': {e}")
            try:
                logger.warning(f"Cleaning up partial chunks for failed document {document_id}")
                self.db.delete_chunks_by_document(document_id)
            except Exception as cleanup_e:
                logger.error(f"Failed to clean up partial chunks for {document_id}: {cleanup_e}")
            raise e
        finally:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temp file: {file_path}")
                except Exception as cleanup_e:
                    logger.error(f"Failed to clean up temp file '{file_path}': {cleanup_e}")

    def _process_pdf_streaming(self, file_path: str, filename: str, file_hash: str, box_id: str, document_id: str, file_type: str = "PDF"):
        """Memory-safe PDF processing — pages in batches with block-based extraction."""
        start_total = time.perf_counter()
        
        with fitz.open(file_path) as doc:
            total_pages = doc.page_count
            logger.info(f"Processing PDF '{filename}' | {total_pages} pages | batch size {PDF_PAGE_BATCH_SIZE}")
    
            total_chunks_saved = 0
            failed_batches = 0
            all_text_for_summary = []  # Collect first pages for summary generation
            global_chunk_index = 1
            
            # Metrics
            t_extract = 0.0
            t_split = 0.0
            t_embed = 0.0
            t_db = 0.0
            t_summary = 0.0
            total_embed_batches = 0
            
            # Extract PDF Table of Contents for deterministic section titles
            toc = doc.get_toc()
            page_to_section = {}
            current_section = None
            if toc:
                for entry in toc:
                    lvl, title, page_num = entry
                    if page_num not in page_to_section:
                        page_to_section[page_num] = title
    
            for page_start in range(0, total_pages, PDF_PAGE_BATCH_SIZE):
                page_end = min(page_start + PDF_PAGE_BATCH_SIZE, total_pages)
    
                t0 = time.perf_counter()
                from app.utils.pdf_parser import sort_blocks_column_aware
                
                page_texts = []
                for page_num in range(page_start, page_end):
                    current_section = page_to_section.get(page_num + 1, current_section)
                    page = doc.load_page(page_num)
                    blocks = page.get_text("blocks")
                    blocks = sort_blocks_column_aware(blocks, page_rotation=getattr(page, 'rotation', 0))
                    page_text = "\n".join(b[4] for b in blocks if len(b) >= 7 and b[6] == 0)
                    
                    # Normalize text: fold case, strip glyphs, collapse whitespace but preserve newlines
                    page_text = page_text.lower()
                    page_text = re.sub(r'[\u25a0-\u25ff\u2022\u202d\u202c]', '', page_text)
                    page_text = re.sub(r'[ \t]+', ' ', page_text).strip()
                    
                    
                    # Heuristic for section title if TOC is missing
                    if not page_to_section.get(page_num + 1):
                        for b in blocks:
                            if len(b) >= 7 and b[6] == 0:
                                line_text = b[4].strip()
                                # Short, uppercase line or starts with numbering (e.g. "1. TOPIC")
                                if 3 < len(line_text) < 60 and (line_text.isupper() or re.match(r'^\d+\.\s+[A-Z]', line_text)):
                                    page_to_section[page_num + 1] = line_text
                                    break
                    current_section = page_to_section.get(page_num + 1, current_section)
                    if current_section:
                        page_to_section[page_num + 1] = current_section
                                    
                    page_texts.append(page_text)
                    
                # Compute normalized offsets
                batch_text = ""
                page_offsets = [] # (start_idx, end_idx, actual_page_num)
                current_idx = 0
                for i, text in enumerate(page_texts):
                    start_idx = current_idx
                    if i > 0 and text:
                        batch_text += " "
                        start_idx += 1
                        
                    batch_text += text
                    end_idx = start_idx + len(text)
                    page_offsets.append((start_idx, end_idx, page_start + i + 1))
                    current_idx = len(batch_text)

                t_extract += time.perf_counter() - t0
    
                # Collect text from first 3 pages for summary
                if page_start == 0:
                    all_text_for_summary.append(batch_text[:3000])
    
                del page_texts
    
                if not batch_text.strip():
                    continue
    
                chunk_docs_raw = self.text_splitter.create_documents([batch_text])
                
                chunk_docs = self._merge_small_pdf_chunks(chunk_docs_raw, batch_text)
                        
                t_split += time.perf_counter() - t0
                
                chunks_info = []
                last_successful_offset = 0
                for c_doc in chunk_docs:
                    c_text = c_doc.page_content
                    
                    # Robust recalculation for merged chunks
                    c_start = c_doc.metadata.get("start_index", 0)
                    actual_start = batch_text.find(c_text[:50], max(0, c_start - 500))
                    if actual_start != -1:
                        c_start = actual_start
                        
                    c_end = c_start + len(c_text)
                    
                    if batch_text[c_start:c_end] != c_text:
                        logger.error("Offset mismatch in chunk! Text not found. Falling back to batch-level page mapping.")
                        c_start = -1
                                
                    if c_start == -1:
                        c_page_start = page_start + 1
                        c_page_end = page_end
                    else:
                        last_successful_offset = c_end
                        overlapping = [
                            p_num for (p_start, p_end, p_num) in page_offsets
                            if p_start <= c_end and p_end >= c_start
                        ]
                        if overlapping:
                            c_page_start = min(overlapping)
                            c_page_end = max(overlapping)
                        else:
                            c_page_start = page_start + 1
                            c_page_end = page_end
                            
                    chunks_info.append({
                        "text": c_text,
                        "page_start": c_page_start,
                        "page_end": c_page_end
                    })
                    
                del batch_text
                del chunk_docs
    
                if not chunks_info:
                    continue
    
                for i in range(0, len(chunks_info), self.batch_size):
                    embed_batch = chunks_info[i : i + self.batch_size]
    
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            headers = []
                            for j, cinfo in enumerate(embed_batch):
                                sec = page_to_section.get(cinfo['page_start']) or "Document"
                                sec_str = f" | Section: {sec}" if (sec and sec.strip()) else ""
                                headers.append(f"[Document: {filename} | Type: {file_type} | Pages {cinfo['page_start']}-{cinfo['page_end']}{sec_str} | Chunk {global_chunk_index + j}]")
                                
                            contextual_batch = [
                                f"{headers[j]}\n\n{cinfo['text']}"
                                for j, cinfo in enumerate(embed_batch)
                            ]
                            t0 = time.perf_counter()
                            embeddings = self.embedder.embed_text(contextual_batch)
                            t_embed += time.perf_counter() - t0
                            del contextual_batch
    
                            records = [
                                {
                                    "document_id": document_id,
                                    "box_id": box_id,
                                    "content": cinfo['text'],
                                    "embedding": embeddings[j],
                                    "chunk_index": global_chunk_index + j,
                                    "page_start": cinfo['page_start'],
                                    "page_end": cinfo['page_end'],
                                    "section_title": page_to_section.get(cinfo['page_start']),
                                    "metadata": {
                                        "type": file_type,
                                        "context_header": headers[j],
                                        "chunk_kind": "child",
                                        # PDF extraction supplies TOC/heading labels per page.
                                        # A page range without a detected label is a safe fallback
                                        # parent, rather than pretending a cross-topic batch is one section.
                                        "parent_id": f"pdf-section-{sec}",
                                        "parent_title": sec,
                                        "section_path": [sec],
                                        "block_type": "section",
                                        "child_index_in_parent": global_chunk_index + j,
                                    }
                                }
                                for j, cinfo in enumerate(embed_batch)
                            ]
    
                            t0 = time.perf_counter()
                            self.db.save_document_chunks(records)
                            t_db += time.perf_counter() - t0
                            
                            total_chunks_saved += len(embed_batch)
                            total_embed_batches += 1
                            del records, embeddings
                            break
                        except Exception as e:
                            # Check if the document was deleted by the user (foreign key violation)
                            if "23503" in str(e) or "foreign key" in str(e).lower():
                                raise DocumentDeletedError(f"Document {document_id} no longer exists.")
                                
                            if attempt == max_retries - 1:
                                failed_batches += 1
                                logger.error(f"Failed batch for pages {page_start+1}-{page_end}: {e}")
                            else:
                                logger.warning(f"Retrying batch for pages {page_start+1}-{page_end} (attempt {attempt + 1})")
    
                    global_chunk_index += len(embed_batch)
    
                gc.collect()
    
                logger.info(f"PDF '{filename}' | pages {page_start+1}-{page_end}/{total_pages} | {total_chunks_saved} chunks")


            
        t_total = time.perf_counter() - start_total
        avg_batch = total_chunks_saved / max(1, total_embed_batches)
        
        logger.info(
            f"INGESTION AUDIT [{filename}]: "
            f"Pages={total_pages} | Chunks={total_chunks_saved} | EmbedBatches={total_embed_batches} | AvgBatch={avg_batch:.1f} || "
            f"Time: Total={t_total:.2f}s | Extract={t_extract:.2f}s | Split={t_split:.2f}s | Embed={t_embed:.2f}s | DB={t_db:.2f}s"
        )

        if total_chunks_saved == 0 and failed_batches == 0:
            raise ValueError("No extractable text was found in this PDF. The document may be scanned/image-only and requires OCR. (OCR can be introduced as a future ingestion capability.)")

        if failed_batches > 0:
            logger.warning(f"Completed '{filename}' with {failed_batches} failed batches | {total_chunks_saved} chunks")
            raise PartialIngestionError(f"Completed with {failed_batches} failed batches | {total_chunks_saved} chunks saved")
        else:
            logger.info(f"Successfully ingested '{filename}' | {total_pages} pages → {total_chunks_saved} chunks")

    def _process_small_file(self, file_path: str, filename: str, file_hash: str, box_id: str, document_id: str, file_type: str = "Document"):
        """Standard processing for DOCX, TXT, CSV, and XLSX files."""
        start_total = time.perf_counter()
        t_embed = 0.0
        t_db = 0.0
        
        t0 = time.perf_counter()
        raw_text = self._extract_text_from_disk(file_path, filename)
        t_extract = time.perf_counter() - t0
        logger.info(f"Extracted text from '{filename}' ({len(raw_text)} chars)")

        if not raw_text.strip():
            raise ValueError("No extractable text was found in this document. The document may be scanned/image-only and requires OCR. (OCR can be introduced as a future ingestion capability.)")

        t0 = time.perf_counter()
        # Build logical parents first (headings/sheets/datasets), then create
        # embedding-sized children.  Only the children are embedded.
        chunks = self.hierarchical_chunker.build_children(raw_text, file_type, self.text_splitter)
        t_split = time.perf_counter() - t0
        total_chunks = len(chunks)
        logger.info(f"Split '{filename}' into {total_chunks} chunks")



        total_batches = (total_chunks + self.batch_size - 1) // self.batch_size
        failed_batches = 0
        global_chunk_index = 1
        
        for i in range(0, total_chunks, self.batch_size):
            batch_num = i // self.batch_size + 1
            batch_data = chunks[i : i + self.batch_size]

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    headers = [
                        f"[Document: {filename} | Type: {file_type} | Section: {' > '.join(item.section_path)} | Chunk {i + j + 1}/{total_chunks}]"
                        for j, item in enumerate(batch_data)
                    ]
                    contextual_batch = [
                        f"{headers[j]}\n\n{item.content}"
                        for j, item in enumerate(batch_data)
                    ]

                    t0 = time.perf_counter()
                    embeddings = self.embedder.embed_text(contextual_batch)
                    t_embed += time.perf_counter() - t0
                    del contextual_batch

                    records = [
                        {
                            "document_id": document_id,
                            "box_id": box_id,
                            "content": item.content,
                            "embedding": embeddings[j],
                            "chunk_index": global_chunk_index + j,
                            "section_title": item.parent_title if item.parent_title not in {"Document", "Dataset", "Workbook"} else None,
                            "metadata": {
                                "type": file_type,
                                "context_header": headers[j],
                                **item.metadata(),
                            }
                        }
                        for j, item in enumerate(batch_data)
                    ]

                    t0 = time.perf_counter()
                    self.db.save_document_chunks(records)
                    t_db += time.perf_counter() - t0
                    del records, embeddings
                    logger.info(f"Processed batch {batch_num}/{total_batches} for '{filename}'")
                    break
                except Exception as e:
                    # Check if the document was deleted by the user (foreign key violation)
                    if "23503" in str(e) or "foreign key" in str(e).lower():
                        raise DocumentDeletedError(f"Document {document_id} no longer exists.")

                    if attempt == max_retries - 1:
                        failed_batches += 1
                        logger.error(f"Failed batch {batch_num}/{total_batches} for '{filename}': {e}")
                    else:
                        logger.warning(f"Retrying batch {batch_num}/{total_batches} for '{filename}' (attempt {attempt + 1})")

            global_chunk_index += len(batch_data)

        t_total = time.perf_counter() - start_total
        avg_batch = total_chunks / max(1, total_batches)

        logger.info(
            f"INGESTION AUDIT [{filename}]: "
            f"Pages=N/A | Chunks={total_chunks} | EmbedBatches={total_batches} | AvgBatch={avg_batch:.1f} || "
            f"Time: Total={t_total:.2f}s | Extract={t_extract:.2f}s | Split={t_split:.2f}s | Embed={t_embed:.2f}s | DB={t_db:.2f}s"
        )

        if failed_batches > 0:
            logger.warning(f"Completed '{filename}' with {failed_batches}/{total_batches} failed batches")
            raise PartialIngestionError(f"Completed with {failed_batches}/{total_batches} failed batches")
        else:
            logger.info(f"Successfully ingested '{filename}' ({total_batches} batches)")

    def delete_document(self, document_id: str, box_id: str) -> bool:
        """Deletes a document and cascades to chunks."""
        success = self.db.delete_document(document_id=document_id, box_id=box_id)
        if success:
            self.lexical_store.invalidate_box(box_id)
        return success

    @staticmethod
    def _merge_small_pdf_chunks(chunk_docs_raw, source_text: str, min_chunk_size: int = 200):
        """Merge small PDF chunks without breaking their source offsets.

        Recursive chunks can overlap. Concatenating two overlapping chunk texts
        creates a string that never appeared in the source document, making
        exact page mapping impossible. Instead, use the original source span
        from the first chunk's start through the small chunk's end.
        """
        merged = []
        for chunk in chunk_docs_raw:
            if len(chunk.page_content) >= min_chunk_size or not merged:
                merged.append(chunk)
                continue

            previous = merged[-1]
            start = previous.metadata.get("start_index", 0)
            small_start = chunk.metadata.get("start_index", 0)
            end = small_start + len(chunk.page_content)

            if 0 <= start <= small_start <= end <= len(source_text):
                previous.page_content = source_text[start:end]
            else:
                # Keeping the small chunk is safer than inventing text when
                # the splitter cannot provide a valid source span.
                merged.append(chunk)
        return merged

    def list_files(self, box_id: str) -> List[str]:
        """Lists all unique filenames for a Box."""
        return self.db.get_all_documents(box_id=box_id)

    def _extract_text_from_disk(self, file_path: str, filename: str) -> str:
        """
        Extracts readable text from non-PDF files.

        Supports: DOCX, TXT, CSV, XLSX
        PDFs use the streaming method instead.
        """
        filename_lower = filename.lower()

        if filename_lower.endswith(".docx"):
            return self._extract_docx(file_path)

        elif filename_lower.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        elif filename_lower.endswith(".csv"):
            return self._extract_csv(file_path)

        elif filename_lower.endswith(".xlsx"):
            return self._extract_xlsx(file_path)

        else:
            raise ValueError(f"Unsupported file type: {filename}")

    def _extract_docx(self, file_path: str) -> str:
        """
        Extracts structured text from a DOCX file, preserving headings, paragraphs, and tables.
        """
        try:
            import docx
            from docx.oxml.table import CT_Tbl
            from docx.oxml.text.paragraph import CT_P
            from docx.table import Table
            from docx.text.paragraph import Paragraph

            doc_file = docx.Document(file_path)
            content = []

            for child in doc_file.element.body:
                if isinstance(child, CT_P):
                    paragraph = Paragraph(child, doc_file)
                    if paragraph.text.strip():
                        style_name = paragraph.style.name if paragraph.style else ""
                        if style_name.startswith("Heading"):
                            try:
                                level = int(style_name.split()[-1])
                                prefix = "#" * level
                                content.append(f"{prefix} {paragraph.text.strip()}")
                            except ValueError:
                                content.append(f"## {paragraph.text.strip()}")
                        else:
                            content.append(paragraph.text.strip())
                elif isinstance(child, CT_Tbl):
                    table = Table(child, doc_file)
                    content.append("[TABLE]")
                    for row in table.rows:
                        # Keep empty cells so we don't shift columns
                        row_text = " | ".join(cell.text.strip().replace("\n", " ") for cell in row.cells)
                        if row_text.strip(" |"):
                            content.append(row_text)

            return "\n\n".join(content)
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise

    def _extract_csv(self, file_path: str) -> str:
        """
        Converts CSV into readable text format.

        Each row becomes: "Column1: value1 | Column2: value2 | ..."
        This makes the data semantically searchable.
        """
        rows = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row_text = " | ".join(
                        f"{key}: {value}" for key, value in row.items()
                        if value and value.strip()
                    )
                    if row_text:
                        rows.append(row_text)
        except Exception as e:
            logger.warning(f"CSV DictReader failed, falling back to raw read: {e}")
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        return "\n".join(rows)

    def _extract_xlsx(self, file_path: str) -> str:
        """
        Extracts text from Excel files (XLSX).

        Reads all sheets, converting each row to "Col: val | Col: val" format.
        """
        try:
            from openpyxl import load_workbook
            wb = load_workbook(file_path, read_only=True, data_only=True)
            all_text = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                all_text.append(f"--- Sheet: {sheet_name} ---")

                # Iterate without casting to list to save memory
                rows_iter = ws.iter_rows(values_only=True)
                try:
                    first_row = next(rows_iter)
                except StopIteration:
                    continue

                # Use first row as headers
                headers = [str(h) if h else f"Col{i}" for i, h in enumerate(first_row)]

                for row in rows_iter:
                    row_text = " | ".join(
                        f"{headers[i]}: {str(cell)}"
                        for i, cell in enumerate(row)
                        if cell is not None and str(cell).strip()
                    )
                    if row_text:
                        all_text.append(row_text)

            wb.close()
            return "\n".join(all_text)

        except ImportError:
            logger.warning("openpyxl not installed, cannot process XLSX files")
            raise ValueError("XLSX support requires openpyxl: pip install openpyxl")
        except Exception as e:
            logger.error(f"XLSX extraction failed: {e}")
            raise

    # ── New: Accuracy Enhancement Helpers ──

    def _detect_file_type(self, filename: str) -> str:
        """Returns a human-readable file type label for contextual headers."""
        ext = os.path.splitext(filename)[1].lower()
        type_map = {
            ".pdf": "PDF", ".docx": "Word Document", ".txt": "Text File",
            ".csv": "CSV Spreadsheet", ".xlsx": "Excel Spreadsheet",
        }
        return type_map.get(ext, "Document")


