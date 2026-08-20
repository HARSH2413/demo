"""
Query Rewriter — resolves multi-turn context into standalone search queries.

When a user asks "What about their education?" after "Tell me about Harsh",
the embedding search would fail because "their education" has no context.
This service rewrites follow-ups into self-contained queries:
    → "What is Harsh's educational background?"

Uses a single, fast LLM call — adds ~50ms on Groq.
Can be toggled off via ENABLE_QUERY_REWRITE=false in .env.
"""
from app.interfaces.llm import ILLM
from app.core.logger import logger

REWRITE_SYSTEM_PROMPT = """You are a search query rewriter for a document retrieval system.

YOUR TASK:
Given a conversation history and a follow-up question, rewrite the follow-up into a STANDALONE search query that includes all necessary context from the conversation.

RULES:
1. Resolve all pronouns (he, she, they, it, this, that) to their specific referents from the conversation.
2. Include key entities and topics from the conversation that the follow-up refers to.
3. Output ONLY the rewritten query — no explanation, no quotes, no preamble.
4. If the follow-up is already self-contained, return it as-is.
5. Keep the query concise and search-friendly (under 50 words).

EXAMPLES:
History: "Tell me about Harsh's work experience"
Follow-up: "What about his education?"
Output: What is Harsh's educational background and education history?

History: "What products does Acme Corp sell?"
Follow-up: "How much do they cost?"
Output: What are the prices of Acme Corp's products?"""


class QueryRewriter:
    def __init__(self, llm: ILLM):
        self.llm = llm

    def rewrite(self, question: str, chat_history: list) -> str:
        """
        Rewrites a follow-up question into a standalone search query.

        If there's no chat history, returns the original question unchanged.
        """
        # No history → nothing to resolve
        if not chat_history:
            return question

        # Build conversation context from last 4 messages
        recent_history = chat_history[-4:]
        history_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}" for msg in recent_history
        )

        user_prompt = f"""CONVERSATION HISTORY:
{history_text}

FOLLOW-UP QUESTION: {question}

REWRITTEN STANDALONE QUERY:"""

        try:
            rewritten = self.llm.generate_response(
                system_prompt=REWRITE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            rewritten = rewritten.strip().strip('"').strip("'")

            if rewritten and len(rewritten) < 500:  # sanity check
                logger.info(f"Rewritten query: '{question}' → '{rewritten}'")
                return rewritten
            else:
                logger.warning(f"Query rewriter returned invalid output, using original")
                return question

        except Exception as e:
            logger.warning(f"Query rewriting failed, using original question: {e}")
            return question
