from app.interfaces.vector_store import IVectorStore
from app.core.logger import logger
from app.core.config import settings

class EvidenceEngine:
    def __init__(
        self,
        db: IVectorStore,
        min_relevance_score: float = 0.3,
        min_relevance_score_low: float = 0.1,
        enable_neighbor_context: bool = True,
    ):
        self.db = db
        self.min_relevance_score = min_relevance_score
        self.min_relevance_score_low = min_relevance_score_low
        self.enable_neighbor_context = enable_neighbor_context

    def get_doc_relevance_score(self, doc: dict) -> float:
        # Strict hierarchy: if reranker is used, that is the single source of truth for thresholding
        if "rerank_score" in doc and doc.get("rerank_score") is not None:
            return float(doc.get("rerank_score"))
        
        # If no reranker is available, fallback to semantic embedding score.
        # DO NOT use rrf_score as a thresholdable metric because it is rank-based (e.g. 1/60), not a similarity distance.
        if "embedding_score" in doc and doc.get("embedding_score") is not None:
            return float(doc.get("embedding_score"))
            
        return 0.0

    def filter_and_expand(self, docs: list[dict]) -> list[dict]:
        filtered = self._dynamic_relevance_filter(docs)
        if self.enable_neighbor_context and filtered:
            filtered = self._expand_with_neighbors(filtered)
        return filtered

    def _dynamic_relevance_filter(self, docs: list) -> list:
        if not docs:
            return docs

        filtered = [
            doc for doc in docs
            if self.get_doc_relevance_score(doc) >= self.min_relevance_score
        ]

        if len(filtered) < 2:
            filtered = [
                doc for doc in docs
                if self.get_doc_relevance_score(doc) >= self.min_relevance_score_low
            ]
            if len(filtered) > len(docs):
                filtered = docs
            logger.info(
                f"Dynamic threshold: {self.min_relevance_score} → {self.min_relevance_score_low} "
                f"({len(docs)} → {len(filtered)} docs)"
            )
        else:
            filtered_count = len(docs) - len(filtered)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} low-relevance docs (threshold={self.min_relevance_score})")
                
        if settings.ENABLE_RERANK_DEBUG_LOGGING:
            dropped = [doc for doc in docs if doc not in filtered]
            for i, d in enumerate(dropped):
                logger.info(f"[RERANK DEBUG] Dropped Chunk [{i}] Score: {self.get_doc_relevance_score(d):.4f} | Content: {d.get('content', '')[:60]}...")

        return filtered

    def _expand_with_neighbors(self, docs: list) -> list:
        # Config caps
        MAX_EXPAND_DOCS = getattr(settings, "MAX_EXPAND_DOCS", 5)
        MAX_NEIGHBOR_CHARS = getattr(settings, "MAX_NEIGHBOR_CHARS", 1500)
        
        # Only expand top N docs to save tokens and time
        docs_to_expand = sorted(docs, key=lambda d: self.get_doc_relevance_score(d), reverse=True)[:MAX_EXPAND_DOCS]
        expand_set = {(d.get("document_id"), d.get("chunk_index")) for d in docs_to_expand}
        
        # Collect all surviving docs in a map for easy merging
        doc_map = {}
        requested_parent_ids = {}
        for d in docs:
            did = d.get("document_id")
            idx = d.get("chunk_index")
            if did and idx is not None:
                doc_map[(did, idx)] = d
                parent_id = (d.get("metadata") or {}).get("parent_id")
                if parent_id:
                    requested_parent_ids.setdefault(did, set()).add(parent_id)
                
        requests = []
        for did, idx in expand_set:
            requests.append({"document_id": did, "chunk_index": idx})
                
        bulk_neighbors = {}
        if requests:
            try:
                bulk_neighbors = self.db.get_multi_neighboring_chunks(requests, limit=3)
            except Exception as e:
                logger.warning(f"Bulk neighbor expansion failed: {e}")
                
        neighbor_map = {}
        for doc_id, n_list in bulk_neighbors.items():
            for n in n_list:
                neighbor_map[(doc_id, n.get("chunk_index"))] = n
                
        # We now want to merge contiguous chunks into single blocks.
        # First, union all chunks (surviving + neighbors)
        all_chunks = {}
        for (did, idx), d in doc_map.items():
            all_chunks[(did, idx)] = d
            
        for (did, idx), n in neighbor_map.items():
            if (did, idx) not in all_chunks:
                # Hierarchical chunks must only expand into siblings from the
                # same logical parent.  Legacy chunks without parent metadata
                # retain the prior adjacency-only behaviour.
                allowed_parent_ids = requested_parent_ids.get(did)
                neighbor_parent_id = (n.get("metadata") or {}).get("parent_id")
                if allowed_parent_ids and neighbor_parent_id not in allowed_parent_ids:
                    continue
                # Limit neighbor chars
                content = n.get("content", "")
                if len(content) > MAX_NEIGHBOR_CHARS:
                    content = content[:MAX_NEIGHBOR_CHARS] + "..."
                n["content"] = content
                all_chunks[(did, idx)] = n
                
        # Group by document_id
        from collections import defaultdict
        groups = defaultdict(list)
        for (did, idx), chunk in all_chunks.items():
            groups[did].append(chunk)
            
        merged_docs = []
        for did, group in groups.items():
            # Sort by chunk_index
            group.sort(key=lambda x: x.get("chunk_index", 0))
            
            # Merge contiguous
            current_merged = None
            for chunk in group:
                if not current_merged:
                    current_merged = dict(chunk) # copy
                else:
                    # Check if contiguous
                    current_parent = (current_merged.get("metadata") or {}).get("parent_id")
                    chunk_parent = (chunk.get("metadata") or {}).get("parent_id")
                    same_parent = not current_parent or not chunk_parent or current_parent == chunk_parent
                    if same_parent and chunk.get("chunk_index") == current_merged.get("chunk_index") + 1:
                        current_merged["content"] += "\n\n" + chunk.get("content", "")
                        current_merged["chunk_index"] = chunk.get("chunk_index") # update to last
                        # Preserve highest relevance score if merging
                        s1 = self.get_doc_relevance_score(current_merged)
                        s2 = self.get_doc_relevance_score(chunk)
                        if s2 > s1:
                            if "rerank_score" in chunk: current_merged["rerank_score"] = chunk["rerank_score"]
                            if "embedding_score" in chunk: current_merged["embedding_score"] = chunk["embedding_score"]
                    else:
                        merged_docs.append(current_merged)
                        current_merged = dict(chunk)
            if current_merged:
                merged_docs.append(current_merged)
                
        # Add back docs that don't have document_id or chunk_index
        for d in docs:
            if not d.get("document_id") or d.get("chunk_index") is None:
                merged_docs.append(d)
                
        return merged_docs

    def determine_confidence(self, docs: list[dict]) -> str:
        if not docs:
            return "low"

        scores = [self.get_doc_relevance_score(doc) for doc in docs]
        top_score = max(scores)
        
        # Calculate source diversity using document_id, not filename
        unique_docs = set(doc.get("document_id") for doc in docs if doc.get("document_id"))

        if len(unique_docs) >= 3 and top_score >= 0.5:
            score_spread = max(scores) - min(scores)
            if score_spread > 0.3:
                return "multi_source"

        if top_score >= 0.7:
            return "high"
        elif top_score >= 0.3:
            return "medium"
        else:
            return "low"

    def should_run_accuracy_rescue(self, confidence_level: str, docs: list[dict]) -> bool:
        if not docs:
            return True

        top_score = max((self.get_doc_relevance_score(doc) for doc in docs), default=0.0)

        if top_score < max(0.12, self.min_relevance_score_low):
            return True

        if len(docs) == 1 and top_score < max(0.25, self.min_relevance_score):
            return True

        if confidence_level == "low" and top_score < 0.25 and len(docs) < 2:
            return True

        return False

    def assign_evidence_ids(self, docs: list[dict]) -> list[dict]:
        """Assigns deterministic unique evidence IDs [E1], [E2], ... per retrieved chunk."""
        for idx, doc in enumerate(docs, 1):
            doc["evidence_id"] = f"[E{idx}]"
        return docs

    def build_context_text(self, docs: list[dict]) -> str:
        """Formats retrieved chunks into clear, distinct evidence blocks."""
        context_parts = []
        for doc in docs:
            evidence_id = doc.get("evidence_id", "[E?]")
            filename = doc.get("filename", "Document")
            
            # Format page numbers
            page_start = doc.get("page_start")
            page_end = doc.get("page_end")
            page_str = ""
            if page_start is not None:
                if page_end is not None and page_end != page_start:
                    page_str = f" | Pages {page_start}-{page_end}"
                else:
                    page_str = f" | Page {page_start}"
                    
            section_title = doc.get("section_title") or ""
            section_str = f" | Section: {section_title}" if section_title else ""
            
            relevance = self.get_doc_relevance_score(doc)
            score_label = f" [relevance: {relevance:.2f}]" if relevance > 0 else ""
            
            content = doc.get("content", "").strip()
            
            context_parts.append(
                f"--- EVIDENCE {evidence_id} ---\n"
                f"Source: {filename}{page_str}{section_str}{score_label}\n"
                f"Content:\n{content}\n"
                f"----------------------"
            )
        return "\n\n".join(context_parts)
