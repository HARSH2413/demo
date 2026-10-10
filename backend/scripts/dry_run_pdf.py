import sys
import logging
import fitz
import re
import time
import psutil
import os
from collections import Counter
from app.utils.pdf_parser import sort_blocks_column_aware
from app.services.ingestion_service import IngestionService
from langchain_text_splitters import RecursiveCharacterTextSplitter

sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    # Fold case
    text = text.lower()
    # Strip glyphs like ■, ○, etc.
    text = re.sub(r'[\u25a0-\u25ff\u2022\u202d\u202c]', '', text)
    # Collapse whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    # Also collapse newlines to space for strict substring search
    text = re.sub(r'\n+', ' ', text)
    return text.strip()

def dry_run_pdf(pdf_path: str):
    start_time = time.time()
    process = psutil.Process(os.getpid())
    print(f"--- DRY RUN: {pdf_path} ---")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=300,
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "],
        add_start_index=True
    )
    
    with fitz.open(pdf_path) as doc:
        total_pages = doc.page_count
        batch_text = ""
        page_offsets = []
        page_to_section = {}
        current_section = ""
        
        zero_text_pages = []
        gutter_pages = []
        rotated_pages = []
        sorted_page_texts = {} # Store for verification
        
        # 1. Extraction and Ordering
        extract_start = time.time()
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            blocks = page.get_text("blocks")
            
            if not blocks:
                zero_text_pages.append(page_num + 1)
                
            if page.rotation != 0:
                rotated_pages.append(page_num + 1)
            
            sorted_blocks = sort_blocks_column_aware(blocks, page_rotation=page.rotation)
            
            left_count = sum(1 for b in sorted_blocks if b[0] < 290)
            right_count = sum(1 for b in sorted_blocks if b[0] > 310)
            if left_count > 0 and right_count > 0:
                gutter_pages.append(page_num + 1)
                
            page_text = "\n".join(b[4] for b in sorted_blocks if len(b) >= 7 and b[6] == 0)
            page_text = re.sub(r'[ \t]+', ' ', page_text)
            
            sorted_page_texts[page_num + 1] = page_text
            
            # Simple section extraction
            for line in page_text.split('\n'):
                line = line.strip()
                if line.startswith('## '):
                    current_section = line[3:]
                    break
            page_to_section[page_num + 1] = current_section
            
            start_idx = len(batch_text)
            if batch_text and page_text:
                batch_text += " "
                start_idx += 1
            batch_text += page_text
            end_idx = start_idx + len(page_text)
            page_offsets.append((start_idx, end_idx, page_num + 1))
            
        extract_end = time.time()
            
        print("\n--- CHUNKING & VERIFICATION ---")
        split_start = time.time()
        chunk_docs_raw = text_splitter.create_documents([batch_text])
        
        # Merge chunks smaller than 200 chars
        MIN_CHUNK_SIZE = 200
        chunk_docs = []
        for d in chunk_docs_raw:
            if len(d.page_content) < MIN_CHUNK_SIZE and chunk_docs:
                chunk_docs[-1].page_content += " " + d.page_content
            else:
                chunk_docs.append(d)
                
        split_end = time.time()
        
        fallbacks_fired = 0
        mismatches = 0
        sampled_mismatches = []
        sizes = []
        
        for i, chunk in enumerate(chunk_docs):
            c_text = chunk.page_content
            sizes.append(len(c_text))
            
            # Since we merged chunks, start_index metadata might be slightly off for merged blocks,
            # but we use the first chunk's start_index, so it's fine.
            c_start = chunk.metadata.get("start_index", 0)
            # Recompute c_start robustly in case of merged chunks
            actual_start = batch_text.find(c_text[:50], max(0, c_start - 500))
            if actual_start != -1:
                c_start = actual_start
            c_end = c_start + len(c_text)
            
            # Map using page_offsets
            page_start = None
            page_end = None
            for (p_s, p_e, p_num) in page_offsets:
                if p_s <= c_start < p_e:
                    page_start = p_num
                if p_s < c_end <= p_e:
                    page_end = p_num
                    break
                    
            if not page_start: page_start = 1
            if not page_end: page_end = total_pages
            
            # Log fallbacks (mocking the IngestionService logic)
            actual_text = batch_text[c_start:c_end]
            if actual_text != c_text:
                fallbacks_fired += 1
                
            section = page_to_section.get(page_start, "")
            
            # Verification using normalized column-sorted text
            norm_chunk = normalize_text(c_text)
            first_60 = norm_chunk[:60]
            last_60 = norm_chunk[-60:] if len(norm_chunk) >= 60 else norm_chunk
            
            found_start = False
            found_end = False
            
            for p in range(page_start - 1, page_end):
                p_text = sorted_page_texts.get(p + 1, "")
                norm_page = normalize_text(p_text)
                
                if first_60 in norm_page:
                    found_start = True
                if last_60 in norm_page:
                    found_end = True
                    
            if not found_start or not found_end:
                mismatches += 1
                if len(sampled_mismatches) < 5:
                    sampled_mismatches.append((i+1, page_start, page_end, first_60, norm_chunk))
                
        print(f"\n--- GST & 18% SEARCH ---")
        gst_hits = 0
        rate_hits = 0
        norm_batch = normalize_text(batch_text)
        for p in range(total_pages):
            p_text = sorted_page_texts.get(p + 1, "")
            n_text = normalize_text(p_text)
            gst_hits += n_text.count(" gst ")
            rate_hits += n_text.count("18%")
        print(f"' gst ' hits: {gst_hits}")
        print(f"'18%' hits: {rate_hits}")
        
        print(f"\n--- SUMMARY ---")
        print(f"Total Pages: {total_pages}")
        print(f"Zero Text Pages: {len(zero_text_pages)} {zero_text_pages}")
        print(f"Rotated Pages: {len(rotated_pages)} {rotated_pages}")
        print(f"Gutter Detected Pages: {len(gutter_pages)}")
        
        print(f"\nTotal Chunks: {len(chunk_docs)}")
        print(f"Offset Fallbacks Fired: {fallbacks_fired}")
        print(f"Independent Verification Mismatches: {mismatches}")
        
        print("\nSize Histogram:")
        for k, v in sorted(Counter([s // 200 * 200 for s in sizes]).items()):
            print(f"  {k}-{k+199} chars: {v} chunks")
            
        if sampled_mismatches:
            print("\nSampled Mismatches:")
            for m in sampled_mismatches:
                print(f"Chunk {m[0]} (Pages {m[1]}-{m[2]}):")
                print(f"  First 60 (norm): '{m[3]}'")
                # Find closest match in page
                p_text = sorted_page_texts.get(m[1], "")
                n_text = normalize_text(p_text)
                idx = n_text.find(m[3][:30])
                if idx != -1:
                    print(f"  Closest page text: '{n_text[idx:idx+80]}...'")
                else:
                    print("  No close match found on starting page.")
        
        total_time = time.time() - start_time
        peak_mem = process.memory_info().rss / 1024 / 1024
        print(f"\nPerformance:")
        print(f"  Extraction time: {extract_end - extract_start:.2f}s")
        print(f"  Split time: {split_end - split_start:.2f}s")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Peak memory: {peak_mem:.2f} MB")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dry_run_pdf.py <pdf_path>")
        sys.exit(1)
    dry_run_pdf(sys.argv[1])
