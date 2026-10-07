"""
Chat Service — the core Q&A engine with advanced retrieval strategies.

ACCURACY FEATURES (v2):
  - HyDE (Hypothetical Document Embeddings) — bridges vocabulary mismatch
  - Multi-query retrieval — searches with 3 query variations
  - Cross-encoder re-ranking — scores each (query, doc) with full attention
  - Dynamic relevance threshold — adapts when few results survive
  - Parent-child context — expands matched chunks with neighboring context
  - Chat history condensation — summarizes old history to save tokens
  - Multi-source confidence — detects when sources disagree

Uses interfaces (IVectorStore, IEmbedder, ILLM, IReranker) so swapping
adapters requires zero changes here — just update .env.
"""
import time
import re
from app.interfaces.vector_store import IVectorStore
from app.interfaces.embedder import IEmbedder
from app.interfaces.llm import ILLM
from app.interfaces.reranker import IReranker
from app.core.logger import logger
from app.core.config import settings
from app.services.retrieval_engine import RetrievalEngine
from app.services.evidence_engine import EvidenceEngine


class ChatService:
    def __init__(
        self,
        db: IVectorStore,
        embedder: IEmbedder,
        llm: ILLM,
        reranker: IReranker,
        query_rewriter=None,
        retrieval_top_k: int = 40,
        reranker_top_k: int = 8,
        min_relevance_score: float = 0.3,
        min_relevance_score_low: float = 0.1,
        enable_hyde: bool = True,
        enable_multi_query: bool = True,
        enable_neighbor_context: bool = True,
    ):
        self.db = db
        self.embedder = embedder
        self.llm = llm
        self.reranker = reranker
        self.query_rewriter = query_rewriter
        self.retrieval_top_k = retrieval_top_k
        self.reranker_top_k = reranker_top_k
        self.min_relevance_score = min_relevance_score
        self.min_relevance_score_low = min_relevance_score_low
        self.enable_hyde = enable_hyde
        self.enable_multi_query = enable_multi_query
        self.enable_neighbor_context = enable_neighbor_context

        self.retrieval_engine = RetrievalEngine(
            db=db,
            embedder=embedder,
            llm=llm,
            reranker=reranker,
            retrieval_top_k=retrieval_top_k,
            reranker_top_k=reranker_top_k,
            enable_hyde=enable_hyde,
            enable_multi_query=enable_multi_query,
        )
        self.evidence_engine = EvidenceEngine(
            db=db,
            min_relevance_score=min_relevance_score,
            min_relevance_score_low=min_relevance_score_low,
            enable_neighbor_context=enable_neighbor_context,
        )

    def ask_question(self, question: str, box_id: str, session_id: str) -> dict:
        total_start = time.perf_counter()

        # 1. Save user question to stateful memory
        try:
            self.db.save_chat_message(session_id=session_id, role="user", content=question)
        except Exception as e:
            logger.error(f"Failed to save user message: {e}")

        # 2. Fetch history (graceful: empty history if DB fails)
        chat_history = []
        try:
            chat_history = self.db.get_chat_history(session_id=session_id, box_id=box_id)
        except Exception as e:
            logger.warning(f"Failed to fetch chat history, continuing without it: {e}")

        # 3. Use original question for first pass (no rewrite yet)
        rewrite_start = time.perf_counter()
        search_query = question
        rewrite_ms = (time.perf_counter() - rewrite_start) * 1000

        # 4-8. Retrieval Pipeline (normal pass)
        retrieval_start = time.perf_counter()
        retrieved_docs = self.retrieval_engine.retrieve_documents(
            search_query=search_query, 
            box_id=box_id,
            force_hyde=False,
            force_multi_query=False
        )
        retrieved_docs = self.evidence_engine.filter_and_expand(retrieved_docs)
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        # 9. Confidence detection (normal pass)
        confidence_level = self.evidence_engine.determine_confidence(retrieved_docs)
        rescue_used = False

        # 9b. Accuracy rescue pass: retry once only when evidence is genuinely weak.
        if self.evidence_engine.should_run_accuracy_rescue(confidence_level, retrieved_docs):
            rescue_start = time.perf_counter()
            
            # ✨ Query Rewriting ONLY happens if first pass fails
            rescue_query = search_query
            if self.query_rewriter:
                try:
                    logger.info("First pass failed; executing query rewriting for rescue pass...")
                    rescue_query = self.query_rewriter.rewrite(question, chat_history)
                except Exception as e:
                    logger.warning(f"Query rewriting failed during rescue, using original: {e}")
                    rescue_query = search_query

            rescue_docs = self.retrieval_engine.execute_accuracy_rescue(search_query=rescue_query, box_id=box_id)
            rescue_docs = self.evidence_engine.filter_and_expand(rescue_docs)
            rescue_ms = (time.perf_counter() - rescue_start) * 1000
            rescue_confidence = self.evidence_engine.determine_confidence(rescue_docs)

            rank = {"low": 0, "medium": 1, "multi_source": 2, "high": 3}
            current_top = max((self.evidence_engine.get_doc_relevance_score(doc) for doc in retrieved_docs), default=0.0)
            rescue_top = max((self.evidence_engine.get_doc_relevance_score(doc) for doc in rescue_docs), default=0.0)

            should_use_rescue = (
                rank.get(rescue_confidence, 0) > rank.get(confidence_level, 0)
                or (
                    rank.get(rescue_confidence, 0) == rank.get(confidence_level, 0)
                    and rescue_top >= (current_top + 0.05)
                )
                or (
                    rank.get(rescue_confidence, 0) == rank.get(confidence_level, 0)
                    and len(rescue_docs) > len(retrieved_docs)
                    and rescue_top >= current_top
                )
            )

            if should_use_rescue:
                logger.info(
                    f"Rescue pass selected | confidence {confidence_level}→{rescue_confidence} "
                    f"| docs {len(retrieved_docs)}→{len(rescue_docs)}"
                )
                retrieved_docs = rescue_docs
                confidence_level = rescue_confidence
                rescue_used = True

            logger.info(
                f"Rescue pass evaluated | used={rescue_used} | ms={rescue_ms:.1f} "
                f"| confidence={confidence_level}"
            )

        logger.info(f"Confidence level: {confidence_level}")

        # Retrieval may intentionally keep weak matches so users can inspect them,
        # but they are not evidence strong enough to answer an unrelated question.
        fallback_phrase = "I could not find the answer to this in the provided company documents."
        top_score = max((self.evidence_engine.get_doc_relevance_score(doc) for doc in retrieved_docs), default=0.0)
        if not retrieved_docs or top_score < settings.ANSWER_MIN_RELEVANCE_SCORE:
            logger.info(
                f"Grounded-answer gate blocked response | top_score={top_score:.3f} "
                f"| required={settings.ANSWER_MIN_RELEVANCE_SCORE:.3f}"
            )
            try:
                self.db.save_chat_message(session_id=session_id, role="assistant", content=fallback_phrase)
            except Exception as e:
                logger.error(f"Failed to save grounded fallback: {e}")
            return {
                "answer": fallback_phrase,
                "key_takeaways": [],
                "related_questions": [],
                "citations": [],
                "session_id": session_id,
                "confidence": "low",
            }

        # 10. Context Builder (labeled, isolated, with relevance scores)
        retrieved_docs = self.evidence_engine.assign_evidence_ids(retrieved_docs)
        context_text = self.evidence_engine.build_context_text(retrieved_docs)

        # 11. Structured logging
        logger.info(f"Chat query | box={box_id} | session={session_id}")
        logger.debug(f"Retrieved {len(retrieved_docs)} docs: {[d.get('filename') for d in retrieved_docs]}")

        # 12. THE DEFINED FALLBACK PHRASE
        # 13. ✨ Chat History Condensation
        condensed_history = self._condense_history(chat_history)

        # 14. ✨ Confidence-aware system prompt
        system_prompt = self._build_system_prompt(
            context_text=context_text,
            fallback_phrase=fallback_phrase,
            confidence_level=confidence_level,
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Inject condensed history
        for msg in condensed_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # 15. Call LLM through interface
        llm_start = time.perf_counter()
        try:
            answer = self.llm.chat_with_messages(messages=messages, temperature=0.0)
        except Exception as e:
            logger.error(f"LLM call failed after retries: {e}")
            answer = "I'm temporarily unable to process your question. Please try again in a moment."
        llm_ms = (time.perf_counter() - llm_start) * 1000

        # 16. Save AI answer (non-fatal if it fails)
        try:
            self.db.save_chat_message(session_id=session_id, role="assistant", content=answer)
        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}")

        # 17. Extract Key Takeaways (NEW)
        post_start = time.perf_counter()
        key_takeaways = []
        if settings.ENABLE_KEY_TAKEAWAYS:
            try:
                key_takeaways = self._extract_key_takeaways(answer)
            except Exception as e:
                logger.warning(f"Key takeaway extraction failed: {e}")

        # 18. Generate Related Questions (NEW)
        related_questions = []
        if settings.ENABLE_RELATED_QUESTIONS:
            try:
                related_questions = self._generate_related_questions(answer, retrieved_docs, question)
            except Exception as e:
                logger.warning(f"Related questions generation failed: {e}")
        post_ms = (time.perf_counter() - post_start) * 1000

        # 19. Citation Builder (with re-rank scores)
        citations = []
        if fallback_phrase not in answer:
            # Normalize full-width brackets like 【E1】 to [E1] for clean UI rendering and parsing
            answer = re.sub(r'【(E\d+)】', r'[\1]', answer)
            
            # Parse [E<number>] references from the answer
            found_numbers = set(re.findall(r'[\[\(\s]E(\d+)[\]\)\s]', answer))
            used_evidence_ids = {f"[E{num}]" for num in found_numbers}
            
            for doc in retrieved_docs:
                evidence_id = doc.get("evidence_id")
                if evidence_id in used_evidence_ids:
                    citations.append({
                        "evidence_id": evidence_id,
                        "document_id": doc.get("document_id"),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index"),
                        "page_start": doc.get("page_start"),
                        "page_end": doc.get("page_end"),
                        "section_title": doc.get("section_title"),
                        "content": doc.get("content", ""),
                        "embedding_score": doc.get("embedding_score", None),
                        "lexical_score": doc.get("lexical_score", None),
                        "rrf_score": doc.get("rrf_score", None),
                        "rerank_score": doc.get("rerank_score", None),
                    })

        total_ms = (time.perf_counter() - total_start) * 1000
        logger.info(
            f"Chat timings | rewrite={rewrite_ms:.1f}ms | retrieval={retrieval_ms:.1f}ms "
            f"| llm={llm_ms:.1f}ms | post={post_ms:.1f}ms | total={total_ms:.1f}ms "
            f"| rescue_used={rescue_used} | docs={len(retrieved_docs)}"
        )

        return {
            "answer": answer,
            "key_takeaways": key_takeaways,
            "related_questions": related_questions,
            "citations": citations,
            "session_id": session_id,
            "confidence": confidence_level,
        }

    # ══════════════════════════════════════════════
    # ✨ NEW: Chat History Condensation
    # ══════════════════════════════════════════════

    def _condense_history(self, chat_history: list) -> list:
        """
        Condenses long chat histories to save LLM tokens.

        - If ≤ 10 messages: pass all of them directly
        - If > 10 messages: summarize older messages + keep last 4 verbatim
        """
        if len(chat_history) <= 10:
            return chat_history

        # Split into old (to summarize) and recent (to keep verbatim)
        old_messages = chat_history[:-4]
        recent_messages = chat_history[-4:]

        try:
            old_text = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}" for msg in old_messages
            )

            summary = self.llm.generate_response(
                system_prompt=(
                    "Summarize the following conversation history in 2-3 sentences. "
                    "Focus on the key topics discussed and any important facts mentioned. "
                    "Output ONLY the summary."
                ),
                user_prompt=old_text[:2000],
                temperature=0.0,
            )

            if summary and len(summary) > 10:
                condensed = [
                    {"role": "system", "content": f"[Previous conversation summary: {summary}]"}
                ]
                condensed.extend(recent_messages)
                logger.info(f"Condensed {len(old_messages)} old messages into summary")
                return condensed

        except Exception as e:
            logger.warning(f"History condensation failed, using last 8 messages: {e}")

        return chat_history[-8:]

    # ══════════════════════════════════════════════
    # Confidence & Prompt Building
    # ══════════════════════════════════════════════

    def _build_system_prompt(
        self, context_text: str, fallback_phrase: str, confidence_level: str
    ) -> str:
        """
        Builds a confidence-aware system prompt.

        - High confidence: full authoritative answer
        - Multi-source: synthesize across documents, note differences
        - Medium confidence: hedged answer acknowledging uncertainty
        - Low confidence: fallback
        """
        if confidence_level == "low" and not context_text:
            # No context at all — use minimal prompt
            return f"""You are ActionRAG, an Enterprise Knowledge Agent.

You have NO relevant documents to answer the user's question.
Reply with EXACTLY this phrase and nothing else: "{fallback_phrase}" """

        detail_level = (settings.ANSWER_DETAIL_LEVEL or "comprehensive").strip().lower()
        if detail_level == "standard":
            detail_instruction = "Provide a concise but complete answer in 1-3 short paragraphs."
        elif detail_level == "detailed":
            detail_instruction = "Provide a detailed answer with clear explanations, covering key points and important nuances."
        else:
            detail_instruction = "Provide a comprehensive answer with full coverage of relevant points, edge cases, and practical implications from the context."

        if settings.ENABLE_STRUCTURED_ANSWERS:
            structure_instruction = (
                "OUTPUT STRUCTURE: Use this structure when relevant: "
                "## Direct Answer, ## Detailed Explanation, ## Evidence by Source, ## Gaps or Unknowns."
            )
        else:
            structure_instruction = (
                "OUTPUT STRUCTURE: Keep a natural narrative format, but still separate major ideas into clear paragraphs."
            )

        confidence_instruction = ""
        if confidence_level == "high":
            confidence_instruction = """CONFIDENCE: The retrieved sources are HIGHLY relevant. Give a direct, authoritative answer based on the evidence below."""
        elif confidence_level == "multi_source":
            confidence_instruction = """CONFIDENCE: The answer spans MULTIPLE documents. Synthesize information across all sources into a coherent answer. If sources contain conflicting information, clearly note the discrepancy and cite which document says what."""
        elif confidence_level == "medium":
            confidence_instruction = """CONFIDENCE: The retrieved sources are PARTIALLY relevant. Answer what you can from the evidence, but clearly state what information is incomplete or uncertain. Preface uncertain parts with "Based on the available information..." or "The documents suggest..." — do NOT invent facts to fill gaps."""
        else:
            confidence_instruction = f"""CONFIDENCE: The retrieved sources have LOW relevance to the question. Provide a cautious, evidence-limited answer using ONLY available context. If the context still does not support a direct answer, reply with EXACTLY: "{fallback_phrase}" """

        return f"""You are ActionRAG, an expert Enterprise Knowledge Agent.

INSTRUCTIONS:
1. FACTUAL ACCURACY: Answer the user's question using ONLY the facts provided in the CONTEXT below. Never invent, assume, or hallucinate information not present in the sources.
2. {confidence_instruction}
3. DETAIL LEVEL: {detail_instruction}
4. {structure_instruction}
5. EVIDENCE CITATION: The CONTEXT is divided into numbered evidence blocks (e.g., '--- EVIDENCE [E1] ---').
   - You MUST base your factual claims ONLY on this supplied evidence.
   - You MUST cite the supporting evidence IDs in your answer using the format [E1], [E2], etc.
   - If the user asks about a specific document, ONLY use facts from that file's sections.
   - If the evidence does not support a complete answer, explicitly state what is missing.
6. SYNTHESIS: When multiple chunks from the SAME document are relevant, synthesize them into a coherent answer rather than repeating information.
7. NATURAL STRUCTURE (FLEXIBLE): Write naturally and conversationally, using structure ONLY where it improves clarity:
   - For complex topics: Use clear paragraphs with descriptive headers (##, ###) where appropriate
   - For lists: Use bullet points naturally when describing multiple items
   - For comparisons: Use tables when comparing 2+ similar items
   - Don't force sections if the topic flows better as prose
   - When relevant, highlight key points with **bold** for emphasis
   - Use appropriate markdown but keep it minimal and natural
8. FORMATTING GUIDELINES:
   - Use markdown naturally and minimally
   - Use **bold** only for key terms and concepts
   - Use bullet points for actual lists, not for padding
   - Use headers (##, ###) only when topic transitions are clear
   - Keep writing concise, engaging, and direct
9. SOURCE-CLAIM DISCIPLINE: Do not make a claim unless it is supported by at least one retrieved source chunk.
10. THE SHIELD: If the CONTEXT does not contain enough information, reply with EXACTLY: "{fallback_phrase}"

CONTEXT:
{context_text}"""

    # ══════════════════════════════════════════════
    # ✨ NEW: Key Takeaways & Related Questions
    # ══════════════════════════════════════════════

    def _extract_key_takeaways(self, answer: str) -> list[str]:
        """
        Intelligently extracts key takeaways from the answer ONLY if meaningful.

        Strategy 1: Parse markdown for existing bullet points (natural structure)
        Strategy 2: Only use LLM extraction if answer is long enough (>500 chars)
        Strategy 3: Return empty if answer is short or conversational (no forced extraction)
        """
        import re

        # Strategy 1: Look for existing bullet points in the answer
        # If the answer naturally has bullet points, extract those as takeaways
        bullet_pattern = r"[•\-\*]\s+(.+?)(?=\n[•\-\*]|\n##|\n\n|$)"
        bullets = re.findall(bullet_pattern, answer, re.DOTALL)

        if bullets:
            # Filter to meaningful bullets (>10 chars, not too long)
            meaningful_bullets = [
                b.strip().replace('\n', ' ')[:120]
                for b in bullets
                if b.strip() and len(b.strip()) > 10 and len(b.strip()) < 500
            ]
            if meaningful_bullets:
                return meaningful_bullets[:settings.KEY_TAKEAWAYS_COUNT]

        # Strategy 2: Only extract if answer is substantial (avoid forcing structure on short answers)
        if len(answer) < 300:
            return []  # Too short for takeaways

        # Strategy 3: Use LLM extraction ONLY for longer answers
        try:
            takeaways_text = self.llm.generate_response(
                system_prompt=(
                    f"Extract 2-3 key takeaways from this text. "
                    "Output ONLY bullet points (starting with •), one per line. "
                    "Keep each takeaway under 20 words. "
                    "Only extract if there are clear, distinct points worth highlighting. "
                    "If the text is conversational with no clear key points, output: NONE"
                ),
                user_prompt=answer[:2000],
                temperature=0.0,
            )

            if takeaways_text and "NONE" not in takeaways_text.upper():
                # Parse bullet points
                bullets = re.findall(bullet_pattern, takeaways_text)
                if bullets:
                    takeaways = [
                        b.strip().replace('\n', ' ')[:120]
                        for b in bullets if b.strip()
                    ]
                    return takeaways[:settings.KEY_TAKEAWAYS_COUNT]

        except Exception as e:
            logger.warning(f"LLM extract_key_takeaways failed: {e}")

        return []

    def _generate_related_questions(
        self, answer: str, retrieved_docs: list, original_question: str
    ) -> list[str]:
        """
        Generates related follow-up questions ONLY when relevant.

        Only generates if:
        - Answer is long enough (substantive content)
        - Multiple documents involved (suggests complexity)
        - Answer has clear topics to expand on
        """

        # Only generate if answer is substantial and multi-sourced
        if len(answer) < 200:
            return []  # Too short for meaningful follow-ups

        unique_files = set(doc.get("filename", "") for doc in retrieved_docs)
        if len(unique_files) < 2:
            return []  # Single source, likely simple question

        # Extract key topics from retrieved documents
        doc_topics = []
        for doc in retrieved_docs[:3]:
            filename = doc.get("filename", "")
            if filename:
                doc_topics.append(filename.replace(".pdf", "").replace(".docx", ""))

        topics_str = ", ".join(doc_topics[:3]) if doc_topics else "related topics"

        try:
            questions_text = self.llm.generate_response(
                system_prompt=(
                    "Based on the provided text, suggest 2-3 natural follow-up questions "
                    "that a curious reader might ask. "
                    "Questions should explore adjacent topics, deeper aspects, or related areas. "
                    "Output ONLY the questions, one per line, without numbering. "
                    "Keep each under 15 words. "
                    "If the answer is too simple/complete and doesn't warrant follow-ups, output: NONE"
                ),
                user_prompt=f"""Original question: {original_question}

Answer: {answer[:1000]}

Sources: {topics_str}""",
                temperature=0.3,
            )

            if questions_text and "NONE" not in questions_text.upper():
                # Parse questions (one per line, non-empty)
                questions = [
                    q.strip().strip("?").strip().rstrip("?") + "?"
                    for q in questions_text.strip().split("\n")
                    if q.strip() and len(q.strip()) > 10
                ]
                # Filter out duplicates and very similar to original
                unique_questions = []
                seen = set()
                for q in questions:
                    q_lower = q.lower()
                    # Check if too similar to original question
                    if q_lower not in seen and original_question.lower() not in q_lower:
                        unique_questions.append(q)
                        seen.add(q_lower)
                        if len(unique_questions) >= settings.RELATED_QUESTIONS_COUNT:
                            break
                return unique_questions

        except Exception as e:
            logger.warning(f"Generate_related_questions failed: {e}")

        return []
