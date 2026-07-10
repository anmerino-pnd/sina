"""
Fábrica perezosa del proveedor de LLM.

Espeja `sina/embedder/embeddings.py:get_embedding_service`: gated por
`ENABLE_CHAT`, instancia una sola vez, cachea el resultado (incluido el fallo) y
elige el proveedor según `LLM_PROVIDER`. Devuelve `None` si el chat está
deshabilitado o si el proveedor no pudo inicializarse.
"""
from __future__ import annotations

import logging

from sina.agent.llm.base import LLMProvider
from sina.config.app_settings import settings
from sina.config.credentials import ollama_api_key

log = logging.getLogger(__name__)

_provider: LLMProvider | None = None
_intentado: bool = False


def get_llm_provider() -> LLMProvider | None:
    """Devuelve el proveedor de LLM configurado, o None si no está disponible."""
    global _provider, _intentado

    if not settings.enable_chat:
        return None
    if _intentado:
        return _provider

    _intentado = True
    proveedor = settings.llm_provider.strip().lower()
    try:
        if proveedor == "ollama":
            from sina.agent.llm.ollama_provider import OllamaProvider
            _provider = OllamaProvider(
                modelo=settings.ollama_model,
                host=settings.ollama_host,
                temperatura=settings.llm_temperature,
                api_key=ollama_api_key,
            )
        # elif proveedor == "gemini":  # hueco listo para el patrocinador
        #     from sina.agent.llm.gemini_provider import GeminiProvider
        #     _provider = GeminiProvider(...)
        else:
            log.error("LLM_PROVIDER desconocido: %r", proveedor)
            _provider = None
    except Exception as e:  # noqa: BLE001 — el chat degrada, no tumba el server
        log.error("No se pudo inicializar el proveedor de LLM (%s): %s", proveedor, e)
        _provider = None

    return _provider
