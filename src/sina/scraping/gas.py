import re
import time
import logging
import requests
import unicodedata
import pandas as pd
from typing import Any
from bs4 import BeautifulSoup, Tag
from datetime import datetime, timezone
from sina.config.credentials import DB_URL
from sina.db.repository import GasolinaRepository
from sina.config.credentials import (
    gasolina_api_rest, 
    cne_refer, 
    gasolineras_ubi, 
    HEADERS
    )

log = logging.getLogger(__name__)

GAS_COLUMN_MAP = {
    "Numero":    "numero",
    "Nombre":    "nombre",
    "Direccion": "direccion",
    "Diesel":    "diesel",
    "Magna":     "magna",
    "Premium":   "premium",
    "Latitud":   "latitud",
    "Longitud":  "longitud",
}

GAS_FLOAT_COLS = ["diesel", "magna", "premium", "latitud", "longitud"]




def _build_catalogo_js(mun_dict: dict) -> dict:
    """
    Construye dos objetos para el frontend:
      - CATALOGO:         { estado: [municipio, ...] }
      - DATOS_DISPONIBLES ya se llena dinámicamente en la ruta
    """
    return {
        estado: sorted(info["municipios"].keys())
        for estado, info in mun_dict.items()
    }

def extract_gas_prices(entidad_id: int, municipio_id: str) -> dict:
    """
    Los IDs ya vienen calculados desde el repositorio,
    no del JSON.
    """
    params = {
        "entidadId"  : entidad_id,
        "municipioId": municipio_id,
    }
    headers = {"User-Agent": "Mozilla/5.0", "Referer": cne_refer}
    response = requests.get(gasolina_api_rest, params=params, headers=headers)
    return response.json()

def transform_gas_prices(estado: str, municipio: str,
                         entidad_id: int, municipio_id: str) -> list[dict]:
    """
    Extrae precios de la API CRE y los transforma en registros
    listos para upsert_precios().
    
    Ya NO usa cache file — lat/lng viven en la DB.
    """
    data = extract_gas_prices(entidad_id, municipio_id)
    df   = pd.DataFrame(data["Value"])

    # ── Mapeo de subproductos ─────────────────────────────
    mapa_productos = {
        sp: (
            "Premium" if "Premium"  in sp else
            "Magna"   if "Regular"  in sp else
            "Diesel"  if "Diésel"   in sp else
            "Otro"
        )
        for sp in df["SubProducto"].unique()
    }
    df["Combustible"] = df["SubProducto"].map(mapa_productos)

    # ── Pivot ─────────────────────────────────────────────
    df_pivot = df.pivot_table(
        index   = ["Numero", "Nombre", "Direccion"],
        columns = "Combustible",
        values  = "PrecioVigente",
        aggfunc = "first"
    ).reset_index()
    df_pivot.columns.name = None

    for col in ["Magna", "Premium", "Diesel"]:
        if col not in df_pivot.columns:
            df_pivot[col] = None

    # ── Construir registros para upsert_precios() ─────────
    registros = [
        {
            "numero"        : row["Numero"],
            "estado"        : estado.lower(),
            "municipio"     : municipio.lower(),
            "nombre"        : row["Nombre"],
            "direccion"     : row["Direccion"],
            "magna"         : row.get("Magna"),
            "premium"       : row.get("Premium"),
            "diesel"        : row.get("Diesel"),
            "fecha_registro": datetime.now(timezone.utc),
        }
        for _, row in df_pivot.iterrows()
    ]

    return registros

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")

def _get_station_links(estado: str, municipio: str) -> list[str]:
    """
    Dado estado y municipio, va al listing page y extrae
    todos los links a páginas de detalle de cada estación.

    Returns: ["https://gasolinamexico.com.mx/estacion/13392/...", ...]
    """
    url = f"{gasolineras_ubi}/{_slugify(estado)}/{_slugify(municipio)}/"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code == 404:
            log.warning(f"Página no encontrada: {url}")
            return []

        response.raise_for_status()

    except requests.RequestException as e:
        log.error(f"Error de red en listing {estado}/{municipio}: {e}")
        return []

    soup  = BeautifulSoup(response.text, "html.parser")
    links: list[str] = [
        str(href)
        for a in soup.find_all("a", href=True)
        if isinstance(a, Tag)
        and (href := a.get("href"))
        and "/estacion/" in str(href)
    ]

    log.info(f"  {municipio}: {len(links)} estaciones encontradas")
    return links

