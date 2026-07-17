"""
Provider de embeddings vía Ollama (API /api/embed).

Mucho más ligero de operar que el provider de HuggingFace (no requiere torch ni
descargar pesos con sentence-transformers): basta `ollama pull qwen3-embedding:8b`.
Mismo modelo Qwen3-Embedding-8B, servido por el Ollama que ya usa el chat/VLM.
"""
from __future__ import annotations

import logging
from typing import List

from sina.embedder.base import EmbeddingProvider

log = logging.getLogger(__name__)


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "qwen3-embedding:8b", host: str | None = None):
        # Import perezoso: no cargar el cliente si los embeddings están apagados.
        from ollama import Client  # noqa: PLC0415

        from sina.config.app_settings import settings  # noqa: PLC0415

        self.model_name = model_name
        self.client = Client(host=host or settings.ollama_host)

    def generate_embedding(self, text: str) -> List[float]:
        return self.generate_embeddings([text])[0]

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """La API embed de Ollama acepta lista → un solo request por lote."""
        if not texts:
            return []
        respuesta = self.client.embed(model=self.model_name, input=texts)
        return [list(v) for v in respuesta["embeddings"]]
