import logging
import requests
import json
from typing import cast, Dict, List, Any, Optional
from datetime import datetime
from sina.config.credentials import DB_URL
from sina.db.repository import get_session, GasLPRepository
from sina.db.models import Localidad, EntidadFederativa, Municipio
from sina.config.credentials import cne_localidades_url, cne_precios_gas_lp_url
from sina.config.timezone import get_mexico_now

logger = logging.getLogger(__name__)

def _parsear_localidades_json(content: bytes) -> List[Dict[str, Any]]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON de localidades: {e}")
        return []

    if not isinstance(data, list):
        logger.error(f"Se esperaba una lista, llegó: {type(data)}")
        return []

    resultados: List[Dict[str, Any]] = []

    for item in data:
        loc_id = item.get("Id")

        if loc_id is None:
            continue

        try:
            loc_id = int(loc_id)
        except (ValueError, TypeError):
            continue

        nombre = item.get("Nombre") or ""
        nombre = nombre.strip()

        if not nombre or nombre.lower().startswith("ninguno"):
            logger.debug(f"  Skipping id={loc_id} nombre='{nombre}'")
            continue

        resultados.append({
            "localidad_id": loc_id,
            "nombre":       nombre,
        })

    return resultados

def fetch_localidades(entidad_id: int, municipio_id_str: str) -> List[Dict[str, Any]]:
    url = cne_localidades_url
    params = {
        "entidadFederativaId": f"{entidad_id:02d}",
        "municipioId":         municipio_id_str,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(
            f"Error al pedir localidades "
            f"(entidad={entidad_id:02d}, mun={municipio_id_str}): {e}"
        )
        return []

    return _parsear_localidades_json(resp.content)


def save_localidades_to_db(entidad_id: int, municipio_id_str: str) -> Dict[str, int]:
    localidades = fetch_localidades(entidad_id, municipio_id_str)

    if not localidades:
        logger.warning(f"Sin localidades para entidad={entidad_id} municipio={municipio_id_str}")
        return {"insertadas": 0, "skipped": 0, "total_api": 0}

    with get_session() as session:
        ids_existentes: set[int] = {
            row[0]
            for row in session.query(Localidad.localidad_id)
            .filter_by(
                municipio_id=municipio_id_str,
                entidad_id=entidad_id,
            )
            .all()
        }

        nuevas = [
            Localidad(
                localidad_id  = loc["localidad_id"],
                nombre        = loc["nombre"],
                entidad_id    = entidad_id,
                municipio_id  = municipio_id_str,
            )
            for loc in localidades
            if loc["localidad_id"] not in ids_existentes
        ]

        skipped = len(localidades) - len(nuevas)

        if nuevas:
            session.add_all(nuevas)

        session.commit()

    resultado = {
        "insertadas": len(nuevas),
        "skipped":    skipped,
        "total_api":  len(localidades),
    }

    logger.info(
        f"[entidad={entidad_id} mun={municipio_id_str}] "
        f"Insertadas={resultado['insertadas']} | "
        f"Skipped={resultado['skipped']}"
    )

    return resultado

def get_localidades_by_municipio(entidad_id: int, municipio_id: str) -> List[Dict[str, Any]]:
    with get_session() as session:
        rows = (
            session.query(Localidad.localidad_id, Localidad.nombre)
            .filter_by(
                entidad_id=entidad_id,
                municipio_id=municipio_id,
            )
            .order_by(Localidad.nombre.asc())
            .all()
        )
        return [{"id": r.localidad_id, "nombre": r.nombre} for r in rows]


def get_precios_gas_lp(
    estado:    str,
    municipio: str,
    localidad: str,
) -> Dict[str, Any]:
    loc = _buscar_localidad(estado, municipio, localidad)

    if loc is None:
        logger.warning(
            f"Localidad no encontrada: {estado} / {municipio} / {localidad}"
        )
        return {
            "error": "Localidad no encontrada",
            "estado": estado,
            "municipio": municipio,
            "localidad": localidad,
        }

    entidad_id:   int = cast(int, loc.entidad_id)
    municipio_id: str = cast(str, loc.municipio_id)
    localidad_id: int = cast(int, loc.localidad_id)

    logger.info(
        f"Localidad encontrada: {loc.nombre} "
        f"(entidad={entidad_id}, mun={municipio_id}, loc={localidad_id})"
    )

    repo = GasLPRepository(db_url=DB_URL)

    if not repo.necesita_actualizacion(entidad_id, municipio_id, localidad_id):
        logger.info(f"Cache hit ✅ — devolviendo datos de DB")
        precios = repo.obtener_por_localidad(entidad_id, municipio_id, localidad_id)
        return _formatear_respuesta(precios, loc, fuente="cache")

    logger.info(f"Cache miss / vencido — llamando a API CNE...")
    datos_api = _fetch_precios_api(localidad_id, entidad_id, municipio_id)

    if datos_api is None:
        precios_viejos = repo.obtener_por_localidad(entidad_id, municipio_id, localidad_id)
        if precios_viejos:
            logger.warning("API falló, devolviendo datos viejos de DB")
            return _formatear_respuesta(precios_viejos, loc, fuente="cache_vencido")

        return {
            "error": "No se pudieron obtener precios (API no disponible)",
            "estado": estado,
            "municipio": municipio,
            "localidad": localidad,
        }

    entidad_nombre   = _get_entidad_nombre(entidad_id)
    municipio_nombre = _get_municipio_nombre(entidad_id, municipio_id)
    registros = _transformar_para_db(datos_api, loc, entidad_nombre, municipio_nombre)
    repo.upsert_precios_gas_lp(registros)
    logger.info(f"DB actualizada con {len(registros)} registros")

    precios_nuevos = repo.obtener_por_localidad(entidad_id, municipio_id, localidad_id)
    return _formatear_respuesta(precios_nuevos, loc, fuente="api")

def _buscar_localidad(estado: str, municipio: str, localidad: str) -> Optional[Localidad]:
    with get_session() as session:
        entidad = (
            session.query(EntidadFederativa)
            .filter(EntidadFederativa.nombre.ilike(estado.strip()))
            .first()
        )
        if entidad is None:
            logger.warning(f"Estado no encontrado: '{estado}'")
            return None

        mun = (
            session.query(Municipio)
            .filter(
                Municipio.entidad_id == entidad.id,
                Municipio.nombre.ilike(municipio.strip()),
            )
            .first()
        )
        if mun is None:
            logger.warning(f"Municipio no encontrado: '{municipio}' en '{estado}'")
            return None

        loc = (
            session.query(Localidad)
            .filter(
                Localidad.entidad_id   == entidad.id,
                Localidad.municipio_id == mun.municipio_id,
                Localidad.nombre.ilike(localidad.strip()),
            )
            .first()
        )

        if loc is None:
            logger.warning(f"Localidad no encontrada: '{localidad}' en '{municipio}'")
            return None

        session.expunge(loc)
        return loc


def _fetch_precios_api(
    localidad_id: int,
    entidad_id:   int,
    municipio_id: str,
) -> Optional[Dict[str, Any]]:
    params = {
        "localidadId": localidad_id,
        "entidadId":   entidad_id,
        "municipioId": municipio_id,
    }

    try:
        resp = requests.get(cne_precios_gas_lp_url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(f"Error llamando API precios: {e}")
        return None
    except ValueError as e:
        logger.error(f"Error parseando JSON de precios: {e}")
        return None

    if not data.get("Success"):
        logger.warning(f"API reportó error: {data.get('Errors')}")
        return None

    return data.get("Value", {})


def _transformar_para_db(datos_api: Dict[str, Any], loc: Localidad,
                         entidad_nombre: str, municipio_nombre: str) -> List[Dict[str, Any]]:
    ahora    = get_mexico_now()
    registros: List[Dict[str, Any]] = []

    for item in datos_api.get("AutoTanques", []) or []:
        precio = item.get("Precio")
        if precio is None:
            continue

        registros.append({
            "entidad_id":            loc.entidad_id,
            "municipio_id":          loc.municipio_id,
            "localidad_id":          loc.localidad_id,
            "entidad_nombre":        entidad_nombre,
            "municipio_nombre":      municipio_nombre,
            "localidad_nombre":      loc.nombre,
            "numero_permiso":        item.get("NumeroPermiso", ""),
            "marca_comercial":       item.get("MarcaComercial") or "",
            "tipo":                  "autotanque",
            "capacidad_recipiente":  None,
            "precio":                float(precio),
            "fecha_extraccion":      ahora,
        })

    for item in datos_api.get("Recipientes", []) or []:
        precio    = item.get("Precio")
        capacidad = item.get("CapacidadRecipiente")
        if precio is None or capacidad is None:
            continue

        registros.append({
            "entidad_id":            loc.entidad_id,
            "municipio_id":          loc.municipio_id,
            "localidad_id":          loc.localidad_id,
            "entidad_nombre":        entidad_nombre,
            "municipio_nombre":      municipio_nombre,
            "localidad_nombre":      loc.nombre,
            "numero_permiso":        item.get("NumeroPermiso", ""),
            "marca_comercial":       item.get("MarcaComercial") or "",
            "tipo":                  "recipiente",
            "capacidad_recipiente":  int(capacidad),
            "precio":                float(precio),
            "fecha_extraccion":      ahora,
        })

    return registros


def _formatear_respuesta(precios: List[Dict[str, Any]], loc: Localidad, fuente: str) -> Dict[str, Any]:
    autotanques = sorted(
        [p for p in precios if p["tipo"] == "autotanque"],
        key=lambda x: x["precio"]
    )
    recipientes = sorted(
        [p for p in precios if p["tipo"] == "recipiente"],
        key=lambda x: (x["precio"], x["capacidad_recipiente"] or 0)
    )

    fecha = precios[0]["fecha_extraccion"] if precios else None

    return {
        "localidad":   loc.nombre,
        "municipio":   precios[0]["municipio_nombre"] if precios else "",
        "estado":      precios[0]["entidad_nombre"]   if precios else "",
        "autotanques": autotanques,
        "recipientes": recipientes,
        "fuente":      fuente,
        "fecha_datos": fecha,
        "total":       len(precios),
    }


_cache_nombres: Dict[str, str] = {}

def _get_entidad_nombre(entidad_id: int) -> str:
    key = f"e_{entidad_id}"

    if key not in _cache_nombres:
        with get_session() as session:
            e = session.get(EntidadFederativa, entidad_id)
            _cache_nombres[key] = str(e.nombre) if e else str(entidad_id)

    return _cache_nombres[key]


def _get_municipio_nombre(entidad_id: int, municipio_id: str) -> str:
    key = f"m_{entidad_id}_{municipio_id}"

    if key not in _cache_nombres:
        with get_session() as session:
            m = (
                session.query(Municipio)
                .filter_by(
                    entidad_id=entidad_id,
                    municipio_id=municipio_id
                )
                .first()
            )

            _cache_nombres[key] = str(m.nombre) if m else municipio_id

    return _cache_nombres[key]
