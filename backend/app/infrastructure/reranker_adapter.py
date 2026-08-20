"""
FastEmbed Reranker Adapter — local cross-encoder re-ranking via ONNX.

Uses a tiny (~23MB) MiniLM cross-encoder model that runs locally with zero
API calls. Dramatically improves retrieval accuracy by scoring each
(query, document) pair with full cross-attention.

To swap models, change RERANKER_MODEL_NAME in your .env:
    RERANKER_MODEL_NAME=Xenova/ms-marco-MiniLM-L-12-v2
"""
from fastembed.rerank.cross_encoder import TextCrossEncoder
from app.interfaces.reranker import IReranker
from app.core.logger import logger


class FastEmbedRerankerAdapter(IReranker):
    def __init__(self, model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2"):
        self.model = TextCrossEncoder(model_name=model_name)
        logger.info(f"Reranker adapter initialized | model={model_name}")

    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """
        Re-ranks documents using cross-encoder scores.

        Scores each (query, doc.content) pair, sorts by score descending,
        and returns the top_k most relevant documents.
        """
        if not documents:
            return []

        # Extract text content for scoring
        passages = [doc.get("content", "") for doc in documents]

        # Score all (query, passage) pairs
        scores = list(self.model.rerank(query, passages))

        # Attach scores back to documents (handle both float and score-object return types)
        scored_docs = []
        for score_entry, doc in zip(scores, documents):
            if isinstance(score_entry, float):
                score = score_entry
            else:
                score = float(score_entry.score)
            enriched = {**doc, "rerank_score": score}
            scored_docs.append(enriched)

        # Sort by cross-encoder score (highest = most relevant)
        scored_docs.sort(key=lambda d: d["rerank_score"], reverse=True)

        logger.debug(
            f"Re-ranked {len(documents)}→{min(top_k, len(scored_docs))} docs | "
            f"top_score={scored_docs[0]['rerank_score']:.4f}" if scored_docs else "no docs"
        )

        return scored_docs[:top_k]