def _scrape_station(url: str) -> dict | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        log.error(f"Error de red en detalle {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # ── Permiso ──────────────────────────────────────────────
    permiso = None
    for li in soup.find_all("li"):
        if not isinstance(li, Tag):          
            continue
        strong = li.find("strong")
        if not isinstance(strong, Tag):      
            continue
        if strong.string and "Permiso" in strong.string:
            permiso = li.get_text(strip=True).replace("Permiso:", "").strip()
            break

    # ── Coordenadas ──────────────────────────────────────────
    lat, lng = None, None
    for script in soup.find_all("script"):
        if not isinstance(script, Tag):     
            continue
        if not script.string or "setView" not in script.string:
            continue
        m = re.search(r'(\d+\.\d+),\s*(-\d+\.\d+)', script.string)
        if m:
            lat = float(m.group(1))
            lng = float(m.group(2))
            break

    if not permiso or lat is None:
        log.warning(f"Datos incompletos — permiso: {permiso}, lat: {lat} | {url}")
        return None

    return {
        "permiso" : permiso,
        "latitud" : lat,
        "longitud": lng,
    }

def scrape_municipio(
    estado   : str,
    municipio: str,
    delay    : float = 1.0,
) -> list[dict[str, Any]]:
    """
    Combina _get_station_links + scrape_detalle_estacion
    para un municipio completo.

    Returns:
    [
        {"permiso": "PL/11257/...", "latitud": 29.17, "longitud": -110.9,
         "estado": "sonora", "municipio": "hermosillo"},
        ...
    ]
    """
    links = _get_station_links(estado, municipio)

    if not links:
        log.warning(f"Sin links para {estado}/{municipio}")
        return []

    resultados: list[dict[str, Any]] = []   # ← mismo aquí
    total      = len(links)

    for i, link in enumerate(links, 1):
        log.info(f"    [{i}/{total}] {link.split('/')[-2]}")

        data = _scrape_station(link)

        if data:
            resultados.append({
                "permiso"  : data["permiso"],
                "latitud"  : data["latitud"],
                "longitud" : data["longitud"],
                "estado"   : estado.lower(),
                "municipio": municipio.lower(),
            })

        time.sleep(delay)

    log.info(f"  ✅ {municipio}: {len(resultados)}/{total} exitosas")
    return resultados

def get_precios_gasolina(estado: str, municipio: str,
                         entidad_id: int, municipio_id: str) -> dict:
    """
    Caché on-demand 24h para precios de gasolina.
    Espejo de get_precios_gas_lp().
    """

    repo = GasolinaRepository(db_url=DB_URL)

    # ── 1. Verificar caché ─────────────────────────────────────
    if not repo.necesita_actualizacion(estado, municipio):
        print(f"Devolviendo datos en caché para {estado}/{municipio}")
        registros = repo.obtener_por_municipio(estado, municipio)
        return {
            "status"   : "ok",
            "fuente"   : "cache",
            "estado"   : estado,
            "municipio": municipio,
            "total"    : len(registros),
            "datos"    : registros,
        }

    # ── 2. Llamar a CRE y actualizar DB ───────────────────────
    try:
        print(f"Actualizando precios de gasolina para {estado}/{municipio} desde API...")
        nuevos = transform_gas_prices(estado, municipio, entidad_id, municipio_id)
        repo.upsert_precios(nuevos)
    except Exception as e:
        log.error(f"Error actualizando gasolina {estado}/{municipio}: {e}")
        # Si hay datos viejos, los devolvemos igual
        registros = repo.obtener_por_municipio(estado, municipio)
        if registros:
            return {
                "status"   : "ok",
                "fuente"   : "cache_vencido",
                "estado"   : estado,
                "municipio": municipio,
                "total"    : len(registros),
                "datos"    : registros,
            }
        return {
            "status" : "error",
            "detail" : f"API no disponible y sin datos en caché: {e}",
        }

    # ── 3. Leer de DB y devolver (consistencia) ───────────────
    registros = repo.obtener_por_municipio(estado, municipio)
    return {
        "status"   : "ok",
        "fuente"   : "api",
        "estado"   : estado,
        "municipio": municipio,
        "total"    : len(registros),
        "datos"    : registros,
    }