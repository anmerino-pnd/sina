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
import shutil
import hashlib
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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


def refrescar_supermercados() -> None:
    """
    Re-scrapea el catálogo de productos de los supermercados (Soriana, Del Sol,
    Benavides). Cada tienda se aísla en su propio try/except para que el fallo de
    una no tumbe a las demás.

    Ojo: Soriana y Del Sol usan navegador (Playwright), es un job pesado; por eso
    va aparte de gasolina/gas LP y semanal en horario de baja demanda.
    """
    tiendas = [
        ("Soriana",               "sina.scraping.supermercados.soriana_spider",     "scrape_soriana"),
        ("Del Sol",               "sina.scraping.supermercados.delsol_spider",      "scrape_delsol"),
        ("Benavides",             "sina.scraping.supermercados.benavides_spider",   "scrape_benavides"),
        ("Farmacias Guadalajara", "sina.scraping.supermercados.guadalajara_spider", "scrape_guadalajara"),
    ]
    for nombre, modulo, funcion in tiendas:
        try:
            import importlib
            spider = getattr(importlib.import_module(modulo), funcion)
            log.info("[scheduler] Supermercados: scrapeando %s", nombre)
            spider()
        except Exception as e:
            log.error("[scheduler] Error scrapeando %s: %s", nombre, e)


def _hash_imagenes(carpeta) -> frozenset:
    """Huella del contenido de un flyer: hashes de sus imágenes (orden-agnóstico)."""
    hashes = set()
    for img in carpeta.glob("*.[jp][pn]*g"):
        hashes.add(hashlib.md5(img.read_bytes()).hexdigest())
    return frozenset(hashes)


def refrescar_flyers() -> dict:
    """
    Monitor de vigencias de volantes. Corre cada FLYERS_INTERVALO_MIN minutos y
    es barato-primero: si ningún flyer está vencido, solo lee metadatos del
    filesystem y termina. Cuando la vigencia real conocida de un flyer ya pasó
    (cualquier día, cualquier duración — sin supuestos de calendario), intenta
    descargar el nuevo; si la tienda aún publica el mismo (imágenes idénticas),
    limpia la carpeta recién creada y el siguiente tick reintenta.

    Devuelve un resumen de acciones (queda en la auditoría `registro_jobs`).
    """
    from sina.config.paths import FLYERS_DATA
    from sina.annotator.ciclo import resumen_pendientes

    spiders = _spiders_flyers()
    detalles: dict = {"vencidos": 0, "nuevos": [], "duplicados": [], "errores": []}

    for estado in resumen_pendientes():
        if estado["vencido"] is not True:
            continue  # vigente, o vigencia desconocida (sin base para actuar)

        detalles["vencidos"] += 1
        tienda, ciudad = estado["tienda"], estado["ciudad"]
        spider = spiders.get(tienda)
        if spider is None:
            log.warning("[scheduler] Flyers: sin spider para '%s', omitido.", tienda)
            detalles["errores"].append(f"{tienda}/{ciudad}: sin spider")
            continue

        ciudad_dir = FLYERS_DATA / tienda / ciudad
        anterior = ciudad_dir / estado["fecha"]
        fechas_previas = {d.name for d in ciudad_dir.iterdir() if d.is_dir()}

        log.info("[scheduler] Flyers: %s/%s vencido (%s), descargando...",
                 tienda, ciudad, estado["vigencia_fin"])
        try:
            spider(ciudad)
        except Exception as e:
            log.error("[scheduler] Flyers: error descargando %s/%s: %s", tienda, ciudad, e)
            detalles["errores"].append(f"{tienda}/{ciudad}: {e}")
            continue

        # Anti-duplicado: si la descarga creó una carpeta nueva pero con las
        # mismas imágenes, la tienda aún no publica el flyer nuevo.
        nuevas = {d.name for d in ciudad_dir.iterdir() if d.is_dir()} - fechas_previas
        for fecha_nueva in nuevas:
            nueva_dir = ciudad_dir / fecha_nueva
            if _hash_imagenes(nueva_dir) == _hash_imagenes(anterior):
                shutil.rmtree(nueva_dir)
                detalles["duplicados"].append(f"{tienda}/{ciudad}")
                log.info(
                    "[scheduler] Flyers: %s/%s aún publica el flyer anterior; "
                    "se limpió %s y se reintenta en el siguiente tick.",
                    tienda, ciudad, fecha_nueva,
                )
            else:
                detalles["nuevos"].append(f"{tienda}/{ciudad}/{fecha_nueva}")
                log.info("[scheduler] Flyers: %s/%s flyer NUEVO en %s.",
                         tienda, ciudad, fecha_nueva)
    return detalles


