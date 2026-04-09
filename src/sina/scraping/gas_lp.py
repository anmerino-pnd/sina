# sina/scraping/gas_lp.py
"""
Cliente para las APIs de la CNE relacionadas con Gas LP.

APIs utilizadas:
  - Catálogo: https://api-catalogo.cne.gob.mx/api/utiles/localidades
  - Precios:  https://api-reportediario.cne.gob.mx/api/PlantaDistribucion/precio

Uso típico:
    # 1) Solo una vez — poblar localidades en la DB
    from sina.scraping.gas_lp import seed_localidades_all
    seed_localidades_all()

    # 2) Obtener precios (ya con IDs)
    from sina.scraping.gas_lp import fetch_precios
    data = fetch_precios(localidad_id=289, entidad_id=26, municipio_id="030")
"""

import time
import logging
import requests
import xml.etree.ElementTree as ET
from sina.config.credentials import cne_localidades_url, cne_precios_gas_lp_url
from sina.db.repository import get_session, LocalidadRepository, MunicipioRepository
from sina.db.models import Localidad, Municipio
logger = logging.getLogger(__name__)

# Reemplazar _parsear_localidades_xml por esto:

def _parsear_localidades_json(content: bytes) -> list[dict]:
    """
    Parsea el JSON de respuesta de la API de localidades.

    Estructura real:
    [
        {
            "Id": 664,
            "Nombre": "20 de Noviembre",
            "EntidadFederativaId": "26",
            "EntidadFederativa": {"EntidadFederativaId": "26", "Nombre": "Sonora"},
            "MunicipioId": "030",
            "Municipio": {"MunicipioId": "030", "Nombre": "Hermosillo", ...}
        },
        ...
    ]
    """
    import json

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON de localidades: {e}")
        return []

    if not isinstance(data, list):
        logger.error(f"Se esperaba una lista, llegó: {type(data)}")
        return []

    resultados = []

    for item in data:
        # ── ID ────────────────────────────────────────────────
        loc_id = item.get("Id")

        if loc_id is None:
            continue

        # Asegurarnos que sea entero válido
        try:
            loc_id = int(loc_id)
        except (ValueError, TypeError):
            continue

        # ── Nombre ───────────────────────────────────────────
        nombre = item.get("Nombre") or ""
        nombre = nombre.strip()

        # Skip vacíos o "Ninguno" (incluyendo "Ninguno [Sergio Ruiz Montaño]")
        if not nombre or nombre.lower().startswith("ninguno"):
            logger.debug(f"  Skipping id={loc_id} nombre='{nombre}'")
            continue

        resultados.append({
            "localidad_id": loc_id,
            "nombre":       nombre,
        })

    return resultados

def fetch_localidades(entidad_id: int, municipio_id_str: str) -> list[dict]:
    url = cne_localidades_url
    params = {
        "entidadFederativaId": entidad_id,
        "municipioId":         municipio_id_str,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Error al pedir localidades (entidad={entidad_id}, mun={municipio_id_str}): {e}")
        return []

    # ← JSON, no XML
    return _parsear_localidades_json(resp.content)