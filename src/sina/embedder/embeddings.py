import os
import logging
from typing import List, Dict, Any, Optional
from sina.embedder.base import EmbeddingProvider

logger = logging.getLogger(__name__)

# Provider por defecto y modelo por provider; intercambiables vía
# EMBEDDING_PROVIDER / EMBEDDING_MODEL. "ollama" es el default: mismo servidor
# que el chat/VLM, sin torch (solo requiere `ollama pull qwen3-embedding:8b`).
DEFAULT_EMBEDDING_PROVIDER = "ollama"
DEFAULT_MODELS = {
    "ollama": "qwen3-embedding:8b",
    "huggingface": "Qwen/Qwen3-Embedding-8B",
}


# --- 3. SERVICIO PRINCIPAL (El que usarás en tu código) ---
class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider

    def _texto_producto(self, producto: str, tienda: str, precio: float) -> str:
        """
        Formato semántico del producto. Es CRUCIAL que el texto usado al indexar
        sea el mismo estilo que el de las consultas para que RAG funcione bien.
        """
        return (
            f"Producto: {producto}. Se vende en el supermercado {tienda} "
            f"a un precio de ${precio:.2f} pesos."
        )

    def vectorizar_supermercado(self, producto: str, tienda: str, precio: float) -> List[float]:
        return self.provider.generate_embedding(self._texto_producto(producto, tienda, precio))

    def vectorizar_productos(self, productos: List[Dict[str, Any]]) -> List[List[float]]:
        """Vectoriza una lista de productos (dicts con producto/tienda/precio) en batch."""
        textos = [
            self._texto_producto(
                p.get("producto", ""), p.get("tienda", ""), float(p.get("precio", 0.0))
            )
            for p in productos
        ]
        return self.provider.generate_embeddings(textos)

    def vectorizar_consulta(self, texto: str) -> List[float]:
        """Vectoriza el texto de una consulta de usuario (para búsqueda semántica)."""
        return self.provider.generate_embedding(texto)


# --- FACTORY (singleton perezoso, controlado por ENABLE_EMBEDDINGS) ---
_service: Optional[EmbeddingService] = None
_service_intentado = False


def _embeddings_habilitado() -> bool:
    return os.getenv("ENABLE_EMBEDDINGS", "0").strip().lower() in ("1", "true", "yes", "on")


def get_embedding_service() -> Optional[EmbeddingService]:
    """
    Devuelve un `EmbeddingService` cacheado, o `None` si los embeddings están
    deshabilitados (ENABLE_EMBEDDINGS) o si el modelo no se pudo cargar.

    El modelo es pesado, así que se carga de forma perezosa una sola vez.
    """
    global _service, _service_intentado

    if not _embeddings_habilitado():
        return None

    if _service_intentado:
        return _service

    _service_intentado = True
    try:
        proveedor = os.getenv("EMBEDDING_PROVIDER", DEFAULT_EMBEDDING_PROVIDER).strip().lower()
        model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_MODELS.get(proveedor, ""))
        logger.info("Inicializando embeddings: provider '%s', modelo '%s'...", proveedor, model_name)
        _service = EmbeddingService(_construir_provider(proveedor, model_name))
    except Exception as e:
        logger.error("No se pudo inicializar el servicio de embeddings: %s", e)
        _service = None
    return _service


def _construir_provider(proveedor: str, model_name: str) -> EmbeddingProvider:
    """Imports perezosos: cada provider carga sus dependencias solo si se elige."""
    if proveedor == "ollama":
        from sina.embedder.ollama_embedder import OllamaEmbeddingProvider
        return OllamaEmbeddingProvider(model_name=model_name)
    if proveedor == "huggingface":
        from sina.embedder.qwen_embedder import QwenHuggingFaceProvider
        return QwenHuggingFaceProvider(model_name=model_name)
    raise ValueError(f"EMBEDDING_PROVIDER desconocido: '{proveedor}' (usa 'ollama' o 'huggingface')")


# --- PRUEBA DEL MÓDULO ---
if __name__ == "__main__":
    # Prueba aislada: ENABLE_EMBEDDINGS=1 uv run python -m sina.embedder.embeddings
    # (respeta EMBEDDING_PROVIDER / EMBEDDING_MODEL del entorno).
    print("Iniciando prueba del motor de Embeddings...")
    motor = get_embedding_service()
    if motor is None:
        print("Servicio deshabilitado o no inicializable (revisa ENABLE_EMBEDDINGS y el provider).")
    else:
        vector = motor.vectorizar_supermercado(
            producto="Arroz Blanco Precocido Diamante 150 g",
            tienda="Soriana",
            precio=24.90,
        )
        print(f"Dimensiones del vector devuelto: {len(vector)}")
        print(f"Muestra (primeros 5 valores): {vector[:5]}")