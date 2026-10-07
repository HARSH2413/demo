import os
import json
import threading
import shutil
from typing import List, Dict, Any, Optional
import bm25s
from app.interfaces.lexical_store import ILexicalStore
from app.core.logger import logger

class BM25SAdapter(ILexicalStore):
    def __init__(self, data_dir: str = ".data/bm25"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.indexes: Dict[str, bm25s.BM25] = {}
        self.metadata_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.locks: Dict[str, threading.Lock] = {}
        self.global_lock = threading.Lock()
        logger.info(f"BM25SAdapter initialized with data_dir={data_dir}")

    def _get_box_lock(self, box_id: str) -> threading.Lock:
        with self.global_lock:
            if box_id not in self.locks:
                self.locks[box_id] = threading.Lock()
            return self.locks[box_id]

    def _box_dir(self, box_id: str) -> str:
        return os.path.join(self.data_dir, box_id)

    def search(self, query: str, box_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_box_lock(box_id):
            if box_id not in self.indexes:
                # If index is not in memory, we assume it wasn't built or loaded.
                return []

            index = self.indexes[box_id]
            metadata = self.metadata_cache.get(box_id, [])

            if not metadata:
                return []

            # Tokenize query
            tokenized_query = bm25s.tokenize(query)
            
            # Search
            actual_limit = min(limit, len(metadata))
            if actual_limit == 0:
                return []
                
            results, scores = index.retrieve(tokenized_query, k=actual_limit)
            
            output = []
            if len(results) > 0:
                for i in range(len(results[0])):
                    doc_idx = int(results[0][i])
                    score = float(scores[0][i])
                    if score > 0.0:
                        doc_meta = dict(metadata[doc_idx])
                        doc_meta["lexical_score"] = score
                        output.append(doc_meta)
            
            return output

    def ensure_box_index(self, box_id: str, db_adapter) -> None:
        with self._get_box_lock(box_id):
            if box_id in self.indexes:
                return
                
            box_dir = self._box_dir(box_id)
            meta_path = os.path.join(box_dir, "metadata.json")
            
            # Try to load existing index
            if os.path.exists(box_dir) and os.path.exists(meta_path):
                try:
                    self.indexes[box_id] = bm25s.BM25.load(box_dir, load_corpus=False)
                    with open(meta_path, "r", encoding="utf-8") as f:
                        self.metadata_cache[box_id] = json.load(f)
                    logger.info(f"Loaded existing BM25 index for box={box_id}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load existing BM25 index for box={box_id}, rebuilding... Error: {e}")
                    self._delete_box_files(box_id)
                    
            # Need to build
            logger.info(f"Building BM25 index for box={box_id}")
            self._build_index(box_id, db_adapter)

    def _build_index(self, box_id: str, db_adapter) -> None:
        response = db_adapter.client.table("document_chunks") \
            .select("id, document_id, chunk_index, content, page_start, page_end, section_title, metadata, documents!inner(box_id, status, filename)") \
            .eq("documents.box_id", box_id) \
            .eq("documents.status", "completed") \
            .execute()
            
        data = response.data
        if not data:
            logger.info(f"No completed chunks found for box={box_id}")
            self.indexes[box_id] = bm25s.BM25(k1=1.2, b=0.75)
            self.metadata_cache[box_id] = []
            return

        corpus_texts = []
        metadata_list = []
        
        for row in data:
            doc_info = row.get("documents", {})
            filename = doc_info.get("filename", "") if isinstance(doc_info, dict) else ""
            
            section = row.get("section_title") or ""
            content = row.get("content") or ""
            
            text = f"{section} {content}".strip()
            corpus_texts.append(text)
            
            metadata_list.append({
                "id": row.get("id"),
                "document_id": row.get("document_id"),
                "chunk_index": row.get("chunk_index"),
                "filename": filename,
                "page_start": row.get("page_start"),
                "page_end": row.get("page_end"),
                "section_title": row.get("section_title"),
                "content": content,
                "metadata": row.get("metadata", {})
            })

        corpus_tokens = bm25s.tokenize(corpus_texts)
        
        index = bm25s.BM25(k1=1.2, b=0.75)
        index.index(corpus_tokens)
        
        box_dir = self._box_dir(box_id)
        os.makedirs(box_dir, exist_ok=True)
        index.save(box_dir)
        
        with open(os.path.join(box_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata_list, f)
            
        self.indexes[box_id] = index
        self.metadata_cache[box_id] = metadata_list
        logger.info(f"Built BM25 index for box={box_id} with {len(metadata_list)} chunks")

    def invalidate_box(self, box_id: str) -> None:
        with self._get_box_lock(box_id):
            if box_id in self.indexes:
                del self.indexes[box_id]
            if box_id in self.metadata_cache:
                del self.metadata_cache[box_id]
            self._delete_box_files(box_id)
            logger.info(f"Invalidated BM25 index for box={box_id}")

    def _delete_box_files(self, box_id: str) -> None:
        box_dir = self._box_dir(box_id)
        if os.path.exists(box_dir):
            shutil.rmtree(box_dir, ignore_errors=True)
