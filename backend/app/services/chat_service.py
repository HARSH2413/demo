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
from typing import Optional
from app.interfaces.vector_store import IVectorStore
from app.interfaces.embedder import IEmbedder
from app.interfaces.llm import ILLM
from app.interfaces.reranker import IReranker
from app.core.logger import logger
from app.core.config import settings


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

    def _get_doc_relevance_score(self, doc: dict) -> float:
        """
        Returns the best available relevance score for a document.

        Priority:
        1) Cross-encoder score (`rerank_score`) when available
        2) Vector/Hybrid score (`similarity`) as fallback
        """
        if "rerank_score" in doc and doc.get("rerank_score") is not None:
            return float(doc.get("rerank_score", 0.0))
        return float(doc.get("similarity", 0.0))

    def ask_question(self, question: str, tenant_id: str, session_id: str) -> dict:
        total_start = time.perf_counter()

        # 1. Save user question to stateful memory
        try:
            self.db.save_chat_message(session_id=session_id, role="user", content=question)
        except Exception as e:
            logger.error(f"Failed to save user message: {e}")

        # 2. Fetch history (graceful: empty history if DB fails)
        chat_history = []
        try:
            chat_history = self.db.get_chat_history(session_id=session_id, tenant_id=tenant_id)
        except Exception as e:
            logger.warning(f"Failed to fetch chat history, continuing without it: {e}")

        # 3. ✨ Query Rewriting — resolve multi-turn context
        rewrite_start = time.perf_counter()
        search_query = question
        if self.query_rewriter:
            try:
                search_query = self.query_rewriter.rewrite(question, chat_history)
            except Exception as e:
                logger.warning(f"Query rewriting failed, using original: {e}")
                search_query = question
        rewrite_ms = (time.perf_counter() - rewrite_start) * 1000

        # 4-8. Retrieval Pipeline (normal pass)
        retrieval_start = time.perf_counter()
        retrieved_docs = self._retrieve_documents(search_query=search_query, tenant_id=tenant_id)
        retrieval_ms = (time.perf_counter() - retrieval_start) * 1000

        # 9. Confidence detection (normal pass)
        confidence_level = self._determine_confidence(retrieved_docs)
        rescue_used = False

        # 9b. Accuracy rescue pass: retry once only when evidence is genuinely weak.
        if self._should_run_accuracy_rescue(confidence_level, retrieved_docs):
            rescue_start = time.perf_counter()
            rescue_docs = self._retrieve_documents(
                search_query=search_query,
                tenant_id=tenant_id,
                force_hyde=True,
                force_multi_query=True,
                retrieval_limit=max(self.retrieval_top_k, self.retrieval_top_k + 10),
            )
            rescue_ms = (time.perf_counter() - rescue_start) * 1000
            rescue_confidence = self._determine_confidence(rescue_docs)

            rank = {"low": 0, "medium": 1, "multi_source": 2, "high": 3}
            current_top = max((self._get_doc_relevance_score(doc) for doc in retrieved_docs), default=0.0)
            rescue_top = max((self._get_doc_relevance_score(doc) for doc in rescue_docs), default=0.0)

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
        top_score = max((self._get_doc_relevance_score(doc) for doc in retrieved_docs), default=0.0)
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
        context_parts = []
        for doc in retrieved_docs:
            score_label = ""
            if "rerank_score" in doc:
                score_label = f" [relevance: {doc['rerank_score']:.2f}]"
            neighbor_label = " [+ neighboring context]" if doc.get("has_neighbor_context") else ""
            context_parts.append(
                f"--- START OF SOURCE: {doc['filename']}{score_label}{neighbor_label} ---\n"
                f"{doc['content']}\n"
                f"--- END OF SOURCE: {doc['filename']} ---"
            )
        context_text = "\n\n".join(context_parts)

        # 11. Structured logging
        logger.info(f"Chat query | tenant={tenant_id} | session={session_id}")
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
            for doc in retrieved_docs:
                citations.append({
                    "filename": doc["filename"],
                    "content": doc["content"],
                    "similarity": doc.get("similarity", 0.0),
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

    def _should_run_accuracy_rescue(self, confidence_level: str, docs: list[dict]) -> bool:
        """
        Runs rescue pass only when first-pass evidence is genuinely weak.

        This preserves accuracy while avoiding unnecessary duplicate expensive retrieval.
        """
        if not docs:
            return True

        top_score = max((self._get_doc_relevance_score(doc) for doc in docs), default=0.0)

        if top_score < max(0.12, self.min_relevance_score_low):
            return True

        if len(docs) == 1 and top_score < max(0.25, self.min_relevance_score):
            return True

        if confidence_level == "low" and top_score < 0.25 and len(docs) < 2:
            return True

        return False

    # ══════════════════════════════════════════════
    # ✨ NEW: Advanced Retrieval Strategies
    # ══════════════════════════════════════════════

    def _build_search_queries(
        self,
        search_query: str,
        use_hyde: Optional[bool] = None,
        use_multi_query: Optional[bool] = None,
    ) -> list[str]:
        """
        Generates multiple search queries for improved retrieval.

        1. Original query (always included)
        2. HyDE — hypothetical document embedding
        3. Multi-query — LLM-generated variations
        """
        queries = [search_query]
        use_hyde = self.enable_hyde if use_hyde is None else use_hyde
        use_multi_query = self.enable_multi_query if use_multi_query is None else use_multi_query

        # HyDE: Generate a hypothetical answer and use IT for embedding search
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

        # Multi-Query: Generate alternative phrasings
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

    def _multi_query_search(
        self,
        queries: list[str],
        original_query: str,
        tenant_id: str,
        retrieval_limit: Optional[int] = None,
    ) -> list[dict]:
        """
        Searches with multiple queries and merges results with deduplication.

        Each query's results are combined; duplicates (same content) are removed,
        keeping the highest similarity score.
        """
        all_docs = {}  # key: content hash, value: doc dict
        search_limit = retrieval_limit or self.retrieval_top_k

        for query in queries:
            try:
                query_vector = self.embedder.embed_text([query])[0]
                docs = self.db.search_similar(
                    query_vector=query_vector,
                    query_text=original_query,  # Always use original for keyword search
                    tenant_id=tenant_id,
                    limit=search_limit,
                )
                for doc in docs:
                    # Deduplicate by content (keep highest similarity)
                    content_key = doc.get("content", "")[:100]
                    existing = all_docs.get(content_key)
                    if not existing or doc.get("similarity", 0) > existing.get("similarity", 0):
                        all_docs[content_key] = doc
            except Exception as e:
                logger.error(f"Search failed for query variant: {e}")

        merged = list(all_docs.values())
        logger.info(f"Multi-query search: {len(queries)} queries → {len(merged)} unique docs")
        return merged

    def _retrieve_documents(
        self,
        search_query: str,
        tenant_id: str,
        force_hyde: Optional[bool] = None,
        force_multi_query: Optional[bool] = None,
        retrieval_limit: Optional[int] = None,
    ) -> list[dict]:
        """Runs full retrieval stack and returns filtered/enriched documents."""
        search_queries = self._build_search_queries(
            search_query=search_query,
            use_hyde=force_hyde,
            use_multi_query=force_multi_query,
        )

        retrieved_docs = self._multi_query_search(
            queries=search_queries,
            original_query=search_query,
            tenant_id=tenant_id,
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

        retrieved_docs = self._dynamic_relevance_filter(retrieved_docs)

        if self.enable_neighbor_context and retrieved_docs:
            retrieved_docs = self._expand_with_neighbors(retrieved_docs, tenant_id)

        return retrieved_docs

    def _dynamic_relevance_filter(self, docs: list) -> list:
        """
        Filters docs by relevance score with dynamic threshold.

        If fewer than 2 docs survive the normal threshold, falls back to
        a lower threshold to avoid returning nothing on partial matches.
        """
        if not docs:
            return docs

        # First pass: normal threshold
        filtered = [
            doc for doc in docs
            if self._get_doc_relevance_score(doc) >= self.min_relevance_score
        ]

        # If we filtered too aggressively, try with lower threshold
        if len(filtered) < 2:
            filtered = [
                doc for doc in docs
                if self._get_doc_relevance_score(doc) >= self.min_relevance_score_low
            ]
            if len(filtered) > len(docs):
                filtered = docs  # Shouldn't happen, but safety check
            logger.info(
                f"Dynamic threshold: {self.min_relevance_score} → {self.min_relevance_score_low} "
                f"({len(docs)} → {len(filtered)} docs)"
            )
        else:
            filtered_count = len(docs) - len(filtered)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} low-relevance docs (threshold={self.min_relevance_score})")

        return filtered

    def _expand_with_neighbors(self, docs: list, tenant_id: str) -> list:
        """
        Expands retrieved chunks with neighboring context from the same document.

        For each matched chunk, fetches adjacent chunks from the same file
        and appends their content, giving the LLM more surrounding context.
        """
        expanded = []
        seen_filenames = set()

        for doc in docs:
            filename = doc.get("filename", "")

            # Only expand once per unique filename to avoid bloat
            if filename in seen_filenames or not filename:
                expanded.append(doc)
                continue

            seen_filenames.add(filename)

            try:
                neighbors = self.db.get_neighboring_chunks(
                    filename=filename,
                    content_snippet=doc.get("content", "")[:100],
                    tenant_id=tenant_id,
                    limit=5,
                )

                if neighbors and len(neighbors) > 1:
                    # Combine neighbor content (excluding the matched chunk itself)
                    neighbor_texts = []
                    for n in neighbors:
                        n_content = n.get("content", "")
                        if n_content and n_content[:100] != doc.get("content", "")[:100]:
                            neighbor_texts.append(n_content)

                    if neighbor_texts:
                        expanded_content = (
                            doc["content"] + "\n\n"
                            "[SURROUNDING CONTEXT FROM SAME DOCUMENT]\n" +
                            "\n---\n".join(neighbor_texts[:2])  # Max 2 neighbors
                        )
                        enriched_doc = {**doc, "content": expanded_content, "has_neighbor_context": True}
                        expanded.append(enriched_doc)
                        logger.debug(f"Expanded '{filename}' with {len(neighbor_texts[:2])} neighbor chunks")
                        continue

            except Exception as e:
                logger.warning(f"Neighbor expansion failed for '{filename}': {e}")

            expanded.append(doc)

        return expanded

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

    def _determine_confidence(self, docs: list) -> str:
        """
        Classifies retrieval confidence with multi-source detection.

        Returns: 'high', 'multi_source', 'medium', or 'low'
        """
        if not docs:
            return "low"

        scores = [self._get_doc_relevance_score(doc) for doc in docs]
        top_score = max(scores)
        unique_files = set(doc.get("filename", "") for doc in docs)

        # Multi-source: top docs come from different files with varying scores
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
                "## Direct Answer, ## Detailed Explanation, ## Evidence by Source, ## Gaps or Unknowns. "
                "In 'Evidence by Source', cite filenames from the context and map each major claim to at least one source."
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
5. SOURCE ISOLATION: The CONTEXT is divided by filenames (e.g., '--- START OF SOURCE: filename.pdf ---').
   - If the user asks about a specific document, ONLY use facts from that file's sections.
   - Sources with higher [relevance] scores are more likely to contain the answer — prioritize them.
   - Sections marked [+ neighboring context] provide surrounding context from the same document for better understanding.
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
