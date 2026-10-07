import time
import re
from app.interfaces.vector_store import IVectorStore
from app.interfaces.lexical_store import ILexicalStore
from app.interfaces.embedder import IEmbedder
from app.interfaces.llm import ILLM
from app.interfaces.reranker import IReranker
from app.core.logger import logger
from app.core.config import settings
from app.services.retrieval_engine import RetrievalEngine
from app.services.evidence_engine import EvidenceEngine
from app.services.query_router import RuleBasedQueryRouter
from app.services.query_expansion import QueryExpansionService


class ChatService:
    def __init__(
        self,
        db: IVectorStore,
        lexical_store: ILexicalStore,
        embedder: IEmbedder,
        llm: ILLM,
        reranker: IReranker,
        retrieval_top_k: int = 20,
        reranker_top_k: int = 5,
        min_relevance_score: float = 0.15,
        min_relevance_score_low: float = 0.05,
    ):
        self.db = db
        self.lexical_store = lexical_store
        self.embedder = embedder
        self.llm = llm
        self.reranker = reranker
        self.retrieval_top_k = retrieval_top_k
        self.reranker_top_k = reranker_top_k
        
        self.router = RuleBasedQueryRouter()
        self.query_expansion = QueryExpansionService(llm=llm)
        
        self.retrieval_engine = RetrievalEngine(
            db=db,
            lexical_store=lexical_store,
            embedder=embedder,
            reranker=reranker,
            retrieval_top_k=retrieval_top_k,
            reranker_top_k=reranker_top_k,
        )
        self.evidence_engine = EvidenceEngine(
            db=db,
            min_relevance_score=min_relevance_score,
            min_relevance_score_low=min_relevance_score_low,
            enable_neighbor_context=False,
        )

    def ask_question(self, question: str, box_id: str, session_id: str) -> dict:
        total_start = time.perf_counter()

        # 1. Save user question to stateful memory
        try:
            self.db.save_chat_message(session_id=session_id, role="user", content=question)
        except Exception as e:
            logger.error(f"Failed to save user message: {e}")

        # 2. Fetch history (deterministic truncation)
        chat_history = []
        try:
            chat_history = self.db.get_chat_history(session_id=session_id, box_id=box_id)
        except Exception as e:
            logger.warning(f"Failed to fetch chat history, continuing without it: {e}")
            
        recent_history = chat_history[-8:] if len(chat_history) > 8 else chat_history

        # 3. Query Routing
        route_decision = self.router.route(question, len(recent_history))
        route = route_decision["route"]
        logger.info(f"Router decided route: {route}")
        
        rewritten_query = question
        variants = []
        
        rewrite_start = time.perf_counter()
        if route == "follow_up":
            logger.info("Executing follow_up query expansion (1 LLM call)...")
            expansion = self.query_expansion.expand(question, recent_history)
            rewritten_query = expansion["rewritten_query"]
            variants = expansion["variants"]
        rewrite_ms = (time.perf_counter() - rewrite_start) * 1000

        # 4. Retrieval Pipeline (First Pass)
        retrieval_start = time.perf_counter()
        retrieved_docs = self.retrieval_engine.retrieve_documents(search_query=rewritten_query, box_id=box_id)
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        # 5. Evidence Gate
        top_score = max((self.evidence_engine.get_doc_relevance_score(doc) for doc in retrieved_docs), default=0.0)
        
        rescue_used = False
        closest_matches = []
        
        if not retrieved_docs or top_score < settings.ANSWER_MIN_RELEVANCE_SCORE:
            logger.info(f"First pass evidence weak (top_score={top_score:.3f}). Triggering Rescue Pass.")
            rescue_used = True
            rescue_start = time.perf_counter()
            
            if route == "normal":
                logger.info("Executing normal rescue query expansion (1 LLM call)...")
                expansion = self.query_expansion.expand(question, [])
                rewritten_query = expansion["rewritten_query"]
                variants = expansion["variants"]
                
            queries_to_run = [rewritten_query] + variants
            logger.info(f"Rescue running queries: {queries_to_run}")
            
            retrieved_docs = self.retrieval_engine.retrieve_documents_multi(
                queries=queries_to_run, 
                box_id=box_id, 
                reranker_query=rewritten_query
            )
            rescue_ms = (time.perf_counter() - rescue_start) * 1000
            retrieval_ms += rescue_ms
            
            top_score = max((self.evidence_engine.get_doc_relevance_score(doc) for doc in retrieved_docs), default=0.0)
            
        fallback_phrase = "I could not find the answer to this in the provided company documents."
        
        # 6. Final Evidence Check
        if not retrieved_docs or top_score < settings.ANSWER_MIN_RELEVANCE_SCORE:
            logger.info(f"Rescue pass still weak (top_score={top_score:.3f}). Returning closest matches.")
            # Map retrieved docs to closest matches citations
            for doc in retrieved_docs[:3]:
                closest_matches.append({
                    "document_id": doc.get("document_id"),
                    "filename": doc.get("filename", ""),
                    "chunk_index": doc.get("chunk_index"),
                    "section_title": doc.get("section_title"),
                    "content": doc.get("content", ""),
                    "rerank_score": doc.get("rerank_score", None)
                })
                
            try:
                self.db.save_chat_message(session_id=session_id, role="assistant", content=fallback_phrase)
            except Exception as e:
                pass
                
            return {
                "answer": fallback_phrase,
                "key_takeaways": [],
                "related_questions": [],
                "citations": [],
                "closest_matches": closest_matches,
                "session_id": session_id,
                "confidence": "low",
            }

        # 7. Context Builder
        retrieved_docs = self.evidence_engine.assign_evidence_ids(retrieved_docs)
        context_text = self.evidence_engine.build_context_text(retrieved_docs)

        # 8. Prompt Building
        system_prompt = self._build_system_prompt(
            context_text=context_text,
            fallback_phrase=fallback_phrase,
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Append rewritten query as user message to LLM to keep focus (or just use original question, 
        # but rewritten might be better if follow-up. Let's stick to original to not confuse UX, but with context)
        # We don't append question here because history already has the user question!
        # Wait, step 1 saved it, step 2 fetched it, so it's ALREADY in recent_history!

        # 9. Call Final LLM
        llm_start = time.perf_counter()
        try:
            answer = self.llm.chat_with_messages(messages=messages, temperature=0.0)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            answer = fallback_phrase
        llm_ms = (time.perf_counter() - llm_start) * 1000

        # 10. Citation Integrity Check
        citations = []
        if fallback_phrase not in answer:
            answer = re.sub(r'【(E\d+)】', r'[\1]', answer)
            found_numbers = set(re.findall(r'[\[\(\s]E(\d+)[\]\)\s]', answer))
            used_evidence_ids = {f"[E{num}]" for num in found_numbers}
            
            valid_evidence_ids = {doc.get("evidence_id") for doc in retrieved_docs if doc.get("evidence_id")}
            
            # Clean up invalid citations from text
            for used_id in used_evidence_ids:
                if used_id not in valid_evidence_ids:
                    answer = answer.replace(used_id, "")
            
            # Build citations
            for doc in retrieved_docs:
                evidence_id = doc.get("evidence_id")
                if evidence_id in used_evidence_ids and evidence_id in valid_evidence_ids:
                    citations.append({
                        "evidence_id": evidence_id,
                        "document_id": doc.get("document_id"),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index"),
                        "page_start": doc.get("page_start"),
                        "page_end": doc.get("page_end"),
                        "section_title": doc.get("section_title"),
                        "content": doc.get("content", ""),
                        "rerank_score": doc.get("rerank_score", None),
                    })
                    
            if not citations:
                answer = fallback_phrase

        # Save assistant message
        try:
            self.db.save_chat_message(session_id=session_id, role="assistant", content=answer)
        except:
            pass

        total_ms = (time.perf_counter() - total_start) * 1000
        logger.info(
            f"Chat timings | rewrite={rewrite_ms:.1f}ms | retrieval={retrieval_ms:.1f}ms "
            f"| llm={llm_ms:.1f}ms | total={total_ms:.1f}ms | rescue_used={rescue_used} | docs={len(retrieved_docs)}"
        )

        return {
            "answer": answer,
            "key_takeaways": [],
            "related_questions": [],
            "citations": citations,
            "closest_matches": [],
            "session_id": session_id,
            "confidence": "high",
        }

    def _build_system_prompt(self, context_text: str, fallback_phrase: str) -> str:
        return f"""You are ActionRAG, an expert Enterprise Knowledge Agent.

INSTRUCTIONS:
1. FACTUAL ACCURACY: Answer the user's question using ONLY the facts provided in the CONTEXT below. Never invent, assume, or hallucinate information not present in the sources.
2. DETAIL LEVEL: Provide a concise but complete answer in 1-3 short paragraphs.
3. OUTPUT STRUCTURE: Keep a natural narrative format, but still separate major ideas into clear paragraphs.
4. EVIDENCE CITATION: The CONTEXT is divided into numbered evidence blocks (e.g., '--- EVIDENCE [E1] ---').
   - You MUST base your factual claims ONLY on this supplied evidence.
   - You MUST cite the supporting evidence IDs in your answer using the format [E1], [E2], etc.
   - If the user asks about a specific document, ONLY use facts from that file's sections.
   - If the evidence does not support a complete answer, explicitly state what is missing.
5. SYNTHESIS: When multiple chunks from the SAME document are relevant, synthesize them into a coherent answer rather than repeating information.
6. SOURCE-CLAIM DISCIPLINE: Do not make a claim unless it is supported by at least one retrieved source chunk.
7. THE SHIELD: If the CONTEXT does not contain enough information, reply with EXACTLY: "{fallback_phrase}"

CONTEXT:
{context_text}"""
