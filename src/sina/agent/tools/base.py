"""
Infraestructura de tools: definición, contexto por request y registro.

Cada `Tool` envuelve una función Python (que consulta los repositorios) con su
esquema JSON para el LLM. Las tools se construyen por request cerrando sobre un
`ContextoConsulta` (ubicación del usuario), de modo que:
  - si el LLM omite `municipio`/`estado`, se usa el del contexto;
  - el `lat/lng` del usuario se INYECTA desde el contexto (el LLM nunca lo rellena,
    así no puede alucinar coordenadas).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from sina.agent.llm.base import ToolCall

log = logging.getLogger(__name__)


@dataclass
class ContextoConsulta:
    """Contexto de la conversación disponible para las tools (no visible al LLM)."""
    estado: str | None = None
    municipio: str | None = None
    localidad: str | None = None
    lat: float | None = None
    lng: float | None = None

    @property
    def tiene_coordenadas(self) -> bool:
        return self.lat is not None and self.lng is not None


@dataclass
class Tool:
    nombre: str
    descripcion: str
    parametros: dict[str, Any]           # JSON Schema (propiedades + required)
    fn: Callable[..., Any]               # ejecuta la consulta; devuelve algo serializable

    def a_esquema_ollama(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.nombre,
                "description": self.descripcion,
                "parameters": {
                    "type": "object",
                    "properties": self.parametros.get("properties", {}),
                    "required": self.parametros.get("required", []),
                },
            },
        }


@dataclass
class RegistroTools:
    tools: dict[str, Tool] = field(default_factory=dict)

    def registrar(self, tool: Tool) -> None:
        self.tools[tool.nombre] = tool

    def esquemas(self) -> list[dict[str, Any]]:
        return [t.a_esquema_ollama() for t in self.tools.values()]

    def ejecutar(self, llamada: ToolCall) -> str:
        """Ejecuta una tool y devuelve su resultado como JSON (string) para el LLM."""
        tool = self.tools.get(llamada.nombre)
        if tool is None:
            return json.dumps({"error": f"tool desconocida: {llamada.nombre}"}, ensure_ascii=False)
        try:
            resultado = tool.fn(**(llamada.argumentos or {}))
        except TypeError as e:
            # Argumentos inválidos del modelo → mensaje corregible, no excepción fatal.
            return json.dumps({"error": f"argumentos inválidos: {e}"}, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            log.exception("Error ejecutando tool %s", llamada.nombre)
            return json.dumps({"error": f"fallo en {llamada.nombre}: {e}"}, ensure_ascii=False)
        return json.dumps(resultado, ensure_ascii=False, default=str)
