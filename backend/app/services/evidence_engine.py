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

        return filtered

    def _expand_with_neighbors(self, docs: list) -> list:
        expanded = []
        retrieved_set = {(doc.get("document_id"), doc.get("chunk_index")) for doc in docs}
        
        requests = []
        for doc in docs:
            doc_id = doc.get("document_id")
            c_idx = doc.get("chunk_index")
            if doc_id is not None and c_idx is not None:
                requests.append({"document_id": doc_id, "chunk_index": c_idx})
                
        bulk_neighbors = {}
        if requests:
            try:
                # Fetch 3 chunks (prev, curr, next)
                bulk_neighbors = self.db.get_multi_neighboring_chunks(requests, limit=3)
            except Exception as e:
                logger.warning(f"Bulk neighbor expansion failed: {e}")
                
        neighbor_map = {}
        for doc_id, n_list in bulk_neighbors.items():
            for n in n_list:
                neighbor_map[(doc_id, n.get("chunk_index"))] = n.get("content", "")
                
        for doc in docs:
            doc_id = doc.get("document_id")
            c_idx = doc.get("chunk_index")
            
            if doc_id is None or c_idx is None:
                expanded.append(doc)
                continue
                
            neighbor_texts = []
            
            # Look for previous chunk
            prev_idx = c_idx - 1
            if (doc_id, prev_idx) not in retrieved_set and (doc_id, prev_idx) in neighbor_map:
                neighbor_texts.append(neighbor_map[(doc_id, prev_idx)])
                
            # Look for next chunk
            next_idx = c_idx + 1
            if (doc_id, next_idx) not in retrieved_set and (doc_id, next_idx) in neighbor_map:
                neighbor_texts.append(neighbor_map[(doc_id, next_idx)])
                
            if neighbor_texts:
                enriched_doc = {**doc, "has_neighbor_context": True, "neighbor_context": "\n---\n".join(neighbor_texts)}
                expanded.append(enriched_doc)
            else:
                expanded.append(doc)

        return expanded

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
        """Assigns deterministic evidence IDs [E1], [E2] grouped by document."""
        doc_id_to_evidence = {}
        evidence_counter = 1
        
        for doc in docs:
            doc_id = doc.get("document_id")
            if not doc_id:
                doc["evidence_id"] = f"[E{evidence_counter}]"
                evidence_counter += 1
                continue
                
            if doc_id not in doc_id_to_evidence:
                doc_id_to_evidence[doc_id] = f"[E{evidence_counter}]"
                evidence_counter += 1
                
            doc["evidence_id"] = doc_id_to_evidence[doc_id]
            
        return docs

    def build_context_text(self, docs: list[dict]) -> str:
        from collections import defaultdict
        groups = defaultdict(list)
        for doc in docs:
            groups[doc.get("evidence_id", "[E?]")].append(doc)
            
        context_parts = []
        for evidence_id, group_docs in groups.items():
            group_docs.sort(key=lambda x: x.get("chunk_index", 0))
            first_doc = group_docs[0]
            filename = first_doc.get("filename", "")
            
            max_score = max((self.get_doc_relevance_score(d) for d in group_docs), default=0.0)
            score_label = f" [relevance: {max_score:.2f}]" if max_score > 0 else ""
            
            chunk_texts = []
            for doc in group_docs:
                meta = doc.get("metadata") or {}
                ctx_head = doc.get("section_title") or meta.get("context_header", "")
                
                text = doc.get("content", "")
                if doc.get("has_neighbor_context") and doc.get("neighbor_context"):
                    text = f"{text}\n\n[SURROUNDING CONTEXT FROM SAME DOCUMENT]\n{doc['neighbor_context']}"
                    
                if ctx_head:
                    chunk_texts.append(f"({ctx_head})\n{text}")
                else:
                    chunk_texts.append(text)
                    
            combined_content = "\n\n...\n\n".join(chunk_texts)
            
            context_parts.append(
                f"--- EVIDENCE {evidence_id} ---\n"
                f"Source: {filename}{score_label}\n"
                f"Content:\n{combined_content}\n"
                f"----------------------"
            )
        return "\n\n".join(context_parts)