def _spiders_flyers() -> dict:
    """Spider por carpeta de tienda. Firma unificada: f(ciudad) -> bool."""
    from sina.config.paths import CASA_LEY_DATA, ABARREY_DATA
    from sina.config.credentials import casa_ley_url, abarrey_url

    spiders: dict = {}

    def _ley(ciudad: str) -> bool:
        if not casa_ley_url:
            log.warning("[scheduler] Flyers: CASA_LEY_URL vacía, Casa Ley omitida.")
            return False
        from sina.scraping.supermercados.casaley_spider import download_flyer
        return download_flyer(base_url=casa_ley_url, city=ciudad, base_dir=str(CASA_LEY_DATA))

    def _abarrey(ciudad: str) -> bool:
        from sina.scraping.supermercados.abarrey_spider import download_flyer
        return download_flyer(base_url=abarrey_url, city=ciudad, base_dir=str(ABARREY_DATA))

    spiders["casa_ley"] = _ley
    spiders["abarrey"] = _abarrey
    return spiders


def _con_registro(nombre: str, fn, solo_con_actividad: bool = False):
    """
    Envuelve un job para auditar cada corrida en Mongo (`registro_jobs`): job,
    inicio/fin, duración, éxito y detalles (si el job devuelve un dict). Con
    Mongo caído el registro degrada a no-op — la auditoría jamás tumba al job.

    `solo_con_actividad=True` (para jobs de intervalo corto, ej. el monitor de
    flyers): los ticks cuyo dict de detalles viene todo vacío/cero NO se
    registran — sin él serían ~72 documentos-ruido al día.
    """
    def _job() -> None:
        from sina.config.timezone import get_mexico_now
        from sina.db.stores import RegistroJobsStore

        inicio = get_mexico_now()
        try:
            resultado = fn()
        except Exception as e:
            RegistroJobsStore().registrar(
                nombre, inicio, get_mexico_now(), ok=False, error=str(e)
            )
            raise
        detalles = resultado if isinstance(resultado, dict) else {}
        if solo_con_actividad and not any(detalles.values()):
            return
        RegistroJobsStore().registrar(
            nombre, inicio, get_mexico_now(), ok=True, detalles=detalles
        )

    _job.__name__ = f"registro_{nombre}"
    return _job


def _scheduler_habilitado() -> bool:
    return os.getenv("ENABLE_SCHEDULER", "1").strip().lower() in ("1", "true", "yes", "on")


def _supermercados_habilitado() -> bool:
    # Desactivado por defecto: es un job pesado (navegador) que casi nunca quieres
    # correr dentro del proceso web. Actívalo explícitamente donde toque.
    return os.getenv("ENABLE_SUPERMERCADOS_SCRAPING", "0").strip().lower() in ("1", "true", "yes", "on")


def _flyers_habilitado() -> bool:
    # Desactivado por defecto: Casa Ley abre Chrome (Selenium). Actívalo en UNA
    # sola instancia (no hay lock multi-instancia, igual que supermercados).
    return os.getenv("ENABLE_FLYERS_SCRAPING", "0").strip().lower() in ("1", "true", "yes", "on")


def _flyers_intervalo_min() -> int:
    try:
        return max(1, int(os.getenv("FLYERS_INTERVALO_MIN", "20")))
    except ValueError:
        return 20


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
        _con_registro("gasolina", refrescar_gasolina),
        CronTrigger(hour=6, minute=0, timezone=MEXICO_TZ),
        id="gasolina_diario",
        replace_existing=True,
    )
    _scheduler.add_job(
        _con_registro("gas_lp", refrescar_gas_lp),
        CronTrigger(day_of_week="sat", hour=8, minute=0, timezone=MEXICO_TZ),
        id="gas_lp_semanal",
        replace_existing=True,
    )

    # Scraping de supermercados: pesado (navegador), opt-in por env aparte.
    if _supermercados_habilitado():
        _scheduler.add_job(
            _con_registro("supermercados", refrescar_supermercados),
            CronTrigger(day_of_week="sun", hour=4, minute=0, timezone=MEXICO_TZ),
            id="supermercados_semanal",
            replace_existing=True,
        )
        log.info("[scheduler] Job de supermercados habilitado (dom 04:00, hora MX).")

    # Monitor de vigencias de volantes: intervalo corto porque los ticks son
    # baratos cuando nada está vencido; el reintento tras un vencimiento sin
    # flyer nuevo publicado sale gratis del propio intervalo. Opt-in por env.
    if _flyers_habilitado():
        minutos = _flyers_intervalo_min()
        _scheduler.add_job(
            _con_registro("flyers", refrescar_flyers, solo_con_actividad=True),
            IntervalTrigger(minutes=minutos, timezone=MEXICO_TZ),
            id="flyers_monitor",
            replace_existing=True,
            max_instances=1,   # un tick lento (Selenium) nunca se encima con el siguiente
            coalesce=True,
        )
        log.info("[scheduler] Monitor de flyers habilitado (cada %d min).", minutos)

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
