from sina.embedder.base import EmbeddingProvider
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenHuggingFaceProvider(EmbeddingProvider):

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Embedding-8B",
    ):
        logger.info(f"Cargando modelo {model_name}...")

        try:
            from sentence_transformers import SentenceTransformer
            import torch

            self.device = "cuda" if torch.cuda.is_available() else "cpu"

            self.model = SentenceTransformer(
                model_name,
                device=self.device
            )

            logger.info(f"Modelo cargado en {self.device.upper()}")

        except ImportError:
            raise ImportError(
                "Faltan dependencias. Ejecuta:\n"
                "uv add sentence-transformers torch torchvision"
            )

    def generate_embedding(self, text: str) -> List[float]:

        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        return embedding.tolist()

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch real: una sola llamada a `encode` para toda la lista."""
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return [e.tolist() for e in embeddings]