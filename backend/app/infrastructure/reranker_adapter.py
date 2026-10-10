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
import math


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
        passages = []
        for doc in documents:
            meta = doc.get("metadata") or {}
            context_header = meta.get("context_header", "")
            content = doc.get("content", "")
            if context_header:
                passages.append(f"{context_header}\n\n{content}")
            else:
                passages.append(content)

        # Score all (query, passage) pairs
        scores = list(self.model.rerank(query, passages))

        # Attach scores back to documents (handle both float and score-object return types)
        scored_docs = []
        for score_entry, doc in zip(scores, documents):
            if isinstance(score_entry, float):
                raw_score = score_entry
            else:
                raw_score = float(getattr(score_entry, 'score', score_entry))
            
            # MiniLM models output raw logits, which can be negative. 
            # Apply a sigmoid function to normalize to a probability [0.0, 1.0] 
            # so it works cleanly with our relevance thresholds.
            normalized_score = 1.0 / (1.0 + math.exp(-raw_score))
            
            enriched = {**doc, "rerank_score": normalized_score}
            scored_docs.append(enriched)

        # Sort by cross-encoder score (highest = most relevant)
        scored_docs.sort(key=lambda d: d["rerank_score"], reverse=True)

        logger.debug(
            f"Re-ranked {len(documents)}→{min(top_k, len(scored_docs))} docs | "
            f"top_score={scored_docs[0]['rerank_score']:.4f}" if scored_docs else "no docs"
        )

        return scored_docs[:top_k]

    def score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]:
        if not pairs:
            return []
            
        # Batch score all pairs via underlying model
        try:
            raw_scores = list(self.model.model.rerank_pairs(pairs))
        except AttributeError:
            # Fallback if the internal API changes
            raw_scores = []
            for q, p in pairs:
                res = list(self.model.rerank(q, [p]))
                if res:
                    s = res[0]
                    raw_scores.append(s if isinstance(s, float) else float(getattr(s, 'score', s)))
                else:
                    raw_scores.append(0.0)
                    
        # Apply sigmoid normalization
        scores = []
        for raw_score in raw_scores:
            scores.append(1.0 / (1.0 + math.exp(-raw_score)))
            
        return scores
