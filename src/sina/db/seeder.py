# sina/db/seeder.py

import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from sina.db.models import EntidadFederativa, Municipio
from sina.config.paths import CATALOGO_MUNICIPIOS_PATH

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


if __name__ == "__main__":
    """Permite ejecutar directamente: python -m sina.db.seeder"""
    import logging
    from sina.db.repository import get_session

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    with get_session() as session:
        resultado = seed_catalogo_municipios(session)
        print(f"\n✅ Seeder finalizado: {resultado}")