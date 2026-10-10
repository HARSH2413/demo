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
            enable_neighbor_context=settings.ENABLE_NEIGHBOR_CONTEXT,
        )

    def ask_question(self, question: str, box_id: str, session_id: str) -> dict:
        total_start = time.perf_counter()
        fallback_phrase = settings.FALLBACK_PHRASE

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
        retrieved_docs = self.evidence_engine.filter_and_expand(retrieved_docs)
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
            
            retrieved_docs = self.evidence_engine.filter_and_expand(retrieved_docs)
            top_score = max((self.evidence_engine.get_doc_relevance_score(doc) for doc in retrieved_docs), default=0.0)
            
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
            # Avoid duplicating the current question if it was already fetched from history
            if msg.get("role") == "user" and msg.get("content") == question:
                continue
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        # Always explicitly append the current user question
        messages.append({"role": "user", "content": question})

        # 9. Call Final LLM
        llm_start = time.perf_counter()
        try:
            answer = self.llm.chat_with_messages(messages=messages, temperature=0.0)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            answer = fallback_phrase
        llm_ms = (time.perf_counter() - llm_start) * 1000

        # 10. Citation Integrity Check (Firewall)
        answer, citations, unsupported_sentences, stripped_citations = self._validate_and_build_citations(answer, retrieved_docs, fallback_phrase)
        retried = False
        
        # Retry once if answer exists but citations failed completely and LLM did not already say fallback phrase
        if not citations and fallback_phrase not in answer:
            logger.info("Answer generated but zero valid citations. Retrying once with citation enforcement prompt.")
            retry_prompt = (
                "You previously answered without using the required evidence citations. "
                "Please rewrite your answer citing the supporting evidence IDs using [E1], [E2], etc. from the context. "
                f"If the context contains absolutely zero information to answer the question, output exactly: '{fallback_phrase}'"
            )
            
            messages.append({"role": "assistant", "content": answer})
            messages.append({"role": "user", "content": retry_prompt})
            
            try:
                answer = self.llm.chat_with_messages(messages=messages, temperature=0.0)
            except Exception as e:
                logger.error(f"LLM retry call failed: {e}")
                answer = fallback_phrase
                
            answer, citations, unsupported_sentences, stripped_citations = self._validate_and_build_citations(answer, retrieved_docs, fallback_phrase)
            retried = True
            
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

        confidence = self.evidence_engine.determine_confidence(retrieved_docs) if citations else "low"

        return {
            "answer": answer,
            "key_takeaways": [],
            "related_questions": [],
            "citations": citations,
            "closest_matches": [],
            "session_id": session_id,
            "confidence": confidence,
            "validation_metadata": {
                "unsupported_sentences": unsupported_sentences,
                "stripped_citations": stripped_citations,
                "retried": retried
            }
        }

    def _validate_and_build_citations(self, answer: str, retrieved_docs: list[dict], fallback_phrase: str):
        from app.utils.citation_validator import split_into_sentences, extract_normalized_numbers, is_factual_sentence
        from app.core.config import settings
        import re
        
        # Normalize bracket variations like 【E1】, 【E1†L1-L2】, [E1:p140], etc. to [E1]
        answer = re.sub(r'【E(\d+)[^】]*】', r'[E\1]', answer)
        answer = re.sub(r'\[E(\d+)[^\]]*\]', r'[E\1]', answer)
        found_numbers = set(re.findall(r'\[E(\d+)\]', answer))
        used_evidence_ids = {f"[E{num}]" for num in found_numbers}
        
        doc_map = {doc.get("evidence_id"): doc for doc in retrieved_docs if doc.get("evidence_id")}
        valid_evidence_ids = set(doc_map.keys())
        
        sentences = split_into_sentences(answer)
        unsupported_sentences = []
        stripped_citations = []
        
        # 1. Clean up invalid citations that do not exist in the context
        for used_id in used_evidence_ids:
            if used_id not in valid_evidence_ids:
                answer = re.sub(re.escape(used_id), "", answer)
                stripped_citations.append(used_id)
                
        # Re-split sentences after removing nonexistent IDs
        sentences = split_into_sentences(answer)
        
        pairs_to_score = []
        sentence_contexts = []
        
        for i, s in enumerate(sentences):
            if not is_factual_sentence(s):
                continue
                
            cites_in_s = set(re.findall(r'\[E\d+\]', s))
            valid_cites_in_s = cites_in_s.intersection(valid_evidence_ids)
            
            if not valid_cites_in_s:
                unsupported_sentences.append(s)
                continue
                
            # Strip citation tags before checking numbers to avoid matching citation digits
            s_clean_of_tags = re.sub(r'\[E\d+\]', '', s).strip()
            nums_in_s = extract_normalized_numbers(s_clean_of_tags)
            
            # Combine text of all cited chunks for number verification
            chunk_texts = []
            for cid in valid_cites_in_s:
                doc = doc_map[cid]
                text = doc.get("content", "")
                if doc.get("neighbor_context"):
                    text += " " + doc.get("neighbor_context", "")
                chunk_texts.append(text)
                
            combined_text = " ".join(chunk_texts)
            nums_in_chunk = extract_normalized_numbers(combined_text)
            
            number_supported = nums_in_s.issubset(nums_in_chunk) if nums_in_s else True
            
            if not number_supported:
                unsupported_sentences.append(s)
                if settings.CITATION_ENFORCEMENT_MODE == "strict":
                    for cid in valid_cites_in_s:
                        s = s.replace(cid, "")
                        stripped_citations.append(cid)
                    sentences[i] = s
                    continue
                
            s_clean = s_clean_of_tags
            for cid in valid_cites_in_s:
                pairs_to_score.append((s_clean, doc_map[cid].get("content", "")))
                sentence_contexts.append((i, cid))
                
        if pairs_to_score and self.reranker:
            scores = self.reranker.score_pairs(pairs_to_score)
            support_by_sentence = {}
            for (idx, cid), score in zip(sentence_contexts, scores):
                if idx not in support_by_sentence:
                    support_by_sentence[idx] = []
                support_by_sentence[idx].append((cid, score))
                
            for idx, results in support_by_sentence.items():
                max_score = max(score for cid, score in results)
                if max_score < settings.CITATION_SUPPORT_THRESHOLD:
                    unsupported_sentences.append(sentences[idx])
                    if settings.CITATION_ENFORCEMENT_MODE == "strict":
                        for cid, _ in results:
                            sentences[idx] = sentences[idx].replace(cid, "")
                            stripped_citations.append(cid)
                        
        final_answer = " ".join(sentences)
        
        if settings.CITATION_ENFORCEMENT_MODE == "strict":
            final_answer = " ".join([s for s in sentences if s not in unsupported_sentences])
                
        final_found = set(re.findall(r'\[E(\d+)\]', final_answer))
        final_used = {f"[E{num}]" for num in final_found}
        
        citations = []
        for doc in retrieved_docs:
            cid = doc.get("evidence_id")
            if cid in final_used and cid in valid_evidence_ids:
                citations.append({
                    "evidence_id": cid,
                    "document_id": doc.get("document_id"),
                    "filename": doc.get("filename", ""),
                    "chunk_index": doc.get("chunk_index"),
                    "page_start": doc.get("page_start"),
                    "page_end": doc.get("page_end"),
                    "section_title": doc.get("section_title"),
                    "content": doc.get("content", ""),
                    "rerank_score": doc.get("rerank_score", None),
                })
                
        return final_answer, citations, unsupported_sentences, list(set(stripped_citations))

    def _build_system_prompt(self, context_text: str, fallback_phrase: str) -> str:
        return f"""You are DocIntel, an expert Enterprise Knowledge Agent.

INSTRUCTIONS:
1. FACTUAL ACCURACY: Answer the user's question using ONLY the facts provided in the CONTEXT below. Never invent, assume, or hallucinate information not present in the sources.
2. DETAIL LEVEL: Provide a concise but complete answer in 1-3 short paragraphs.
3. OUTPUT STRUCTURE: Keep a natural narrative format, but still separate major ideas into clear paragraphs.
4. EVIDENCE CITATION: The CONTEXT is divided into numbered evidence blocks (e.g., '--- EVIDENCE [E1] ---').
   - You MUST base your factual claims ONLY on this supplied evidence.
   - You MUST cite the supporting evidence IDs in your answer using the format [E1], [E2], etc. immediately after the claims they support.
   - If the user asks about a specific document, ONLY use facts from that file's sections.
   - If the evidence only contains brief mentions, a heading, or partial information about the topic, state what is mentioned in the evidence, cite the evidence ID (e.g., [E1]), and explicitly state what is missing or that detailed explanations/clauses are not present in the provided documents.
5. SYNTHESIS: When multiple chunks are relevant, synthesize them into a coherent answer rather than repeating information.
6. SOURCE-CLAIM DISCIPLINE: Do not make a claim unless it is supported by at least one retrieved source chunk.
7. THE SHIELD: ONLY IF the CONTEXT contains absolutely zero information or relevance to the question, reply with EXACTLY: "{fallback_phrase}"

CONTEXT:
{context_text}"""
