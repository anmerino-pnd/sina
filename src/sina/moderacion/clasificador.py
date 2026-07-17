"""
Clasificador de consultas vía Ollama (modelo chico DEDICADO, no el del agente).

- Salida estructurada real con `format=<json schema>` (mismo patrón que
  `vlm/ollama_vlm.py`) y validación contra el enum de etiquetas (MEJORA #2).
- Timeout + 1 reintento; cualquier falla cae a fail-open "relevante" con
  log — nunca propaga excepción ni tumba el request (MEJORA #4). Fail-open
  porque el dominio es de bajo riesgo y clasificador y agente comparten el
  mismo Ollama: si está caído, el agente fallará con su propio manejo; el
  pre-filtro determinista sigue atrapando lo obviamente inapropiado.
- Síncrono a propósito: el endpoint del chat es `def` y corre en el threadpool
  de FastAPI, así que este IO no bloquea el event loop (MEJORA #7).
- El mensaje y el historial viajan SERIALIZADOS COMO DATOS (JSON) dentro del
  mensaje `user`, nunca concatenados como instrucciones (MEJORA #8).
"""
from __future__ import annotations

import json
import logging
import re

from sina.config.app_settings import settings
from sina.config.prompt import moderacion_system_prompt

log = logging.getLogger(__name__)

ETIQUETAS = {"relevante", "irrelevante", "inapropiado"}
ETIQUETA_FALLBACK = "relevante"  # fail-open (ver docstring del módulo)

ETIQUETA_SCHEMA = {
    "type": "object",
    "properties": {"label": {"type": "string", "enum": sorted(ETIQUETAS)}},
    "required": ["label"],
}

# Turnos `user` del historial que ve el clasificador (contexto reciente).
_MAX_TURNOS_HISTORIAL = 5
_INTENTOS = 2  # 1 llamada + 1 reintento

_client = None
# Los modelos "pensantes" (qwen3.x) gastan MUCHO en razonamiento antes del JSON
# (medido: ~99 s con think vs ~2 s sin think para la misma etiqueta), así que se
# pide `think=False` siempre; si el modelo/servidor rechaza el parámetro, se
# apaga solo y se reintenta sin él.
_pasar_think = True


def _get_client():
    """Cliente Ollama perezoso y cacheado (mismo patrón que `agent/llm/factory.py`)."""
    global _client
    if _client is None:
        from ollama import Client

        _client = Client(
            host=settings.moderacion_host or settings.ollama_host,
            timeout=settings.moderacion_timeout_s,
        )
    return _client


def _turnos_usuario(historial: list[dict] | None) -> list[str]:
    """Últimos N contenidos del usuario (acepta claves rol/contenido o role/content)."""
    turnos = []
    for m in historial or []:
        rol = m.get("rol") or m.get("role")
        contenido = m.get("contenido") or m.get("content")
        if rol == "user" and isinstance(contenido, str) and contenido:
            turnos.append(contenido)
    return turnos[-_MAX_TURNOS_HISTORIAL:]


def _parsear_etiqueta(contenido: str | None) -> str | None:
    if not contenido:
        return None
    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError:
        # Con `format=` no debería pasar; por si un modelo envuelve en markdown.
        limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", contenido.strip())
        try:
            datos = json.loads(limpio)
        except json.JSONDecodeError:
            return None
    etiqueta = datos.get("label") if isinstance(datos, dict) else None
    if isinstance(etiqueta, str) and etiqueta.strip().lower() in ETIQUETAS:
        return etiqueta.strip().lower()
    return None


def clasificar(mensaje: str, historial: list[dict] | None) -> tuple[str, str]:
    """
    Clasifica el mensaje con el historial reciente como contexto.
    Devuelve `(etiqueta, origen)` con origen "llm" o "fallback"; jamás lanza.
    """
    # El contenido del usuario va como DATOS (JSON), no como instrucciones.
    entrada = json.dumps(
        {"historial_usuario": _turnos_usuario(historial), "mensaje_actual": mensaje},
        ensure_ascii=False,
    )
    messages = [
        {"role": "system", "content": moderacion_system_prompt},
        {"role": "user", "content": entrada},
    ]
    global _pasar_think
    for intento in range(1, _INTENTOS + 1):
        try:
            extra = {"think": False} if _pasar_think else {}
            resp = _get_client().chat(
                model=settings.moderacion_model,
                messages=messages,
                options={"temperature": 0},
                format=ETIQUETA_SCHEMA,
                # El modelo chico se queda cargado: con el keep_alive default de
                # Ollama (5 min) cada arranque en frío rebasa el timeout y toda
                # consulta tras un rato de inactividad caería al fallback.
                keep_alive="30m",
                **extra,
            )
            etiqueta = _parsear_etiqueta(getattr(resp.message, "content", None))
            if etiqueta is not None:
                return etiqueta, "llm"
            log.warning(
                "Clasificador devolvió salida fuera del enum (intento %d/%d).",
                intento, _INTENTOS,
            )
        except Exception as e:  # noqa: BLE001 — degradar, nunca tumbar el request
            if _pasar_think and "think" in str(e).lower():
                _pasar_think = False
                log.info("El modelo de moderación no acepta `think`; se omite.")
                continue
            log.warning(
                "Clasificador de moderación falló (intento %d/%d): %s",
                intento, _INTENTOS, e,
            )
    log.warning("Clasificador sin respuesta válida; fail-open a %r.", ETIQUETA_FALLBACK)
    return ETIQUETA_FALLBACK, "fallback"
