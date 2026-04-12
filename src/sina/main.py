# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from sqlalchemy import select
import traceback
import json

from sina.processing.image_segmentation import (
    process_annotations,
    AnnotationPayload,
    ExtractPayload,
    FlyerPayload,
)
from sina.processing.records import df_to_dict
from sina.scraping.casa_ley import download_flyer
from sina.scraping.qqp import extract_qqp, QQP_COLUMN_MAP, QQP_FLOAT_COLS, QQP_DATETIME_COLS
from sina.scraping.gas import (
    scrape_municipio,
    transform_gas_prices,
    get_precios_gasolina
)
from sina.scraping.gas_lp import get_precios_gas_lp, get_localidades_by_municipio
from sina.config.credentials import DB_URL, casa_ley_url
from sina.config.settings import _get_classes_config, build_filesystem_tree
from sina.config.paths import (
    TEMPLATES_DIR, CASA_LEY_DATA, STATIC_DIR, DATA
)
from sina.db.repository import QQPRepository, GasolinaRepository, MunicipioRepository
from sina.db.models import EntidadFederativa, Municipio, Localidad

try:
    from sina.ollama.extract_flyer_text import extract_text
except ImportError:
    extract_text = None

# ============================================================
#  APP & MOUNTS
# ============================================================
_municipios_validos: set[str] = set()
_catalogo_js: dict            = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el catálogo desde la DB al arrancar. Una sola vez."""
    global _municipios_validos, _catalogo_js
    repo = MunicipioRepository(db_url=DB_URL)
    _municipios_validos = repo.obtener_nombres_validos()
    _catalogo_js        = repo.obtener_catalogo()
    yield

app = FastAPI(
    title       = "SINA API",
    description = "Sistema de Información de precios y anotaciones",
    version     = "1.0.0",
    lifespan=lifespan
)

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
#  FRONTEND ROUTES  (HTML)
# ============================================================
@app.get("/sina/annotator", response_class=HTMLResponse)
async def view_annotator(request: Request):
    """UI de anotación de volantes."""
    class_config = _get_classes_config()
    return templates.TemplateResponse("annotator.html", {
        "request" : request,
        "file_tree": build_filesystem_tree(DATA),
        "classes" : list(class_config.keys()),
        "colors"  : class_config,
    })

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

# ============================================================
#  API · GASOLINA
# ============================================================
@app.get("/api/v1/gasolina")
async def get_gasolina(estado: str, municipio: str):
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
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/update/gasolina")
async def update_gasolina(estado: str, municipio: str):
    """
    Descarga precios desde la API CRE y hace upsert en DB.
    Preserva lat/lng ya scrapeadas.
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

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/update/ubicacion/gasolineras")
async def update_ubicaciones_gasolineras(estado: str, municipio: str):
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

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
# ============================================================
#  API · GAS LP
# ============================================================
@app.get("/api/v1/gas-lp")
async def get_gas_lp(estado: str, municipio: str, localidad: str):
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
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/gas-lp/localidades")
async def get_localidades(estado: str, municipio: str):
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
async def get_gas_lp_by_ids(entidad_id: int, municipio_id: str, localidad_id: int):
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
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
#  API · QQP
# ============================================================
@app.post("/api/v1/update/qqp")
async def update_qqp():
    """
    Descarga el CSV más reciente de QQP y reemplaza los datos en DB.
    """
    try:
        repo      = QQPRepository(db_url=DB_URL)
        df        = extract_qqp()
        registros = df_to_dict(df, column_map=QQP_COLUMN_MAP, float_cols=QQP_FLOAT_COLS, datetime_cols=QQP_DATETIME_COLS)

        repo.borrar_todo()
        repo.guardar_en_bulk(registros)

        return {
            "status"     : "ok",
            "insertados" : len(registros),
            "total_en_db": repo.contar(),
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
#  API · ANNOTATOR
# ============================================================
@app.post("/api/v1/annotator/annotate")
def annotate(payload: AnnotationPayload):
    """Guarda bounding boxes y genera recortes."""
    try:
        result = process_annotations(
            supermarket=payload.supermarket,
            city       =payload.city,
            date       =payload.date,
            image_name =payload.image_name,
            bboxes     =payload.bboxes,
        )
        return {"status": "ok", "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/annotator/flyer")
def download_flyer_endpoint(payload: FlyerPayload):
    """Descarga el volante del supermercado indicado."""
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


@app.post("/api/v1/annotator/extract")
def extract_flyer_text(payload: ExtractPayload):
    """Extrae texto de recortes usando LLM. Usa caché si ya existe."""
    json_path = DATA / payload.supermarket / payload.city / payload.date / "flyer_data.json"

    if not json_path.exists():
        if extract_text is None:
            raise HTTPException(status_code=500, detail="Módulo de extracción no disponible.")

        success = extract_text(
            supermarket=payload.supermarket,
            city       =payload.city,
            date       =payload.date,
        )
        if not success:
            raise HTTPException(status_code=500, detail="Error al generar documento con LLM.")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return {"status": "ok", "data": json.load(f)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/annotator/status")
def get_annotator_status(supermarket: str, city: str, date: str):
    """Verifica si existen recortes y flyer_data.json para una fecha."""
    base_dir     = DATA / supermarket / city / date
    recortes_dir = base_dir / "recortes"

    return {
        "has_json"    : (base_dir / "flyer_data.json").exists(),
        "has_recortes": recortes_dir.exists() and any(recortes_dir.iterdir()),
    }