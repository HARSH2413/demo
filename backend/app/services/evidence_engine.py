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
        if "rerank_score" in doc and doc.get("rerank_score") is not None:
            return float(doc.get("rerank_score", 0.0))
        if "rrf_score" in doc and doc.get("rrf_score") is not None:
            return float(doc.get("rrf_score", 0.0))
        if "embedding_score" in doc and doc.get("embedding_score") is not None:
            return float(doc.get("embedding_score", 0.0))
        return float(doc.get("embedding_score", 0.0))

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
        seen_filenames = set()
        
        requests = []
        doc_indices_to_expand = []
        
        for idx, doc in enumerate(docs):
            filename = doc.get("filename", "")
            
            if filename in seen_filenames or not filename:
                continue
                
            document_id = doc.get("document_id")
            chunk_index = doc.get("chunk_index")
            
            if document_id is not None and chunk_index is not None:
                seen_filenames.add(filename)
                requests.append({"document_id": document_id, "chunk_index": chunk_index})
                doc_indices_to_expand.append(idx)
                
        bulk_neighbors = {}
        if requests:
            try:
                bulk_neighbors = self.db.get_multi_neighboring_chunks(requests, limit=5)
            except Exception as e:
                logger.warning(f"Bulk neighbor expansion failed: {e}")
                
        seen_filenames.clear()
        for doc in docs:
            filename = doc.get("filename", "")
            document_id = doc.get("document_id")
            
            if filename in seen_filenames or not filename or document_id not in bulk_neighbors:
                expanded.append(doc)
                if filename:
                    seen_filenames.add(filename)
                continue
                
            seen_filenames.add(filename)
            neighbors = bulk_neighbors.get(document_id, [])
            
            if neighbors and len(neighbors) > 1:
                neighbor_texts = []
                for n in neighbors:
                    n_content = n.get("content", "")
                    if n_content and n_content[:100] != doc.get("content", "")[:100]:
                        neighbor_texts.append(n_content)

                if neighbor_texts:
                    enriched_doc = {**doc, "has_neighbor_context": True, "neighbor_context": "\n---\n".join(neighbor_texts[:2])}
                    expanded.append(enriched_doc)
                    logger.debug(f"Expanded '{filename}' with {len(neighbor_texts[:2])} neighbor chunks")
                    continue
                    
            expanded.append(doc)

        return expanded

    def determine_confidence(self, docs: list[dict]) -> str:
        if not docs:
            return "low"

        scores = [self.get_doc_relevance_score(doc) for doc in docs]
        top_score = max(scores)
        unique_files = set(doc.get("filename", "") for doc in docs)

        if len(unique_files) >= 3 and top_score >= 0.5:
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
        """Assigns deterministic evidence IDs [E1], [E2] to the filtered documents."""
        for i, doc in enumerate(docs):
            doc["evidence_id"] = f"[E{i+1}]"
        return docs

    def build_context_text(self, docs: list[dict]) -> str:
        context_parts = []
        for doc in docs:
            score_label = ""
            if "rerank_score" in doc:
                score_label = f" [relevance: {doc['rerank_score']:.2f}]"
            neighbor_label = " [+ neighboring context]" if doc.get("has_neighbor_context") else ""
            
            evidence_id = doc.get("evidence_id", "[E?]")
            
            meta = doc.get("metadata") or {}
            context_header = meta.get("context_header", f"[Document: {doc.get('filename')}]")
            
            neighbor_context_text = ""
            if doc.get("has_neighbor_context") and doc.get("neighbor_context"):
                neighbor_context_text = f"\n[SURROUNDING CONTEXT FROM SAME DOCUMENT]\n{doc['neighbor_context']}\n"
            
            context_parts.append(
                f"--- EVIDENCE {evidence_id} ---\n"
                f"Source: {doc.get('filename')}{score_label}{neighbor_label}\n"
                f"Context: {context_header}\n"
                f"Content: {doc.get('content')}{neighbor_context_text}\n"
                f"----------------------"
            )
        return "\n\n".join(context_parts)
