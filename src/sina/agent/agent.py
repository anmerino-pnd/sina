"""
El agente de ahorro: orquesta LLM + tools en un grafo y transmite en streaming.

`responder_stream` recorre el grafo (`agente ↔ tools`) cediendo eventos:
  - `token`  : fragmento de la respuesta final (para SSE en vivo)
  - `paso`   : una tool en ejecución (para "usando …")
  - `done`   : respuesta final completa + telemetría agregada
  - `error`  : algo falló

Diseño síncrono (ver `llm/base.py`): el endpoint lo consume desde el threadpool.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

from sina.agent.graph import END, Grafo
from sina.agent.llm.base import LLMProvider, LLMUso
from sina.agent.tools.base import ContextoConsulta
from sina.agent.tools.registry import construir_registro
from sina.config.app_settings import settings
from sina.config.timezone import get_mexico_now

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres SINA, un asistente que ayuda a familias mexicanas a gastar menos en \
gasolina, gas LP y despensa. Respondes en español claro y sencillo (público de baja \
alfabetización digital), en pocas frases.

Reglas:
- Usa SIEMPRE las herramientas para obtener precios; NUNCA inventes precios ni estaciones.
- Si no sabes el municipio del usuario, pídeselo antes de buscar.
- Para gasolina "cerca de mí" usa ordenar_por="cercania" (solo funciona si el usuario compartió su ubicación).
- El Gas LP se consulta por localidad: si no la sabes, usa listar_localidades_gas_lp.
- Al terminar, responde en lenguaje natural con los datos que devolvieron las herramientas \
(nombre del lugar, precio en pesos). No muestres JSON."""


@dataclass
class Evento:
    tipo: str            # "token" | "paso" | "done" | "error"
    dato: Any


@dataclass
class _Telemetria:
    usos: list[LLMUso] = field(default_factory=list)
    tool_timings: list[dict] = field(default_factory=list)
    llm_ms: float = 0.0
    tools_ms: float = 0.0
    iteraciones: int = 0


def _msg_historial(historial: list[dict] | None) -> list[dict]:
    salida: list[dict] = []
    for m in historial or []:
        rol = m.get("rol") or m.get("role")
        contenido = m.get("contenido") or m.get("content")
        if rol in ("user", "assistant") and contenido:
            salida.append({"role": rol, "content": contenido})
    return salida


def responder_stream(
    mensaje: str,
    contexto: ContextoConsulta,
    historial: list[dict] | None,
    provider: LLMProvider,
) -> Iterator[Evento]:
    registro = construir_registro(contexto)
    fecha_pregunta = get_mexico_now()
    t_inicio = time.perf_counter()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += _msg_historial(historial)
    messages.append({"role": "user", "content": mensaje})

    tel = _Telemetria()
    estado: dict[str, Any] = {
        "messages": messages,
        "provider": provider,
        "registro": registro,
        "tool_calls": [],
        "iteraciones": 0,
        "respuesta": "",
        "max_iters": settings.llm_max_iters,
        "tel": tel,
    }

    def nodo_agente(state: dict) -> Iterator[Evento]:
        prov: LLMProvider = state["provider"]
        reg = state["registro"]
        # En la última iteración permitida no ofrecemos tools → el modelo debe responder.
        ofrecer_tools = state["iteraciones"] < state["max_iters"]
        esquemas = reg.esquemas() if ofrecer_tools else None

        t0 = time.perf_counter()
        contenido = ""
        tool_calls: list = []
        uso: LLMUso | None = None
        try:
            for delta in prov.chat_stream(state["messages"], esquemas):
                if delta.texto:
                    contenido += delta.texto
                    yield Evento("token", delta.texto)
                if delta.tool_calls:
                    tool_calls.extend(delta.tool_calls)
                if delta.uso is not None:
                    uso = delta.uso
        except Exception as e:  # noqa: BLE001
            log.exception("Error en el proveedor de LLM")
            yield Evento("error", {"detalle": f"error del modelo: {e}"})
            state["respuesta"] = state.get("respuesta") or ""
            return {"tool_calls": []}

        state["tel"].llm_ms += (time.perf_counter() - t0) * 1000
        if uso is not None:
            state["tel"].usos.append(uso)

        asistente: dict[str, Any] = {"role": "assistant", "content": contenido}
        if tool_calls:
            asistente["tool_calls"] = [
                {"function": {"name": tc.nombre, "arguments": tc.argumentos}} for tc in tool_calls
            ]
        else:
            state["respuesta"] = contenido
        state["messages"].append(asistente)
        return {"tool_calls": tool_calls}

    def router(state: dict) -> str:
        if state.get("tool_calls") and state["iteraciones"] < state["max_iters"]:
            return "tools"
        return END

    def nodo_tools(state: dict) -> Iterator[Evento]:
        reg = state["registro"]
        t0 = time.perf_counter()
        for tc in state["tool_calls"]:
            yield Evento("paso", {"tool": tc.nombre, "argumentos": tc.argumentos})
            tt0 = time.perf_counter()
            resultado = reg.ejecutar(tc)
            state["tel"].tool_timings.append(
                {"tool": tc.nombre, "ms": round((time.perf_counter() - tt0) * 1000, 1)}
            )
            state["messages"].append(
                {"role": "tool", "tool_name": tc.nombre, "content": resultado}
            )
        state["tel"].tools_ms += (time.perf_counter() - t0) * 1000
        return {"iteraciones": state["iteraciones"] + 1, "tool_calls": []}

    grafo = Grafo()
    grafo.add_node("agente", nodo_agente)
    grafo.add_node("tools", nodo_tools)
    grafo.set_entry("agente")
    grafo.add_conditional_edges("agente", router, {"tools": "tools", END: END})
    grafo.add_edge("tools", "agente")

    hubo_error = False
    for evento in grafo.stream(estado):
        if evento.tipo == "error":
            hubo_error = True
        yield evento

    respuesta = (estado.get("respuesta") or "").strip()
    if not respuesta and not hubo_error:
        respuesta = "No pude encontrar esa información ahora mismo. ¿Puedes darme más detalles?"

    metadatos = _agregar_metadatos(tel, fecha_pregunta, t_inicio)
    yield Evento("done", {"respuesta": respuesta, "metadatos": metadatos})


def _agregar_metadatos(tel: _Telemetria, fecha_pregunta, t_inicio: float) -> dict[str, Any]:
    input_tokens = sum(u.input_tokens for u in tel.usos)
    output_tokens = sum(u.output_tokens for u in tel.usos)
    cached = [u.cached_tokens for u in tel.usos if u.cached_tokens is not None]
    modelo = tel.usos[-1].modelo if tel.usos else settings.ollama_model
    # tokens/seg del último turno con salida (el de la respuesta), más representativo.
    tps = next((u.tokens_por_segundo for u in reversed(tel.usos)
                if u.tokens_por_segundo), None)
    total_ms = (time.perf_counter() - t_inicio) * 1000
    return {
        "modelo": modelo,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": sum(cached) if cached else None,
        "tokens_por_segundo": round(tps, 1) if tps else None,
        "duracion_ms": round(total_ms, 1),
        "fecha_pregunta": fecha_pregunta.isoformat(),
        "tool_timings": tel.tool_timings,
        "phase_timings": {
            "llm_ms": round(tel.llm_ms, 1),
            "tools_ms": round(tel.tools_ms, 1),
            "total_ms": round(total_ms, 1),
            "iteraciones": tel.iteraciones if tel.iteraciones else len(tel.usos),
        },
    }
