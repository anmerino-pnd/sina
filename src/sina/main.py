# main.py
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import cast
from sqlalchemy import select
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
import logging
import time
import json

from sina.annotator.image_segmentation import (
    process_annotations,
    resolver_ruta_flyer,
    AnnotationPayload,
    ExtractPayload,
    FlyerPayload,
    PreanotarPayload,
    PersistirPayload,
)
from sina.annotator.zonas import detectar_zonas
from sina.annotator.records import df_to_dict
from sina.scraping.supermercados.casaley_spider import download_flyer
from sina.scraping.gobierno.cre_gasolina import (
    scrape_municipio,
    transform_gas_prices,
    get_precios_gasolina
)
from sina.scraping.gobierno.cne_gas_lp import get_precios_gas_lp, get_localidades_by_municipio
from sina.config.credentials import DB_URL, casa_ley_url
from sina.config.settings import _get_classes_config, _get_flyer_ciudades, build_filesystem_tree
from sina.config.paths import (
    TEMPLATES_DIR,
    CASA_LEY_DATA,
    STATIC_DIR,
    DATA,
    BASE_DIR,
)
from sina.config.canasta import (
    estructurar_canasta
)
from sina.db.repository import (
    GasolinaRepository,
    GasLPRepository,
    SupermercadoRepository,
    MunicipioRepository,
)
from sina.db.models import EntidadFederativa, Municipio, Localidad
from sina.config.logging_config import configurar_logging
from sina.scheduler import iniciar_scheduler, detener_scheduler

# ── Fase 4: auth, seguridad, rate limiting y servido de la SPA ──
from sina.api.auth import router as auth_router
from sina.api.users import router as users_router
from sina.api.chat import router as chat_router
from sina.api.ratelimit import limiter
from sina.api.security import SecurityHeadersMiddleware, require_admin
from sina.config.app_settings import settings

log = logging.getLogger(__name__)

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

# Extracción por ZONA (VLM estructurado + validación). Import defensivo: si falta
# alguna dependencia, el endpoint responde con error claro en vez de romper el arranque.
try:
    from sina.vlm.extraccion import extraer_recortes
except Exception:  # noqa: BLE001
    extraer_recortes = None

# ============================================================
#  APP & MOUNTS
# ============================================================
_municipios_validos: set[str] = set()
_catalogo_js: dict            = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranque: logging, catálogo de municipios (una vez) y scheduler."""
    configurar_logging()
    global _municipios_validos, _catalogo_js
    repo = MunicipioRepository(db_url=DB_URL)
    _municipios_validos = repo.obtener_nombres_validos()
    _catalogo_js        = repo.obtener_catalogo()
    iniciar_scheduler()
    yield
    detener_scheduler()

app = FastAPI(
    title       = "SINA API",
    description = "Sistema de Información de precios y anotaciones",
    version     = "1.0.0",
    lifespan=lifespan
)

# ── Seguridad y rate limiting (Fase 4) ──────────────────────
def _rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Adaptador tipado para el handler 429 de slowapi (conserva Retry-After)."""
    return _rate_limit_exceeded_handler(request, cast(RateLimitExceeded, exc))

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
# Sin este middleware los `default_limits` del limiter no aplican a nada:
# solo regirían los endpoints decorados explícitamente (/auth/google, /chat).
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
if settings.cors_origins:
    # Solo se activa CORS si hay orígenes configurados (frontend separado).
    # En mismo-origen (SPA servida por FastAPI) no hace falta.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

