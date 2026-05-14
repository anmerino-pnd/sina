import logging
from typing import List
from sina.embedder.base import EmbeddingProvider
from sina.embedder.qwen_embedder import QwenHuggingFaceProvider

# Configuración básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 3. SERVICIO PRINCIPAL (El que usarás en tu código) ---
class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider
        
    def vectorizar_supermercado(self, producto: str, tienda: str, precio: float) -> List[float]:
        """
        Prepara el texto del producto para ser vectorizado.
        El formato de este texto es CRUCIAL para que RAG funcione bien después.
        """
        # Formato semántico: Ayuda al modelo a entender el contexto
        texto_semantico = f"Producto: {producto}. Se vende en el supermercado {tienda} a un precio de ${precio:.2f} pesos."
        
        logger.info(f"Generando vector para: '{producto}'...")
        return self.provider.generate_embedding(texto_semantico)


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