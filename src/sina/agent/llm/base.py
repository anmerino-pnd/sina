"""
Abstracción del proveedor de LLM (Fase 3).

Espeja el patrón de `sina/embedder/base.py`: una clase abstracta que fija el
contrato, para que hoy exista `OllamaProvider` (open-source local) y mañana un
patrocinador solo tenga que escribir, p. ej., `GeminiProvider(LLMProvider)` con
la misma firma y reciba exactamente las mismas tools.

El contrato es SÍNCRONO a propósito: las tools consultan SQLAlchemy síncrono y
`ollama.chat` es síncrono; el endpoint corre en el threadpool de FastAPI (`def`).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class ToolCall:
    """Una llamada a tool solicitada por el modelo."""
    id: str
    nombre: str
    argumentos: dict[str, Any]


@dataclass
class LLMUso:
    """Telemetría normalizada de una generación (independiente del proveedor)."""
    modelo: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int | None = None  # None si el proveedor no lo expone (Ollama)
    duracion_ms: float = 0.0
    tokens_por_segundo: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "modelo": self.modelo,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "duracion_ms": round(self.duracion_ms, 1),
            "tokens_por_segundo": (
                round(self.tokens_por_segundo, 1)
                if self.tokens_por_segundo is not None else None
            ),
        }


@dataclass
class LLMDelta:
    """Un evento del stream de generación."""
    texto: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    uso: LLMUso | None = None
    fin: bool = False


class LLMProvider(ABC):
    """Contrato mínimo de un proveedor de LLM con tool-calling."""

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[LLMDelta]:
        """
        Genera en streaming. Cede `LLMDelta` con:
          - `texto`: fragmento de contenido (respuesta al usuario), o
          - `tool_calls`: lista de tools que el modelo quiere ejecutar (turno de tools),
        y un delta final con `fin=True` y `uso` (telemetría) poblado.
        """
        raise NotImplementedError

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[ToolCall], LLMUso]:
        """
        Variante no-stream (útil para pruebas): drena `chat_stream` y agrega.
        """
        texto = ""
        tool_calls: list[ToolCall] = []
        uso: LLMUso | None = None
        for delta in self.chat_stream(messages, tools):
            texto += delta.texto
            if delta.tool_calls:
                tool_calls.extend(delta.tool_calls)
            if delta.uso is not None:
                uso = delta.uso
        return texto, tool_calls, uso or LLMUso(modelo="desconocido")
