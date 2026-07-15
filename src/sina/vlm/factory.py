"""
Fábrica perezosa del proveedor de VLM.

Espeja `agent/llm/factory.py`: gated por `ENABLE_VLM`, instancia una sola vez,
cachea el resultado (incluido el fallo) y elige el proveedor según `VLM_PROVIDER`.
Devuelve `None` si el VLM está deshabilitado o no pudo inicializarse (el flujo de
extracción degrada con un error claro, no tumba el server).
"""
from __future__ import annotations

import logging

from sina.vlm.base import VLMProvider
from sina.config.app_settings import settings
from sina.config.credentials import ollama_api_key

log = logging.getLogger(__name__)

_provider: VLMProvider | None = None
_intentado: bool = False


def get_vlm_provider() -> VLMProvider | None:
    """Devuelve el proveedor de VLM configurado, o None si no está disponible."""
    global _provider, _intentado

    if not settings.enable_vlm:
        return None
    if _intentado:
        return _provider

    _intentado = True
    proveedor = settings.vlm_provider.strip().lower()
    try:
        if proveedor == "ollama":
            from sina.vlm.ollama_vlm import OllamaVLMProvider
            _provider = OllamaVLMProvider(
                modelo=settings.vlm_model,
                host=settings.vlm_host,
                api_key=ollama_api_key,
            )
        # elif proveedor == "gemini":  # hueco listo para el patrocinador
        #     from sina.vlm.gemini_vlm import GeminiVLMProvider
        #     _provider = GeminiVLMProvider(modelo=..., api_key=google_api_key)
        else:
            log.error("VLM_PROVIDER desconocido: %r", proveedor)
            _provider = None
    except Exception as e:  # noqa: BLE001 — la extracción degrada, no tumba el server
        log.error("No se pudo inicializar el proveedor de VLM (%s): %s", proveedor, e)
        _provider = None

    return _provider
