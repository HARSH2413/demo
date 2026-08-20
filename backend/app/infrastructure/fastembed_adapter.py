"""
FastEmbed Adapter — config-driven model selection.

To swap embedding models, change EMBEDDING_MODEL_NAME in your .env:
    EMBEDDING_MODEL_NAME=BAAI/bge-large-en-v1.5
"""
from typing import List
from fastembed import TextEmbedding
from app.interfaces.embedder import IEmbedder
from app.core.logger import logger


class FastEmbedAdapter(IEmbedder):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model = TextEmbedding(model_name=model_name)
        logger.info(f"FastEmbed adapter initialized | model={model_name}")

    def embed_text(self, text_chunks: List[str]) -> List[List[float]]:
        embeddings = list(self.model.embed(text_chunks))
        return [embedding.tolist() for embedding in embeddings]