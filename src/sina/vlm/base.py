"""
Proveedor de VLM (Vision-Language Model) para extraer datos estructurados de
imágenes de flyers. Espeja el patrón de `agent/llm/base.py`: una ABC con DTOs
normalizados para que cambiar de proveedor (open-source local ↔ patrocinado en la
nube) no filtre tipos del vendor al resto del sistema.

Hoy: `OllamaVLMProvider` (visión local vía Ollama). Mañana un patrocinador puede
añadir `GeminiVLMProvider(VLMProvider)` con la MISMA firma y recibir el mismo
prompt/schema, sin tocar el pipeline de extracción ni el anotador.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VLMUso:
    """Telemetría normalizada de una extracción (para medir/optimizar)."""
    modelo: str
    input_tokens: int = 0
    output_tokens: int = 0
    duracion_ms: float = 0.0


@dataclass
class VLMResultado:
    """Salida de una extracción: JSON ya parseado + telemetría opcional."""
    datos: dict
    uso: VLMUso | None = None


class VLMProvider(ABC):
    @abstractmethod
    def extraer(
        self,
        imagen_path: str,
        prompt: str,
        formato: dict | None = None,
    ) -> VLMResultado:
        """
        Corre el modelo de visión sobre `imagen_path` con `prompt` de sistema y,
        si el proveedor lo soporta, `formato` como JSON Schema para forzar salida
        estructurada. Devuelve un `VLMResultado` con el JSON parseado en `datos`.
        """
        ...
