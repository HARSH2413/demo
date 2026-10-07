"""
FastEmbed Adapter — config-driven model selection.

"""
from typing import List
from fastembed import TextEmbedding
from app.interfaces.embedder import IEmbedder
from app.core.logger import logger
from app.core.cache import global_embedding_cache


class FastEmbedAdapter(IEmbedder):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model = TextEmbedding(model_name=model_name)
        self.cache = global_embedding_cache
        logger.info(f"FastEmbed adapter initialized | model={model_name}")

    def embed_text(self, text_chunks: List[str]) -> List[List[float]]:
        results = []
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(text_chunks):
            cached = self.cache.get_embedding(text)
            if cached:
                results.append(cached)
            else:
                results.append(None)
                uncached_indices.append(i)
                uncached_texts.append(text)
                
        if uncached_texts:
            new_embeddings = list(self.model.embed(uncached_texts))
            for idx, emb, txt in zip(uncached_indices, new_embeddings, uncached_texts):
                emb_list = emb.tolist()
                results[idx] = emb_list
                self.cache.set_embedding(txt, emb_list)
                
        return results