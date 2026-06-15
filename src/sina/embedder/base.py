from abc import ABC, abstractmethod
from typing import List


# --- 1. INTERFAZ ESTRATÉGICA ---
class EmbeddingProvider(ABC):
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Convierte un texto descriptivo en un vector matemático."""
        pass

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Vectoriza varios textos. Implementación por defecto: itera
        `generate_embedding`. Los proveedores que soporten batch real
        (p. ej. SentenceTransformer) deberían sobreescribirla.
        """
        return [self.generate_embedding(t) for t in texts]