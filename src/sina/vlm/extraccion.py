"""
Extracción de productos por ZONA (recorte) usando el `VLMProvider`.

Cada recorte del flyer (una zona delimitada por espacios en blanco) se manda al
VLM y devuelve un ARREGLO de productos. La salida se **valida con Pydantic** y se
aplican chequeos de **sanidad de precio** (positivo y en rango plausible); lo que
no pasa se marca para revisión humana en el anotador (nunca llega crudo a la DB).
"""
from __future__ import annotations

import logging

from pydantic import BaseModel, field_validator

from sina.annotator.image_segmentation import resolver_ruta_flyer
from sina.config.prompt import extract_zona_prompt, zona_schema_json
from sina.vlm.factory import get_vlm_provider

log = logging.getLogger(__name__)

# Rango plausible de un precio de flyer (MXN). Fuera de esto → revisión.
PRECIO_MIN = 0.0
PRECIO_MAX = 100_000.0

_EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


class ProductoFlyer(BaseModel):
    producto: str
    marca: str | None = None
    precio: float | None = None
    unidad: str | None = None
    tipo_oferta: str | None = None
    descripcion_oferta: str | None = None

    @field_validator("producto")
    @classmethod
    def _producto_no_vacio(cls, v: str) -> str:
        v = " ".join(str(v).split()).strip()
        if not v:
            raise ValueError("producto vacío")
        return v

    @field_validator("precio")
    @classmethod
    def _precio_plausible(cls, v: float | None) -> float | None:
        # Descarta precios imposibles (alucinaciones); el humano lo completará.
        if v is None:
            return None
        if v <= PRECIO_MIN or v > PRECIO_MAX:
            return None
        return round(float(v), 2)


class RVProblema(BaseModel):
    crudo: dict
    error: str


def extraer_zona(provider, imagen_path) -> dict:
    """
    Extrae los productos de un recorte. Devuelve
    `{"productos": [...], "revisar": bool, "n": int}`.
    `revisar=True` si algún producto quedó sin precio válido o hubo errores.
    """
    resultado = provider.extraer(
        str(imagen_path), prompt=extract_zona_prompt, formato=zona_schema_json,
    )
    crudos = (resultado.datos or {}).get("productos") or []

    productos: list[dict] = []
    revisar = False
    for c in crudos:
        if not isinstance(c, dict):
            revisar = True
            continue
        try:
            p = ProductoFlyer(**c)
        except Exception as e:  # noqa: BLE001 — producto inválido → marcar y seguir
            log.warning("Producto inválido en %s: %s", imagen_path, e)
            revisar = True
            continue
        if p.precio is None:
            revisar = True
        productos.append(p.model_dump())

    return {"productos": productos, "revisar": revisar, "n": len(productos)}


def extraer_recortes(supermarket: str, city: str, date: str) -> dict:
    """
    Corre el VLM sobre TODOS los recortes de un flyer y agrega el resultado por
    zona (nombre de archivo del recorte). Pensado para la revisión humana en el
    anotador antes de persistir.
    """
    provider = get_vlm_provider()
    if provider is None:
        raise RuntimeError(
            "VLM no disponible (revisa ENABLE_VLM y VLM_PROVIDER/VLM_MODEL)."
        )

    base = resolver_ruta_flyer(supermarket, city, date, "recortes")
    if not base.exists():
        raise FileNotFoundError("No hay carpeta de recortes; primero recorta las zonas.")

    zonas: dict[str, dict] = {}
    total = 0
    for crop in sorted(base.iterdir()):
        if crop.suffix.lower() not in _EXTENSIONES:
            continue
        try:
            res = extraer_zona(provider, crop)
        except Exception as e:  # noqa: BLE001 — una zona no debe tumbar todo
            log.error("Error extrayendo zona %s: %s", crop.name, e)
            res = {"productos": [], "revisar": True, "n": 0, "error": str(e)}
        zonas[crop.name] = res
        total += res.get("n", 0)

    return {"zonas": zonas, "total_productos": total}