# ── Routers de auth y usuarios (Fase 4) + chat (Fase 3) ─────
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(chat_router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/datos",  StaticFiles(directory=str(DATA)),       name="datos")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ============================================================
#  HELPERS
# ============================================================
def _validar_ubicacion(estado: str, municipio: str) -> tuple[str, str, int, str]:
    e = estado.strip().lower()
    m = municipio.strip().lower()
    if e not in _municipios_validos or m not in _municipios_validos:
        raise HTTPException(status_code=400, detail="Estado o municipio no válido.")

    repo = MunicipioRepository(db_url=DB_URL)
    ids  = repo.obtener_ids(e, m)
    if not ids:
        raise HTTPException(status_code=400, detail="Combinación estado/municipio no encontrada.")

    entidad_id, municipio_id = ids
    return e, m, entidad_id, municipio_id


# ============================================================
#  API · SALUD
# ============================================================
_HEALTH_TTL = 60  # segundos; los health-checks frecuentes no deben pegar a la DB
_health_cache: tuple[float, dict] | None = None

@app.get("/api/v1/health")
def health(response: Response):
    """Vigencia de los datos por categoría (última actualización + vigente)."""
    global _health_cache
    ahora = time.monotonic()
    if _health_cache is None or ahora - _health_cache[0] > _HEALTH_TTL:
        _health_cache = (ahora, {
            "status"       : "ok",
            "gasolina"     : GasolinaRepository(db_url=DB_URL).estado_cache(),
            "gas_lp"       : GasLPRepository(db_url=DB_URL).estado_cache(),
            "supermercados": SupermercadoRepository(db_url=DB_URL).estado_cache(),
        })
    response.headers["Cache-Control"] = "public, max-age=60"
    return _health_cache[1]


# ============================================================
#  API · CATÁLOGO (estado → municipios) para la SPA
# ============================================================
@app.get("/api/v1/catalogo")
def get_catalogo(response: Response):
    """
    Catálogo { estado: [municipios] } que la SPA usa para los selectores.
    Reemplaza la inyección del catálogo en el HTML de Jinja. Se sirve desde
    el cache calentado en el lifespan; cae al repositorio si aún no está listo.
    """
    response.headers["Cache-Control"] = "public, max-age=3600"
    if _catalogo_js:
        return {"estados": _catalogo_js}
    return {"estados": MunicipioRepository(db_url=DB_URL).obtener_catalogo()}


# ============================================================
#  FRONTEND ROUTES  (HTML)
# ============================================================
@app.get("/sina/annotator", response_class=HTMLResponse)
async def view_annotator(request: Request):
    """
    Shell del anotador (sin datos sensibles). El navegador no puede mandar headers
    en la navegación inicial, así que la página en sí no va admin-gated; el árbol de
    archivos y todas las acciones se cargan vía endpoints que SÍ exigen `X-Admin-Key`
    (la UI lo toma de un campo y lo adjunta en cada fetch). Clase única: `zona`.
    """
    class_config = _get_classes_config()
    return templates.TemplateResponse("annotator.html", {
        "request" : request,
        "classes" : ["zona"],
        "colors"  : {"zona": class_config.get("zona", "#7a2492")},
        "ciudades": _get_flyer_ciudades(),
    })


@app.get("/api/v1/annotator/tree")
def get_annotator_tree(_admin: None = Depends(require_admin)):
    """Árbol de datos/ (supermercado→ciudad→fecha→archivos). Requiere clave admin."""
    return {"tree": build_filesystem_tree(DATA)}

@app.get("/sina/gasolina", response_class=HTMLResponse)
async def view_gasolina(request: Request):
    """UI de precios de gasolina."""
    return templates.TemplateResponse("gasolina.html", {
        "request" : request,
        "catalogo": json.dumps(_catalogo_js, ensure_ascii=False),
    })

@app.get("/sina/gas-lp", response_class=HTMLResponse)
async def view_gas_lp(request: Request):
    """UI de precios de Gas LP."""
    return templates.TemplateResponse("gas_lp.html", {
        "request" : request,
        "catalogo": json.dumps(_catalogo_js, ensure_ascii=False),
    })

# Endpoint UI QQP removido (deprecado)

# ============================================================
#  API · GASOLINA
# ============================================================
@app.get("/api/v1/gasolina")
def get_gasolina(estado: str, municipio: str):
    estado, municipio, entidad_id, municipio_id = _validar_ubicacion(estado, municipio)

    try:
        resultado = get_precios_gasolina(estado, municipio, entidad_id, municipio_id)

        if resultado.get("status") == "error":
            raise HTTPException(status_code=503, detail=resultado["detail"])

        if resultado["total"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Sin datos para {municipio}, {estado}."
            )

        return resultado

    except HTTPException:
        raise
    except Exception:
        log.exception("Error obteniendo precios de gasolina")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")

@app.post("/api/v1/update/gasolina")
def update_gasolina(estado: str, municipio: str, _admin: None = Depends(require_admin)):
    """
    Descarga precios desde la API CRE y hace upsert en DB.
    Preserva lat/lng ya scrapeadas. Requiere clave de administrador.
    """
    estado, municipio, entidad_id, municipio_id = _validar_ubicacion(estado, municipio)
    registros = transform_gas_prices(estado, municipio, entidad_id, municipio_id)

    try:
        repo      = GasolinaRepository(db_url=DB_URL)
        repo.upsert_precios(registros)

        return {
            "status"   : "ok",
            "estado"   : estado,
            "municipio": municipio,
            "actualizados": len(registros),
            "total_en_db" : repo.contar(),
        }

    except Exception:
        log.exception("Error actualizando precios de gasolina")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")

@app.post("/api/v1/update/ubicacion/gasolineras")
def update_ubicaciones_gasolineras(
    estado: str, municipio: str, _admin: None = Depends(require_admin)
):
    estado, municipio, _, _ = _validar_ubicacion(estado, municipio)
    registros = scrape_municipio(estado, municipio)

    try:
        repo      = GasolinaRepository(db_url=DB_URL)
        repo.upsert_ubicaciones(registros)

        return {
            "status"   : "ok",
            "estado"   : estado,
            "municipio": municipio,
            "actualizados": len(registros),
            "total_en_db" : repo.contar(),
        }

    except Exception:
        log.exception("Error actualizando ubicaciones de gasolineras")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")

# ============================================================
#  API · GAS LP
# ============================================================
@app.get("/api/v1/gas-lp")
def get_gas_lp(estado: str, municipio: str, localidad: str):
    """
    Precios de Gas LP por localidad.
    Caché semanal on-demand — llama a CNE solo si los datos vencieron.
    """
    try:
        resultado = get_precios_gas_lp(estado, municipio, localidad)

        if "error" in resultado:
            status = 404 if "no encontrada" in resultado["error"].lower() else 503
            raise HTTPException(status_code=status, detail=resultado["error"])

        return resultado

    except HTTPException:
        raise
    except Exception:
        log.exception("Error obteniendo precios de gas LP")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")

@app.get("/api/v1/gas-lp/localidades")
def get_localidades(estado: str, municipio: str):
    """
    Devuelve localidades disponibles para un estado/municipio.
    """
    estado = estado.strip().lower()
    municipio = municipio.strip().lower()

    if estado not in _municipios_validos or municipio not in _municipios_validos:
        raise HTTPException(status_code=400, detail="Estado o municipio no válido.")

    repo = MunicipioRepository(db_url=DB_URL)
    ids = repo.obtener_ids(estado, municipio)
    if not ids:
        raise HTTPException(status_code=404, detail="Combinación estado/municipio no encontrada.")

    entidad_id, municipio_id = ids
    localidades = get_localidades_by_municipio(entidad_id, municipio_id)

    return {
        "estado": estado,
        "municipio": municipio,
        "entidad_id": entidad_id,
        "municipio_id": municipio_id,
        "localidades": localidades,
    }

@app.get("/api/v1/gas-lp/by-ids")
def get_gas_lp_by_ids(entidad_id: int, municipio_id: str, localidad_id: int):
    """
    Precios de Gas LP usando IDs directamente (más eficiente para UI).
    Caché semanal on-demand — llama a CNE solo si los datos vencieron.
    """
    # Resolver nombres desde DB
    repo = MunicipioRepository(db_url=DB_URL)

    with repo.Session() as session:
        entidad = session.get(EntidadFederativa, entidad_id)
        if not entidad:
            raise HTTPException(status_code=404, detail="Entidad no encontrada.")

        mun_row = session.execute(
            select(Municipio).where(
                Municipio.entidad_id == entidad_id,
                Municipio.municipio_id == municipio_id,
            )
        ).scalars().first()
        if not mun_row:
            raise HTTPException(status_code=404, detail="Municipio no encontrado.")

        loc_row = session.execute(
            select(Localidad).where(
                Localidad.localidad_id == localidad_id,
            )
        ).scalars().first()
        if not loc_row:
            raise HTTPException(status_code=404, detail="Localidad no encontrada.")

    estado = entidad.nombre.lower()
    municipio = mun_row.nombre.lower()
    localidad = str(loc_row.nombre)

    try:
        resultado = get_precios_gas_lp(estado, municipio, localidad)

        if "error" in resultado:
            status = 404 if "no encontrada" in resultado["error"].lower() else 503
            raise HTTPException(status_code=status, detail=resultado["error"])

        return resultado

    except HTTPException:
        raise
    except Exception:
        log.exception("Error obteniendo precios de gas LP por IDs")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")

# ============================================================
#  API · SUPERMERCADOS
# ============================================================
@app.get("/api/v1/supermercados")
def get_supermercados(
    q: str | None = None,
    tienda: str | None = None,
    departamento: str | None = None,
    categoria: str | None = None,
    limit: int = 30,
):
    """
    Productos de supermercado con filtros (tienda/departamento/categoría).
    Si `q` viene y hay embeddings disponibles, usa búsqueda semántica
    (pgvector); si no, búsqueda de texto por nombre ordenada por precio.
    """
    try:
        repo = SupermercadoRepository(db_url=DB_URL)
        datos = repo.buscar(
            q=q, tienda=tienda, departamento=departamento,
            categoria=categoria, limit=limit,
        )
        return {
            "status": "ok",
            "q":      q,
            "total":  len(datos),
            "datos":  datos,
        }
    except Exception:
        log.exception("Error buscando productos de supermercado")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")


# ============================================================
#  API · QQP (DEPRECATED)
# ============================================================
# Endpoints QQP removidos a favor del web scraping directo (Soriana, Del Sol, etc.)

# ============================================================
#  API · ANNOTATOR
# ============================================================
@app.post("/api/v1/annotator/annotate")
def annotate(payload: AnnotationPayload, _admin: None = Depends(require_admin)):
    """Guarda bounding boxes y genera recortes. Requiere clave de administrador."""
    try:
        result = process_annotations(
            supermarket=payload.supermarket,
            city       =payload.city,
            date       =payload.date,
            image_name =payload.image_name,
            bboxes     =payload.bboxes,
        )
        return {"status": "ok", "data": result}
    except ValueError:
        raise HTTPException(status_code=400, detail="Parámetros de ruta no válidos.")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    except Exception:
        log.exception("Error procesando anotaciones")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")


@app.post("/api/v1/annotator/flyer")
def download_flyer_endpoint(payload: FlyerPayload, _admin: None = Depends(require_admin)):
    """Descarga el volante del supermercado indicado. Requiere clave de administrador."""
    match payload.supermarket:
        case "Casa Ley" | "casa_ley":
            return download_flyer(
                city    =payload.city,
                base_url=casa_ley_url,
                base_dir=str(CASA_LEY_DATA),
            )
        case _:
            raise HTTPException(
                status_code=501,
                detail=f"Supermercado '{payload.supermarket}' no implementado aún."
            )


@app.post("/api/v1/annotator/preanotar")
def preanotar_zonas(payload: PreanotarPayload, _admin: None = Depends(require_admin)):
    """
    Propone zonas de recorte (CV clásico) para que el humano las ajuste. NO persiste.
    Requiere clave de administrador.
    """
    try:
        image_path = resolver_ruta_flyer(
            payload.supermarket, payload.city, payload.date, payload.image_name
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Parámetros de ruta no válidos.")
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    try:
        zonas = detectar_zonas(image_path, tienda=payload.supermarket)
    except Exception:
        log.exception("Error en pre-anotación de zonas")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    return {"status": "ok", "zonas": zonas}


@app.post("/api/v1/annotator/extract")
def extract_flyer_text(payload: ExtractPayload, _admin: None = Depends(require_admin)):
    """
    Extrae productos POR ZONA (recorte) con el VLM, salida estructurada y validada.
    Re-ejecutable (sin caché por archivo). Requiere clave de administrador.
    """
    if extraer_recortes is None:
        raise HTTPException(status_code=500, detail="Módulo de extracción no disponible.")
    try:
        data = extraer_recortes(payload.supermarket, payload.city, payload.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Parámetros de ruta no válidos.")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # VLM deshabilitado o no inicializado.
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        log.exception("Error extrayendo zonas del flyer")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    return {"status": "ok", "data": data}


@app.post("/api/v1/annotator/persistir")
def persistir_flyer(payload: PersistirPayload, _admin: None = Depends(require_admin)):
    """
    Inserta a Postgres los productos YA verificados por el humano
    (`supermercados`, fuente=flyer + vigencia). Requiere clave de administrador.
    """
    from datetime import date as _date

    productos = payload.productos or []
    if not productos:
        raise HTTPException(status_code=400, detail="No hay productos para insertar.")
    if len(productos) > 2000:
        raise HTTPException(status_code=413, detail="Demasiados productos en una sola inserción.")

    def _parse_fecha(d: str | None):
        if not d:
            return None
        try:
            return _date.fromisoformat(d)
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha de vigencia inválida (YYYY-MM-DD).")

    vi = _parse_fecha(payload.vigencia_inicio)
    vf = _parse_fecha(payload.vigencia_fin)

    try:
        n = SupermercadoRepository(db_url=DB_URL).upsert_flyer_productos(
            productos=productos,
            tienda=(payload.tienda or "").strip() or "Desconocida",
            fuente=(payload.fuente or "flyer").strip(),
            vigencia_inicio=vi,
            vigencia_fin=vf,
        )
    except Exception:
        log.exception("Error insertando productos de flyer")
        raise HTTPException(status_code=500, detail="Error interno del servidor.")
    return {"status": "ok", "insertados": n}


@app.get("/api/v1/annotator/status")
def get_annotator_status(
    supermarket: str, city: str, date: str, _admin: None = Depends(require_admin)
):
    """Verifica si existen recortes y flyer_data.json para una fecha. Requiere clave de administrador."""
    try:
        base_dir = resolver_ruta_flyer(supermarket, city, date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Parámetros de ruta no válidos.")

    recortes_dir = base_dir / "recortes"

    return {
        "has_json"    : (base_dir / "flyer_data.json").exists(),
        "has_recortes": recortes_dir.exists() and any(recortes_dir.iterdir()),
    }


# ============================================================
#  SPA REACT (Fase 4) — servida por FastAPI en el mismo origen
# ============================================================
# El build de Vite vive en frontend/dist. Montamos los assets con hash y un
# catch-all que devuelve index.html para que el routing de cliente y los
# deep-links funcionen. Debe registrarse DESPUÉS de todas las rutas /api,
# /static, /datos y /sina para no ensombrecerlas.
if (FRONTEND_DIST / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="spa-assets",
    )

_SPA_INDEX = FRONTEND_DIST / "index.html"
_RESERVED_PREFIXES = ("api/", "static/", "datos/", "sina/", "assets/")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_catch_all(full_path: str):
    """Sirve la SPA. 404 JSON para rutas de API/estáticos no existentes."""
    if full_path.startswith(_RESERVED_PREFIXES):
        raise HTTPException(status_code=404, detail="No encontrado.")

    # Archivos reales en la raíz del build (favicon, sina-mark.svg, robots…).
    if full_path:
        candidato = (FRONTEND_DIST / full_path).resolve()
        if (
            candidato.is_file()
            and candidato.is_relative_to(FRONTEND_DIST.resolve())
        ):
            return FileResponse(str(candidato))

    # Cualquier otra ruta → index.html (routing de cliente / deep-links).
    if _SPA_INDEX.is_file():
        return FileResponse(str(_SPA_INDEX))

    # Aún no se ha corrido `vite build`.
    raise HTTPException(
        status_code=503,
        detail="La SPA no está compilada. Corre `npm run build` en frontend/.",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)