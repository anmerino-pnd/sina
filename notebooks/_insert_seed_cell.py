# ============================================================
# Scrap masivo de localidades — solo las faltantes
# ============================================================
# Itera todas las entidades y sus municipios.
# Para cada municipio, verifica si ya tiene localidades en la DB.
# Solo llama a la API CNE si faltan localidades.
# ============================================================

from sina.db.repository import get_session
from sina.db.models import EntidadFederativa, Municipio, Localidad
from sina.scraping.gas_lp import fetch_localidades
from typing import cast
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def seed_localidades_all(delay: float = 0.5) -> dict:
    """
    Itera todas las entidades y sus municipios.
    Para cada municipio, verifica si ya tiene localidades en la DB.
    Solo llama a la API CNE si faltan localidades.

    Args:
        delay: segundos entre llamadas a la API para evitar rate-limit.

    Returns:
        {
            "total_municipios": int,
            "ya_completos": int,
            "scrapeados": int,
            "localidades_insertadas": int,
            "errores": list[str],
        }
    """
    resultados = {
        "total_municipios": 0,
        "ya_completos": 0,
        "scrapeados": 0,
        "localidades_insertadas": 0,
        "errores": [],
    }

    with get_session() as session:
        # 1. Todas las entidades
        entidades = session.query(EntidadFederativa).order_by(EntidadFederativa.id).all()
        logger.info(f"{len(entidades)} entidades encontradas.")

        for entidad in entidades:
            logger.info(f"\n{'─' * 50}")
            logger.info(f"Entidad {entidad.id} — {entidad.nombre}")

            # 2. Todos sus municipios
            municipios = (
                session.query(Municipio)
                .filter_by(entidad_id=entidad.id)
                .order_by(Municipio.municipio_id)
                .all()
            )

            for mun in municipios:
                resultados["total_municipios"] += 1

                # 3. ¿Ya tenemos localidades para este municipio?
                count_existente = (
                    session.query(Localidad)
                    .filter_by(
                        entidad_id=entidad.id,
                        municipio_id=mun.municipio_id,
                    )
                    .count()
                )

                if count_existente > 0:
                    resultados["ya_completos"] += 1
                    logger.info(
                        f"  ✅ {mun.nombre} ({mun.municipio_id}): "
                        f"{count_existente} localidades ya existentes — skip"
                    )
                    continue

                # 4. No hay localidades — llamar a la API CNE
                logger.info(
                    f"  ⏳ {mun.nombre} ({mun.municipio_id}): "
                    f"sin localidades — llamando a API..."
                )

                try:
                    raw_list = fetch_localidades(cast(int, entidad.id), cast(str, mun.municipio_id))
                    resultados["scrapeados"] += 1

                    if not raw_list:
                        logger.info(f"    → 0 localidades devueltas por la API")
                        time.sleep(delay)
                        continue

                    # 5. Insertar en DB
                    nuevas = [
                        Localidad(
                            localidad_id=loc["localidad_id"],
                            nombre=loc["nombre"],
                            entidad_id=entidad.id,
                            municipio_id=mun.municipio_id,
                        )
                        for loc in raw_list
                    ]

                    session.add_all(nuevas)
                    session.flush()  # para obtener IDs sin commit
                    resultados["localidades_insertadas"] += len(nuevas)

                    logger.info(f"    → {len(nuevas)} localidades insertadas")

                except Exception as e:
                    msg = f"{entidad.nombre}/{mun.nombre}: {e}"
                    resultados["errores"].append(msg)
                    logger.error(f"    ✗ Error: {e}")

                time.sleep(delay)

        session.commit()

    logger.info(f"\n{'=' * 50}")
    logger.info(f"Resumen:")
    logger.info(f"  Total municipios:       {resultados['total_municipios']}")
    logger.info(f"  Ya completos (skip):    {resultados['ya_completos']}")
    logger.info(f"  Scrapados:              {resultados['scrapeados']}")
    logger.info(f"  Localidades insertadas: {resultados['localidades_insertadas']}")
    logger.info(f"  Errores:                {len(resultados['errores'])}")

    if resultados["errores"]:
        logger.info("  Detalle errores:")
        for err in resultados["errores"]:
            logger.info(f"    - {err}")

    return resultados
