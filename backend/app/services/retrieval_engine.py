from typing import Optional
from app.interfaces.vector_store import IVectorStore
from app.interfaces.embedder import IEmbedder
from app.interfaces.llm import ILLM
from app.interfaces.reranker import IReranker
from app.core.logger import logger

class RetrievalEngine:
    def __init__(
        self,
        db: IVectorStore,
        embedder: IEmbedder,
        llm: ILLM,
        reranker: IReranker,
        retrieval_top_k: int = 40,
        reranker_top_k: int = 8,
        enable_hyde: bool = True,
        enable_multi_query: bool = True,
    ):
        self.db = db
        self.embedder = embedder
        self.llm = llm
        self.reranker = reranker
        self.retrieval_top_k = retrieval_top_k
        self.reranker_top_k = reranker_top_k
        self.enable_hyde = enable_hyde
        self.enable_multi_query = enable_multi_query

    def retrieve_documents(
        self,
        search_query: str,
        box_id: str,
        force_hyde: Optional[bool] = None,
        force_multi_query: Optional[bool] = None,
        retrieval_limit: Optional[int] = None,
    ) -> list[dict]:
        """Runs full retrieval stack and returns retrieved documents."""
        search_queries = self._build_search_queries(
            search_query=search_query,
            use_hyde=force_hyde,
            use_multi_query=force_multi_query,
        )

        retrieved_docs = self._multi_query_search(
            queries=search_queries,
            original_query=search_query,
            box_id=box_id,
            retrieval_limit=retrieval_limit,
        )

        if retrieved_docs and self.reranker:
            try:
                retrieved_docs = self.reranker.rerank(
                    query=search_query,
                    documents=retrieved_docs,
                    top_k=self.reranker_top_k,
                )
                logger.info(f"Re-ranked → top {len(retrieved_docs)} docs")
            except Exception as e:
                logger.warning(f"Re-ranking failed, using original order: {e}")
                retrieved_docs = retrieved_docs[:self.reranker_top_k]

        return retrieved_docs

    def execute_accuracy_rescue(self, search_query: str, box_id: str) -> list[dict]:
        return self.retrieve_documents(
            search_query=search_query,
            box_id=box_id,
            force_hyde=True,
            force_multi_query=True,
            retrieval_limit=max(self.retrieval_top_k, self.retrieval_top_k + 10),
        )

    def _build_search_queries(
        self,
        search_query: str,
        use_hyde: Optional[bool] = None,
        use_multi_query: Optional[bool] = None,
    ) -> list[str]:
        queries = [search_query]
        use_hyde = self.enable_hyde if use_hyde is None else use_hyde
        use_multi_query = self.enable_multi_query if use_multi_query is None else use_multi_query

        if use_hyde:
            try:
                hypothetical = self.llm.generate_response(
                    system_prompt=(
                        "You are a helpful assistant. Given a question, write a short paragraph (2-3 sentences) "
                        "that would answer this question, as if quoting from an internal company document. "
                        "Be specific and factual-sounding. Output ONLY the paragraph."
                    ),
                    user_prompt=search_query,
                    temperature=0.0,
                )
                if hypothetical and len(hypothetical) > 20:
                    queries.append(hypothetical)
                    logger.info(f"HyDE generated hypothetical answer ({len(hypothetical)} chars)")
            except Exception as e:
                logger.warning(f"HyDE generation failed: {e}")

        if use_multi_query:
            try:
                alternatives = self.llm.generate_response(
                    system_prompt=(
                        "You are a search query optimizer. Given a question, generate 2 alternative "
                        "phrasings that might retrieve different relevant documents. "
                        "Output ONLY the 2 queries, one per line, no numbering or bullets."
                    ),
                    user_prompt=search_query,
                    temperature=0.3,
                )
                if alternatives:
                    for alt in alternatives.strip().split("\n"):
                        alt = alt.strip().strip("-").strip("•").strip()
                        if alt and len(alt) > 10 and len(alt) < 300:
                            queries.append(alt)
                    logger.info(f"Multi-query generated {len(queries)-1} alternative queries")
            except Exception as e:
                logger.warning(f"Multi-query generation failed: {e}")

        return queries

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

    def _multi_query_search(
        self,
        queries: list[str],
        original_query: str,
        box_id: str,
        retrieval_limit: Optional[int] = None,
    ) -> list[dict]:
        all_docs = {}
        search_limit = retrieval_limit or self.retrieval_top_k
        lexical_query = self._expand_lexical_variants(original_query)

        for query in queries:
            try:
                query_vector = self.embedder.embed_text([query])[0]
                docs = self.db.search_similar(
                    query_vector=query_vector,
                    query_text=lexical_query,
                    box_id=box_id,
                    limit=search_limit,
                )
                for doc in docs:
                    content_key = (doc.get("document_id"), doc.get("chunk_index"))
                    existing = all_docs.get(content_key)
                    score = doc.get("rrf_score") or doc.get("embedding_score") or 0.0
                    existing_score = existing.get("rrf_score") or existing.get("embedding_score") or 0.0 if existing else -1.0
                    if not existing or score > existing_score:
                        all_docs[content_key] = doc
            except Exception as e:
                logger.error(f"Search failed for query variant: {e}")

        merged = list(all_docs.values())
        logger.info(f"Multi-query search: {len(queries)} queries → {len(merged)} unique docs")
        return merged
