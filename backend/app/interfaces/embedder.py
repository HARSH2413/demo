from abc import ABC, abstractmethod
from typing import List

class IEmbedder(ABC):
    @abstractmethod
    def embed_text(self, text_chunks: List[str]) -> List[List[float]]:
        """
        Converts a list of text strings into a list of mathematical vectors.
        """
        pass