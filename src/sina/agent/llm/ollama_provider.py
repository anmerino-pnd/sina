"""
Proveedor de LLM sobre Ollama (open-source, local).

Reutiliza el paquete `ollama` que ya usaba `sina/ollama/extract_flyer_text.py`.
Soporta tool-calling nativo (`ollama.chat(..., tools=[...])`) y streaming
(`stream=True`), y arma la telemetría (`LLMUso`) desde los contadores que Ollama
devuelve en el chunk final (`prompt_eval_count`, `eval_count`, `eval_duration`).
"""
from __future__ import annotations

import logging
from typing import Any, Iterator

from sina.agent.llm.base import LLMProvider, LLMDelta, LLMUso, ToolCall

log = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        modelo: str,
        host: str = "http://localhost:11434",
        temperatura: float = 0.2,
        api_key: str = "",
    ) -> None:
        # Import perezoso para no acoplar el arranque a ollama.
        from ollama import Client

        self.modelo = modelo
        self.temperatura = temperatura
        if api_key:
            # Modo "cloud" (mismo patrón que extract_flyer_text.py).
            self._client = Client(host=host, headers={"Authorization": f"Bearer {api_key}"})
        else:
            self._client = Client(host=host)

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[LLMDelta]:
        stream = self._client.chat(
            model=self.modelo,
            messages=messages,
            tools=tools or None,
            stream=True,
            options={"temperature": self.temperatura},
        )

        idx = 0
        for chunk in stream:
            msg = getattr(chunk, "message", None)

            # Fragmento de texto (respuesta al usuario).
            contenido = getattr(msg, "content", "") if msg else ""
            if contenido:
                yield LLMDelta(texto=contenido)

            # Tool-calls (turno de tools). Ollama los entrega en un chunk, con
            # content vacío; el modelo no mezcla texto de usuario con tool_calls.
            tcs = getattr(msg, "tool_calls", None) if msg else None
            if tcs:
                llamadas: list[ToolCall] = []
                for tc in tcs:
                    fn = tc.function
                    args = fn.arguments
                    if isinstance(args, str):
                        import json
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    llamadas.append(
                        ToolCall(id=f"call_{idx}", nombre=fn.name, argumentos=dict(args or {}))
                    )
                    idx += 1
                yield LLMDelta(tool_calls=llamadas)

            # Chunk final: telemetría.
            if getattr(chunk, "done", False):
                yield LLMDelta(uso=self._armar_uso(chunk), fin=True)

    def _armar_uso(self, chunk: Any) -> LLMUso:
        input_tokens = int(getattr(chunk, "prompt_eval_count", 0) or 0)
        output_tokens = int(getattr(chunk, "eval_count", 0) or 0)
        total_ns = int(getattr(chunk, "total_duration", 0) or 0)
        eval_ns = int(getattr(chunk, "eval_duration", 0) or 0)
        tps: float | None = None
        if eval_ns > 0 and output_tokens > 0:
            tps = output_tokens / (eval_ns / 1e9)
        return LLMUso(
            modelo=self.modelo,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=None,  # Ollama no lo expone; un GeminiProvider sí lo hará.
            duracion_ms=total_ns / 1e6,
            tokens_por_segundo=tps,
        )
