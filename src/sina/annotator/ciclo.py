"""
Ciclo de vida de un flyer: descargado → anotado → extraído → persistido.

Todo se infiere del filesystem (sin tabla nueva), a partir de los artefactos
que deja cada etapa en `datos/flyers/<tienda>/<ciudad>/<fecha>/`:

  - descargado : `page_NN.jpg` + `metadata.json` (los deja el spider)
  - anotado    : `labels/*.json` (los deja "Guardar todo" del anotador)
  - extraído   : `extraccion.json` (lo deja `POST /annotator/extract`)
  - persistido : `persistido.json` (lo deja `POST /annotator/persistir`)

La vigencia NO asume ninguna cadencia (puede durar una semana o dos días y
vencer cualquier día; cada tienda es distinta). Se resuelve por prioridad:

  1. `persistido.json` — la que el humano confirmó al insertar (máxima confianza).
  2. `metadata.json`   — la parseada del scraping (Abarrey la publica en su HTML).
  3. Desconocida       — el sistema no adivina: `vencido = None` y la acción es
     capturarla (en Casa Ley va impresa en la imagen, solo el humano la ve).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sina.config.paths import FLYERS_DATA
from sina.config.timezone import get_mexico_now
from sina.annotator.image_segmentation import resolver_ruta_flyer

log = logging.getLogger(__name__)

_GLOB_IMAGENES = "*.[jp][pn]*g"  # mismo criterio que build_filesystem_tree


def _leer_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def estado_flyer(tienda: str, ciudad: str, fecha: str) -> dict:
    """Estado completo de un flyer (etapa + avance + vigencia + vencido)."""
    base = resolver_ruta_flyer(tienda, ciudad, fecha)

    imagenes = len(list(base.glob(_GLOB_IMAGENES)))
    anotadas = len(list((base / "labels").glob("*.json")))
    extraido = (base / "extraccion.json").exists()
    persistido = _leer_json(base / "persistido.json")

    if persistido:
        etapa = "persistido"
    elif extraido:
        etapa = "extraido"
    elif anotadas > 0:
        etapa = "anotado"
    elif imagenes > 0:
        etapa = "descargado"
    else:
        etapa = "vacio"

    # Vigencia por prioridad: humano (persistido) → scraping (metadata) → desconocida.
    fuente_vigencia = None
    vig_inicio = vig_fin = None
    if persistido.get("vigencia_fin"):
        vig_inicio = persistido.get("vigencia_inicio")
        vig_fin = persistido.get("vigencia_fin")
        fuente_vigencia = "humano"
    else:
        metadata = _leer_json(base / "metadata.json")
        if metadata.get("vigencia_fin"):
            vig_inicio = metadata.get("vigencia_inicio")
            vig_fin = metadata.get("vigencia_fin")
            fuente_vigencia = "scraping"

    vencido = None
    if vig_fin:
        try:
            from datetime import date
            vencido = get_mexico_now().date() > date.fromisoformat(vig_fin)
        except ValueError:
            vig_inicio = vig_fin = fuente_vigencia = None

    return {
        "tienda": tienda,
        "ciudad": ciudad,
        "fecha": fecha,
        "etapa": etapa,
        "imagenes": imagenes,
        "anotadas": anotadas,
        "vigencia_inicio": vig_inicio,
        "vigencia_fin": vig_fin,
        "fuente_vigencia": fuente_vigencia,
        "vencido": vencido,
    }


def _accion(estado: dict) -> str:
    """Siguiente paso humano/sistema para el flyer más reciente de una tienda-ciudad."""
    etapa = estado["etapa"]
    if etapa == "persistido":
        if estado["vencido"] is True:
            return "esperando flyer nuevo"
        if estado["vencido"] is None:
            return "capturar vigencia"
        return "al dia"
    if etapa == "extraido":
        return "insertar"
    if etapa == "anotado":
        return "anotar" if estado["anotadas"] < estado["imagenes"] else "extraer"
    if etapa == "descargado":
        return "anotar"
    return "sin imagenes"


def resumen_pendientes() -> list[dict]:
    """
    El flyer más reciente de cada (tienda, ciudad) con su estado y la acción
    sugerida. Es la fuente del panel "Folletos" del anotador y del job de
    descarga automática (que actúa solo cuando `vencido is True`).
    """
    resumen: list[dict] = []
    if not FLYERS_DATA.exists():
        return resumen

    for tienda_dir in sorted(FLYERS_DATA.iterdir()):
        if not tienda_dir.is_dir():
            continue
        for ciudad_dir in sorted(tienda_dir.iterdir()):
            if not ciudad_dir.is_dir():
                continue
            fechas = sorted(d.name for d in ciudad_dir.iterdir() if d.is_dir())
            if not fechas:
                continue
            try:
                # Nombre de carpeta = YYYY-MM-DD → el orden lexicográfico es cronológico.
                estado = estado_flyer(tienda_dir.name, ciudad_dir.name, fechas[-1])
            except ValueError:
                log.warning(
                    "Carpeta de flyer con nombre inválido: %s/%s/%s",
                    tienda_dir.name, ciudad_dir.name, fechas[-1],
                )
                continue
            estado["accion"] = _accion(estado)
            resumen.append(estado)
    return resumen
