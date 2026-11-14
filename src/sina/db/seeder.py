# sina/db/seeder.py

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
import pyarrow.parquet as pq
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from sina.db.models import (
    EntidadFederativa,
    Municipio,
    Localidad,
    PrecioGasolina,
    CatalogoConfig,
)
from sina.config.paths import (
    CATALOGO_MUNICIPIOS_PATH,
    LOCALIDADES_PARQUET_PATH,
    UBICACIONES_GASOLINERAS_PARQUET_PATH,
    SORIANA_CONFIG_PATH,
    DELSOL_CONFIG_PATH,
    BENAVIDES_CONFIG_PATH,
    GUADALAJARA_CONFIG_PATH,
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000


def _dialect_insert(session: Session, model):
    """INSERT con soporte ON CONFLICT acorde al dialecto de la sesión activa."""
    if session.get_bind().dialect.name == "postgresql":
        return pg_insert(model)
    return sqlite_insert(model)


def seed_catalogo_municipios(
    session: Session,
    catalogo_path: Path = CATALOGO_MUNICIPIOS_PATH,
) -> dict:
    """
    Lee catalogo_municipios.json y puebla cne_entidades y cne_municipios
    de forma idempotente en bloque.

    Returns:
        {"entidades": int, "municipios": int} — registros nuevos insertados
    """
    if not catalogo_path.exists():
        logger.warning(f"No existe {catalogo_path}; se omite seed de municipios.")
        return {"entidades": 0, "municipios": 0}

    with open(catalogo_path, "r", encoding="utf-8") as f:
        catalogo: dict = json.load(f)

    entidades_existentes: set[int] = set(
        session.scalars(select(EntidadFederativa.id)).all()
    )
    municipios_existentes: set[tuple[int, str]] = {
        (eid, mid)
        for eid, mid in session.execute(
            select(Municipio.entidad_id, Municipio.municipio_id)
        ).all()
    }

    nuevas_entidades: list[dict] = []
    nuevos_municipios: list[dict] = []

    for nombre_estado, datos_estado in catalogo.items():
        entidad_id = int(datos_estado["id"])
        nombre_norm = nombre_estado.title()

        if entidad_id not in entidades_existentes:
            nuevas_entidades.append({"id": entidad_id, "nombre": nombre_norm})
            entidades_existentes.add(entidad_id)

        municipios_raw: dict = datos_estado.get("municipios", {})
        for nombre_mun, datos_mun in municipios_raw.items():
            municipio_id_str = str(datos_mun["id"])
            clave = (entidad_id, municipio_id_str)
            if clave not in municipios_existentes:
                nuevos_municipios.append({
                    "municipio_id": municipio_id_str,
                    "nombre": nombre_mun.title(),
                    "entidad_id": entidad_id,
                })
                municipios_existentes.add(clave)

    if nuevas_entidades:
        stmt_ent = _dialect_insert(session, EntidadFederativa).values(nuevas_entidades).on_conflict_do_nothing(
            index_elements=["id"]
        )
        session.execute(stmt_ent)

    if nuevos_municipios:
        stmt_mun = _dialect_insert(session, Municipio).values(nuevos_municipios).on_conflict_do_nothing(
            index_elements=["municipio_id", "entidad_id"]
        )
        session.execute(stmt_mun)

    session.commit()

    logger.info(
        f"Seeder municipios completado — "
        f"Entidades nuevas: {len(nuevas_entidades)} | "
        f"Municipios nuevos: {len(nuevos_municipios)}"
    )

    return {
        "entidades": len(nuevas_entidades),
        "municipios": len(nuevos_municipios),
    }


def seed_catalogo_localidades(
    session: Session,
    parquet_path: Path = LOCALIDADES_PARQUET_PATH,
    batch_size: int = BATCH_SIZE,
) -> dict:
    """
    Lee datos/seeds/cne_localidades.parquet (297,878 localidades CNE) y puebla
    cne_localidades por lotes usando ON CONFLICT DO NOTHING sobre
    (localidad_id, municipio_id, entidad_id).

    Returns:
        {"localidades_procesadas": int}
    """
    if not parquet_path.exists():
        logger.warning(f"No existe {parquet_path}; se omite seed de localidades CNE.")
        return {"localidades_procesadas": 0}

    tabla = pq.read_table(
        parquet_path,
        columns=["entidad_id", "municipio_id", "localidad_id", "nombre"],
    )
    filas = tabla.to_pylist()
    total = len(filas)

    for inicio in range(0, total, batch_size):
        lote = filas[inicio : inicio + batch_size]
        stmt = (
            _dialect_insert(session, Localidad)
            .values(lote)
            .on_conflict_do_nothing(
                index_elements=["localidad_id", "municipio_id", "entidad_id"]
            )
        )
        session.execute(stmt)

    session.commit()
    logger.info(f"Seeder localidades CNE completado — Procesadas: {total}")
    return {"localidades_procesadas": total}


def seed_ubicaciones_gasolineras(
    session: Session,
    parquet_path: Path = UBICACIONES_GASOLINERAS_PARQUET_PATH,
    batch_size: int = BATCH_SIZE,
) -> dict:
    """
    Lee datos/seeds/ubicaciones_gasolineras.parquet (coordenadas Fase 1 de
    estaciones CRE) y hace upsert por lotes en `gasolineras`. Si el permiso
    `numero` ya existe con precios de la CRE, solo actualiza `latitud` y
    `longitud` sin pisar precios ni fecha de registro.

    Returns:
        {"gasolineras_ubicaciones": int}
    """
    if not parquet_path.exists():
        logger.warning(f"No existe {parquet_path}; se omite seed de ubicaciones de gasolineras.")
        return {"gasolineras_ubicaciones": 0}

    tabla = pq.read_table(
        parquet_path,
        columns=["numero", "estado", "municipio", "latitud", "longitud"],
    )
    filas = tabla.to_pylist()
    total = len(filas)

    for inicio in range(0, total, batch_size):
        lote = filas[inicio : inicio + batch_size]
        base = _dialect_insert(session, PrecioGasolina)
        stmt = base.values(lote).on_conflict_do_update(
            index_elements=["numero"],
            set_={
                "latitud": base.excluded.latitud,
                "longitud": base.excluded.longitud,
            },
        )
        session.execute(stmt)

    session.commit()
    logger.info(f"Seeder ubicaciones de gasolineras completado — Procesadas: {total}")
    return {"gasolineras_ubicaciones": total}


def seed_catalogo_tienda(session: Session, tienda: str, config_path: Path) -> dict:
    """
    Lee un *_config.json de supermercado y puebla catalogos_config para `tienda`.

    El upsert es idempotente: busca por (tienda, departamento, categoria, url_path)
    e inserta solo si no existe, así que se puede re-ejecutar sin duplicar.

    Returns:
        {"tienda": str, "rutas": int} — rutas insertadas en esta corrida
    """
    if not config_path.exists():
        logger.warning(f"[{tienda}] No existe {config_path.name}; se omite.")
        return {"tienda": tienda, "rutas": 0}

    with open(config_path, "r", encoding="utf-8") as f:
        datos: dict = json.load(f)

    rutas_existentes: set[tuple[str, str, str]] = {
        (dep, cat, url)
        for dep, cat, url in session.execute(
            select(
                CatalogoConfig.departamento,
                CatalogoConfig.categoria,
                CatalogoConfig.url_path,
            ).where(CatalogoConfig.tienda == tienda)
        ).all()
    }

    ahora = datetime.now(timezone.utc)
    nuevas_rutas: list[dict] = []

    for departamento, datos_depto in datos.items():
        for categoria, datos_cat in datos_depto.items():
            url_path = datos_cat.get("url_path", "")
            prioridad = datos_cat.get("prioridad", 1)
            clave = (departamento, categoria, url_path)

            if clave not in rutas_existentes:
                nuevas_rutas.append({
                    "tienda": tienda,
                    "departamento": departamento,
                    "categoria": categoria,
                    "url_path": url_path,
                    "prioridad": prioridad,
                    "activo": True,
                    "fecha_registro": ahora,
                })
                rutas_existentes.add(clave)

    if nuevas_rutas:
        stmt = (
            _dialect_insert(session, CatalogoConfig)
            .values(nuevas_rutas)
            .on_conflict_do_nothing(
                index_elements=["tienda", "departamento", "categoria", "url_path"]
            )
        )
        session.execute(stmt)

    session.commit()

    logger.info(f"Seeder catálogo [{tienda}] completado — Rutas nuevas: {len(nuevas_rutas)}")

    return {"tienda": tienda, "rutas": len(nuevas_rutas)}


# Tiendas con catálogo de rutas para scraping (nombre → archivo de config).
TIENDAS_CATALOGO: list[tuple[str, Path]] = [
    ("Soriana", SORIANA_CONFIG_PATH),
    ("Del Sol", DELSOL_CONFIG_PATH),
    ("Benavides", BENAVIDES_CONFIG_PATH),
    ("Farmacias Guadalajara", GUADALAJARA_CONFIG_PATH),
]


def seed_catalogos(session: Session) -> dict:
    """Puebla catalogos_config para todas las tiendas en TIENDAS_CATALOGO."""
    resultados = {}
    for tienda, config_path in TIENDAS_CATALOGO:
        resultados[tienda] = seed_catalogo_tienda(session, tienda, config_path)["rutas"]
    return resultados


def seed_todo(session: Session) -> dict:
    """Ejecuta todos los seeders base (municipios, localidades, ubicaciones de gasolineras y catálogos)."""
    res_municipios = seed_catalogo_municipios(session)
    res_localidades = seed_catalogo_localidades(session)
    res_gasolineras = seed_ubicaciones_gasolineras(session)
    res_catalogos = seed_catalogos(session)
    return {
        "municipios": res_municipios,
        "localidades": res_localidades,
        "gasolineras": res_gasolineras,
        "catalogos": res_catalogos,
    }


if __name__ == "__main__":
    """Permite ejecutar directamente: python -m sina.db.seeder"""
    from sina.db.repository import get_session

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    with get_session() as session:
        resultado_municipios = seed_catalogo_municipios(session)
        print(f"\n[OK] Seeder municipios: {resultado_municipios}")

        resultado_localidades = seed_catalogo_localidades(session)
        print(f"[OK] Seeder localidades CNE: {resultado_localidades}")

        resultado_gasolineras = seed_ubicaciones_gasolineras(session)
        print(f"[OK] Seeder ubicaciones gasolineras: {resultado_gasolineras}")

        resultado_catalogos = seed_catalogos(session)
        print(f"[OK] Seeder catálogos supermercados: {resultado_catalogos}")
