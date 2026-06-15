import os
import logging
from typing import List, Dict, Any, Optional
from sina.embedder.base import EmbeddingProvider
from sina.embedder.qwen_embedder import QwenHuggingFaceProvider

logger = logging.getLogger(__name__)

# Modelo open-source por defecto; intercambiable vía EMBEDDING_MODEL.
DEFAULT_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"


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
        model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
        logger.info("Inicializando embeddings con modelo '%s'...", model_name)
        _service = EmbeddingService(QwenHuggingFaceProvider(model_name=model_name))
    except Exception as e:
        logger.error("No se pudo inicializar el servicio de embeddings: %s", e)
        _service = None
    return _service


# --- PRUEBA DEL MÓDULO ---
if __name__ == "__main__":
    # Si quieres probarlo de forma aislada corriendo: python src/sina/processing/embeddings.py
    
    print("Iniciando prueba del motor de Embeddings...")
    try:
        # Inyectamos el proveedor Qwen al servicio
        motor = EmbeddingService(QwenHuggingFaceProvider())
        
        # Simulamos un producto extraído de Soriana
        vector = motor.vectorizar_supermercado(
            producto="Arroz Blanco Precocido Diamante 150 g",
            tienda="Soriana",
            precio=24.90
        )
        
        print("\n✅ ÉXITO!")
        print(f"Dimensiones del vector devuelto: {len(vector)}")
        print(f"Muestra (primeros 5 valores): {vector[:5]}")
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")