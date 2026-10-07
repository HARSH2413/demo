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
        # Fast path cache
        cached = self.cache.get_query_result(search_query, box_id)
        if cached is not None:
            logger.info("Cache hit for query results")
            return cached

        docs = self._hybrid_search(search_query, box_id, self.retrieval_top_k)
        
        if docs and self.reranker:
            try:
                docs = self.reranker.rerank(query=search_query, documents=docs, top_k=self.reranker_top_k)
            except Exception as e:
                logger.warning(f"Re-ranking failed: {e}")
                docs = docs[:self.reranker_top_k]

        self.cache.set_query_result(search_query, box_id, docs)
        return docs

    def retrieve_documents_multi(self, queries: List[str], box_id: str, reranker_query: str) -> List[Dict[str, Any]]:
        """Runs multiple queries (for rescue pass), merges all with RRF, and reranks using reranker_query."""
        all_merged = {}
        
        for q in queries:
            docs = self._hybrid_search(q, box_id, self.retrieval_top_k)
            for d in docs:
                key = (d.get("document_id"), d.get("chunk_index"))
                if key not in all_merged:
                    all_merged[key] = d
                else:
                    # Accumulate RRF score
                    all_merged[key]["rrf_score"] = (all_merged[key].get("rrf_score", 0.0) + d.get("rrf_score", 0.0))
                    # Keep best embedding/lexical score
                    e1 = all_merged[key].get("embedding_score", 0.0)
                    e2 = d.get("embedding_score", 0.0)
                    all_merged[key]["embedding_score"] = max(e1 if e1 is not None else 0.0, e2 if e2 is not None else 0.0)
                    
                    l1 = all_merged[key].get("lexical_score", 0.0)
                    l2 = d.get("lexical_score", 0.0)
                    all_merged[key]["lexical_score"] = max(l1 if l1 is not None else 0.0, l2 if l2 is not None else 0.0)
                    
        # Sort by accumulated RRF
        merged_list = sorted(all_merged.values(), key=lambda x: x.get("rrf_score", 0.0), reverse=True)
        
        if merged_list and self.reranker:
            try:
                merged_list = self.reranker.rerank(query=reranker_query, documents=merged_list, top_k=self.reranker_top_k)
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
            
        sorted_docs = sorted(docs.values(), key=lambda x: x["rrf_score"], reverse=True)
        return sorted_docs[:limit]

    def _expand_lexical_variants(self, text: str) -> str:
        variants_map = {
            "gst": "Goods and Services Tax",
            "pf": "Provident Fund EPF",
            "epf": "Provident Fund PF",
            "pto": "Paid Time Off",
            "hr": "Human Resources",
            "nda": "Non-Disclosure Agreement",
            "kpi": "Key Performance Indicator",
            "roi": "Return on Investment",
        }
        words = text.split()
        expanded_words = []
        for word in words:
            clean_word = word.lower().strip(",.?!()[]{}\"'")
            expanded_words.append(word)
            if clean_word in variants_map:
                expanded_words.append(variants_map[clean_word])
        
        return " ".join(expanded_words)
