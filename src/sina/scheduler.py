"""
Scheduler de actualización automática de pipelines (Fase 1).

Usa APScheduler en background con horario de México (America/Mexico_City):
  - Gasolina: diario 06:00
  - Gas LP:   sábados 08:00

Refresca solo las ubicaciones/localidades que YA tienen datos en la DB
(las que los usuarios han consultado), reutilizando la lógica de caché
on-demand de `get_precios_gasolina()` y `get_precios_gas_lp()`. A las horas
programadas los datos ya están vencidos, así que esas funciones vuelven a
llamar a la API de gobierno y refrescan la DB.

Se controla con la variable de entorno `ENABLE_SCHEDULER` (default: activado).
"""
import os
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from sina.config.timezone import MEXICO_TZ
from sina.config.credentials import DB_URL
from sina.db.repository import GasolinaRepository, GasLPRepository, MunicipioRepository

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def refrescar_gasolina() -> None:
    """Re-scrapea precios de gasolina para los municipios ya presentes en DB."""
    from sina.scraping.gobierno.cre_gasolina import get_precios_gasolina

    repo = GasolinaRepository(db_url=DB_URL)
    mun_repo = MunicipioRepository(db_url=DB_URL)
    ubicaciones = repo.ubicaciones_con_precios()
    log.info("[scheduler] Gasolina: refrescando %d municipios", len(ubicaciones))

    for estado, municipio in ubicaciones:
        ids = mun_repo.obtener_ids(estado, municipio)
        if not ids:
            log.warning("[scheduler] Sin IDs para %s/%s, omitido", estado, municipio)
            continue
        entidad_id, municipio_id = ids
        try:
            get_precios_gasolina(estado, municipio, entidad_id, municipio_id)
        except Exception as e:
            log.error("[scheduler] Error refrescando gasolina %s/%s: %s", estado, municipio, e)


def refrescar_gas_lp() -> None:
    """Re-scrapea precios de gas LP para las localidades ya presentes en DB."""
    from sina.scraping.gobierno.cne_gas_lp import get_precios_gas_lp

    repo = GasLPRepository(db_url=DB_URL)
    combinaciones = repo.combinaciones_con_datos()
    log.info("[scheduler] Gas LP: refrescando %d localidades", len(combinaciones))

    for c in combinaciones:
        try:
            get_precios_gas_lp(
                c["entidad_nombre"], c["municipio_nombre"], c["localidad_nombre"]
            )
        except Exception as e:
            log.error(
                "[scheduler] Error refrescando gas LP %s/%s/%s: %s",
                c["entidad_nombre"], c["municipio_nombre"], c["localidad_nombre"], e,
            )


def _scheduler_habilitado() -> bool:
    return os.getenv("ENABLE_SCHEDULER", "1").strip().lower() in ("1", "true", "yes", "on")


def iniciar_scheduler() -> BackgroundScheduler | None:
    """Arranca el scheduler en background. No hace nada si está deshabilitado."""
    global _scheduler

    if not _scheduler_habilitado():
        log.info("[scheduler] Deshabilitado (ENABLE_SCHEDULER).")
        return None

    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=MEXICO_TZ)
    _scheduler.add_job(
        refrescar_gasolina,
        CronTrigger(hour=6, minute=0, timezone=MEXICO_TZ),
        id="gasolina_diario",
        replace_existing=True,
    )
    _scheduler.add_job(
        refrescar_gas_lp,
        CronTrigger(day_of_week="sat", hour=8, minute=0, timezone=MEXICO_TZ),
        id="gas_lp_semanal",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("[scheduler] Iniciado (gasolina 06:00 diario, gas LP sáb 08:00, hora MX).")
    return _scheduler


def detener_scheduler() -> None:
    """Detiene el scheduler si está corriendo."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("[scheduler] Detenido.")
