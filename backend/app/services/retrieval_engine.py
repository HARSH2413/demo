from typing import Optional, List, Dict, Any
from app.interfaces.vector_store import IVectorStore
from app.interfaces.lexical_store import ILexicalStore
from app.interfaces.embedder import IEmbedder
from app.interfaces.reranker import IReranker
from app.core.logger import logger
from app.core.cache import global_query_cache

class RetrievalEngine:
    def __init__(
        self,
        db: IVectorStore,
        lexical_store: ILexicalStore,
        embedder: IEmbedder,
        reranker: IReranker,
        retrieval_top_k: int = 20,
        reranker_top_k: int = 5,
    ):
        self.db = db
        self.lexical_store = lexical_store
        self.embedder = embedder
        self.reranker = reranker
        self.retrieval_top_k = retrieval_top_k
        self.reranker_top_k = reranker_top_k
        self.cache = global_query_cache
        self.rrf_k = 60

    def retrieve_documents(self, search_query: str, box_id: str) -> List[Dict[str, Any]]:
        """Runs a single query dense + lexical search, merges with RRF, and reranks."""
        cached = self.cache.get_query_result(search_query, box_id)
        if cached is not None:
            logger.info("Cache hit for query results")
            return cached

        docs = self._hybrid_search(search_query, box_id, self.retrieval_top_k)
        
        if docs and self.reranker:
            try:
                docs = self.reranker.rerank(query=search_query, documents=docs, top_k=self.reranker_top_k)
                
                from app.core.config import settings
                if settings.ENABLE_RERANK_DEBUG_LOGGING:
                    logger.info(f"[RERANK DEBUG] Query: '{search_query}'")
                    for i, d in enumerate(docs):
                        logger.info(f"  [{i}] Score: {d.get('rerank_score', 0):.4f} | Chunk: {d.get('content', '')[:60]}...")
            except Exception as e:
                logger.warning(f"Re-ranking failed: {e}")
                docs = docs[:self.reranker_top_k]

        self.cache.set_query_result(search_query, box_id, docs)
        return docs

    def retrieve_documents_multi(self, queries: List[str], box_id: str, reranker_query: str) -> List[Dict[str, Any]]:
        """Runs multiple queries (for rescue pass), merges all with global RRF, and reranks using reranker_query."""
        self.lexical_store.ensure_box_index(box_id, self.db)
        
        all_dense = {}
        for q in queries:
            try:
                query_vector = self.embedder.embed_text([q])[0]
                dense_results = self.db.search_dense(query_vector=query_vector, box_id=box_id, limit=self.retrieval_top_k)
                for d in dense_results:
                    key = (d.get("document_id"), d.get("chunk_index"))
                    # Deduplicate: keep the highest dense score across queries
                    if key not in all_dense or d.get("embedding_score", 0.0) > all_dense[key].get("embedding_score", 0.0):
                        all_dense[key] = d
            except Exception as e:
                logger.error(f"Multi dense search failed for query '{q}': {e}")
                
        all_lexical = {}
        for q in queries:
            try:
                lexical_query = self._expand_lexical_variants(q)
                lexical_results = self.lexical_store.search(query=lexical_query, box_id=box_id, limit=self.retrieval_top_k)
                for d in lexical_results:
                    key = (d.get("document_id"), d.get("chunk_index"))
                    # Deduplicate: keep the highest lexical score across queries
                    if key not in all_lexical or d.get("lexical_score", 0.0) > all_lexical[key].get("lexical_score", 0.0):
                        all_lexical[key] = d
            except Exception as e:
                logger.error(f"Multi lexical search failed for query '{q}': {e}")
                
        # Sort globally by their respective raw scores before RRF
        global_dense_sorted = sorted(all_dense.values(), key=lambda x: x.get("embedding_score", 0.0), reverse=True)
        global_lexical_sorted = sorted(all_lexical.values(), key=lambda x: x.get("lexical_score", 0.0), reverse=True)
        
        merged_list = self._rrf_merge(global_dense_sorted, global_lexical_sorted, self.retrieval_top_k)
        
        if merged_list and self.reranker:
            try:
                merged_list = self.reranker.rerank(query=reranker_query, documents=merged_list, top_k=self.reranker_top_k)
                
                from app.core.config import settings
                if settings.ENABLE_RERANK_DEBUG_LOGGING:
                    logger.info(f"[RERANK DEBUG MULTI] Reranker Query: '{reranker_query}'")
                    for i, d in enumerate(merged_list):
                        logger.info(f"  [{i}] Score: {d.get('rerank_score', 0):.4f} | Chunk: {d.get('content', '')[:60]}...")
            except Exception as e:
                logger.warning(f"Re-ranking failed in multi: {e}")
                merged_list = merged_list[:self.reranker_top_k]
                
        return merged_list

    def _hybrid_search(self, query: str, box_id: str, limit: int) -> List[Dict[str, Any]]:
        self.lexical_store.ensure_box_index(box_id, self.db)
        
        dense_results = []
        try:
            query_vector = self.embedder.embed_text([query])[0]
            dense_results = self.db.search_dense(query_vector=query_vector, box_id=box_id, limit=limit)
        except Exception as e:
            logger.error(f"Dense search failed: {e}")
            
        lexical_results = []
        try:
            lexical_query = self._expand_lexical_variants(query)
            lexical_results = self.lexical_store.search(query=lexical_query, box_id=box_id, limit=limit)
        except Exception as e:
            logger.error(f"Lexical search failed: {e}")
            
        return self._rrf_merge(dense_results, lexical_results, limit)

    def _rrf_merge(self, dense: List[Dict], lexical: List[Dict], limit: int) -> List[Dict]:
        scores = {}
        docs = {}
        
        # We need a stable tiebreaker, because ranks shouldn't be arbitrary if scores are identical.
        # But python's stable sort is enough if we just enumerate after sorting.
        
        for rank, doc in enumerate(dense):
            key = (doc.get("document_id"), doc.get("chunk_index"))
            scores[key] = scores.get(key, 0.0) + 1.0 / (self.rrf_k + rank + 1)
            docs[key] = doc
            
        for rank, doc in enumerate(lexical):
            key = (doc.get("document_id"), doc.get("chunk_index"))
            scores[key] = scores.get(key, 0.0) + 1.0 / (self.rrf_k + rank + 1)
            if key not in docs:
                docs[key] = doc
                docs[key]["embedding_score"] = 0.0
            else:
                docs[key]["lexical_score"] = doc.get("lexical_score", 0.0)
                
        for key in docs:
            docs[key]["rrf_score"] = scores[key]
            
        # Tie-breaker for deterministic tests: sort by score desc, then by document_id asc, chunk_index asc
        sorted_docs = sorted(docs.values(), key=lambda x: (
            x["rrf_score"],
            x.get("embedding_score", 0.0),
            -ord(x.get("document_id", "z")[0]),
            -x.get("chunk_index", 0)
        ), reverse=True)
        
        return sorted_docs[:limit]

    def _expand_lexical_variants(self, text: str) -> str:
        from app.core.config import settings
        variants_map = getattr(settings, "LEXICAL_VARIANTS_MAP", {
            "gst": "Goods and Services Tax",
            "pf": "Provident Fund EPF",
            "epf": "Provident Fund PF",
            "pto": "Paid Time Off",
            "hr": "Human Resources",
            "nda": "Non-Disclosure Agreement",
            "kpi": "Key Performance Indicator",
            "roi": "Return on Investment",
        })
        words = text.split()
        expanded_words = []
        for word in words:
            clean_word = word.lower().strip(",.?!()[]{}\"'")
            expanded_words.append(word)
            if clean_word in variants_map:
                expanded_words.append(variants_map[clean_word])
        
        return " ".join(expanded_words)
