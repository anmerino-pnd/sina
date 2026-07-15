"""
Proveedor de VLM sobre Ollama (visión, open-source local; adaptable a la nube).

Reutiliza el paquete `ollama`. A diferencia del extractor original
(`sina/ollama/extract_flyer_text.py`), usa el parámetro `format=<json schema>` de
Ollama para **forzar salida estructurada** en vez de confiar solo en el prompt.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from sina.vlm.base import VLMProvider, VLMResultado, VLMUso

log = logging.getLogger(__name__)


class OllamaVLMProvider(VLMProvider):
    def __init__(
        self,
        modelo: str,
        host: str = "http://localhost:11434",
        api_key: str = "",
    ) -> None:
        # Import perezoso para no acoplar el arranque a ollama.
        from ollama import Client

        self.modelo = modelo
        if api_key:
            # Modo nube (mismo patrón que extract_flyer_text.py): host de Ollama Cloud.
            self._client = Client(
                host="https://ollama.com",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        else:
            self._client = Client(host=host)

    def extraer(
        self,
        imagen_path: str,
        prompt: str,
        formato: dict | None = None,
    ) -> VLMResultado:
        inicio = time.time()
        resp = self._client.chat(
            model=self.modelo,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": "Extrae los productos visibles en esta imagen.",
                    "images": [str(imagen_path)],
                },
            ],
            options={"temperature": 0},
            format=formato or None,  # JSON Schema → salida estructurada real.
        )
        dur_ms = (time.time() - inicio) * 1000.0

        contenido: str | None = getattr(resp.message, "content", None)
        datos = self._parsear(contenido)
        return VLMResultado(datos=datos, uso=self._armar_uso(resp, dur_ms))

    @staticmethod
    def _parsear(contenido: str | None) -> dict:
        if not contenido:
            return {"productos": []}
        try:
            return json.loads(contenido)
        except json.JSONDecodeError:
            # Con `format=` no debería pasar; por si un modelo envuelve en markdown.
            import re
            limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", contenido.strip())
            try:
                return json.loads(limpio)
            except json.JSONDecodeError:
                log.warning("VLM devolvió JSON no parseable; se ignora la zona.")
                return {"productos": []}

    def _armar_uso(self, resp: Any, dur_ms: float) -> VLMUso:
        return VLMUso(
            modelo=self.modelo,
            input_tokens=int(getattr(resp, "prompt_eval_count", 0) or 0),
            output_tokens=int(getattr(resp, "eval_count", 0) or 0),
            duracion_ms=dur_ms,
        )
