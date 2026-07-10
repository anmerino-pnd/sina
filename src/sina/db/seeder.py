# sina/db/seeder.py

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sina.db.models import (
    EntidadFederativa, Municipio,
    CatalogoConfig,
)
from sina.config.paths import (
    CATALOGO_MUNICIPIOS_PATH, CLASES_JSON_PATH,
    SORIANA_CONFIG_PATH, DELSOL_CONFIG_PATH, BENAVIDES_CONFIG_PATH,
    GUADALAJARA_CONFIG_PATH,
)

logger = logging.getLogger(__name__)

def seed_catalogo_municipios(session: Session) -> dict:
    """
    Lee catalogo_municipios.json y puebla cne_entidades y cne_municipios.
    
    Estructura esperada del JSON:
    {
        "aguascalientes": {
            "id": "01",
            "municipios": {
                "aguascalientes": {"id": "001"},
                "asientos":       {"id": "002"},
                ...
            }
        },
        ...
    }
    
    Returns:
        {"entidades": int, "municipios": int}  — registros insertados
    """
    with open(CATALOGO_MUNICIPIOS_PATH, "r", encoding="utf-8") as f:
        catalogo: dict = json.load(f)

    entidades_insertadas = 0
    municipios_insertados = 0

    for nombre_estado, datos_estado in catalogo.items():
        entidad_id  = int(datos_estado["id"])
        nombre_norm = nombre_estado.title()  # "aguascalientes" → "Aguascalientes"

        # ── Upsert EntidadFederativa ───────────────────────────
        entidad = session.get(EntidadFederativa, entidad_id)

        if entidad is None:
            entidad = EntidadFederativa(id=entidad_id, nombre=nombre_norm)
            session.add(entidad)
            entidades_insertadas += 1
            logger.debug(f"  + Entidad: {nombre_norm} (id={entidad_id})")
        else:
            logger.debug(f"  ~ Entidad ya existe: {nombre_norm}")

        # ── Upsert Municipios ──────────────────────────────────
        municipios_raw: dict = datos_estado.get("municipios", {})

        for nombre_mun, datos_mun in municipios_raw.items():
            municipio_id_str = datos_mun["id"]   # "001", "030", etc.
            nombre_mun_norm  = nombre_mun.title()

            # Verificar si ya existe
            existe = (
                session.query(Municipio)
                .filter_by(municipio_id=municipio_id_str, entidad_id=entidad_id)
                .first()
            )

            if existe is None:
                mun = Municipio(
                    municipio_id=municipio_id_str,
                    nombre=nombre_mun_norm,
                    entidad_id=entidad_id,
                )
                session.add(mun)
                municipios_insertados += 1

    session.commit()

    logger.info(
        f"Seeder completado — "
        f"Entidades: {entidades_insertadas} | "
        f"Municipios: {municipios_insertados}"
    )

    return {
        "entidades": entidades_insertadas,
        "municipios": municipios_insertados,
    }


def seed_catalogo_tienda(session: Session, tienda: str, config_path: Path) -> dict:
    """
    Lee un *_config.json de supermercado y puebla catalogos_config para `tienda`.

    Estructura esperada del JSON (nivel superior = departamento, sin wrapper de
    tienda — así vienen soriana_config.json / delsol_config.json / benavides_config.json):
    {
        "despensa": {
            "arroz": {
                "url_path": "/despensa/arroz-frijol-y-semillas/arroz/",
                "nombre_visible": "Arroz",
                "prioridad": 1
            },
            ...
        },
        ...
    }

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

    rutas_insertadas = 0

    for departamento, datos_depto in datos.items():
        for categoria, datos_cat in datos_depto.items():
            url_path = datos_cat.get("url_path", "")
            prioridad = datos_cat.get("prioridad", 1)

            registro = session.query(CatalogoConfig).filter(
                CatalogoConfig.tienda == tienda,
                CatalogoConfig.departamento == departamento,
                CatalogoConfig.categoria == categoria,
                CatalogoConfig.url_path == url_path,
            ).first()

            if registro is None:
                catalogo = CatalogoConfig(
                    tienda=tienda,
                    departamento=departamento,
                    categoria=categoria,
                    url_path=url_path,
                    prioridad=prioridad,
                    activo=True,
                    fecha_registro=datetime.now(timezone.utc),
                )
                session.add(catalogo)
                rutas_insertadas += 1
                logger.debug(f"  + [{tienda}] {departamento} > {categoria} => {url_path}")
            else:
                logger.debug(f"  ~ [{tienda}] ya existe: {departamento} > {categoria}")

    session.commit()

    logger.info(f"Seeder catálogo [{tienda}] completado — Rutas nuevas: {rutas_insertadas}")

    return {"tienda": tienda, "rutas": rutas_insertadas}


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


if __name__ == "__main__":
    """Permite ejecutar directamente: python -m sina.db.seeder"""
    import logging
    from sina.db.repository import get_session

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    with get_session() as session:
        # Seed de municipios primero
        resultado_municipios = seed_catalogo_municipios(session)
        print(f"\n[OK] Seeder municipios: {resultado_municipios}")

        # Luego catálogos de rutas de todas las tiendas (Soriana, Del Sol, Benavides)
        resultado_catalogos = seed_catalogos(session)
        print(f"\n[OK] Seeder catálogos supermercados: {resultado_catalogos}")
