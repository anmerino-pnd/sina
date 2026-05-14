from abc import ABC, abstractmethod
from typing import List


# --- 1. INTERFAZ ESTRATÉGICA ---
class EmbeddingProvider(ABC):
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Convierte un texto descriptivo en un vector matemático."""
        pass