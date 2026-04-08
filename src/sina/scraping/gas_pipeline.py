# sina/scraping/gas_pipeline.py
import asyncio
import logging
from datetime import date
from typing import Optional

from sina.scraping.gas import (
    _load_catalogo,
    df_gas_prices,
    GAS_COLUMN_MAP,
    GAS_FLOAT_COLS,
)
from sina.processing.records import df_to_dict
from sina.db.repository import GasolinaRepository
from sina.config.credentials import DB_URL

# ============================================================
#  LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ============================================================
#  PIPELINE
# ============================================================
async def pipeline_nacional(
    delay: float = 0.5,
    estados_filtro: Optional[list[str]] = None,
):
    """
    Itera sobre todos los estados y municipios del catálogo,
    extrae precios de la API CRE y los guarda en la DB.

    Args:
        delay          : Segundos de espera entre requests (cortesía con la API).
        estados_filtro : Si se pasa una lista, solo procesa esos estados.
                         Útil para pruebas o reprocesamiento parcial.
    """
    mun_dict = _load_catalogo()
    repo     = GasolinaRepository(db_url=DB_URL)

    estados = (
        {k: v for k, v in mun_dict.items() if k in estados_filtro}
        if estados_filtro
        else mun_dict
    )

    total_estados    = len(estados)
    total_municipios = sum(len(info["municipios"]) for info in estados.values())

    log.info("=" * 60)
    log.info(f"Iniciando pipeline nacional — {date.today()}")
    log.info(f"Estados   : {total_estados}")
    log.info(f"Municipios: {total_municipios}")
    log.info("=" * 60)

    exitosos = 0
    fallidos = []

    for estado, info in estados.items():
        municipios = info["municipios"]

        log.info(f"\n📍 Estado: {estado.upper()} ({len(municipios)} municipios)")

        for municipio in municipios.keys():
            try:
                log.info(f"   ⏳ Extrayendo: {municipio}...")

                # 1. Extraer
                df = df_gas_prices(estado, municipio)

                # 2. Transformar
                registros = df_to_dict(
                    df,
                    column_map=GAS_COLUMN_MAP,
                    float_cols=GAS_FLOAT_COLS,
                    extra_fields={
                        "estado":         estado,
                        "municipio":      municipio,
                        "fecha_registro": date.today(),
                    }
                )

                # 3. Guardar (upsert, no borrar todo)
                repo.guardar_en_bulk(registros)

                log.info(f"   ✅ {municipio}: {len(registros)} registros guardados.")
                exitosos += 1

            except KeyError as e:
                # Municipio no encontrado en catálogo de coordenadas, etc.
                log.warning(f"   ⚠️  {municipio}: KeyError — {e}")
                fallidos.append((estado, municipio, str(e)))

            except Exception as e:
                # Cualquier otro error: loggea y CONTINÚA
                log.error(f"   ❌ {municipio}: {e}")
                fallidos.append((estado, municipio, str(e)))

            finally:
                # Siempre espera antes del siguiente request
                await asyncio.sleep(delay)

    # ============================================================
    #  RESUMEN FINAL
    # ============================================================
    log.info("\n" + "=" * 60)
    log.info("PIPELINE FINALIZADO")
    log.info(f"  ✅ Exitosos : {exitosos}")
    log.info(f"  ❌ Fallidos : {len(fallidos)}")

    if fallidos:
        log.warning("\nMunicipios con error:")
        for estado, municipio, err in fallidos:
            log.warning(f"  - {estado} / {municipio}: {err}")

    log.info("=" * 60)

    return {
        "fecha"    : str(date.today()),
        "exitosos" : exitosos,
        "fallidos" : fallidos,
    }