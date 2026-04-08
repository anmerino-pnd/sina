# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from datetime import date
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
from sina.scraping.qqp import extract_qqp, QQP_COLUMN_MAP, QQP_FLOAT_COLS
from sina.scraping.gas import (
    _load_catalogo,
    _build_catalogo_js,
    _build_municipios_validos,
    transform_gas_prices,
)
# from sina.pipeline.gas import pipeline_nacional
from sina.config.credentials import DB_URL, casa_ley_url
from sina.config.settings import _get_classes_config, build_filesystem_tree
from sina.config.paths import (
    TEMPLATES_DIR, CASA_LEY_DATA, STATIC_DIR, DATA
)
from sina.db.repository import QQPRepository, GasolinaRepository

try:
    from sina.ollama.extract_flyer_text import extract_text
except ImportError:
    extract_text = None

# ============================================================
#  APP & MOUNTS
# ============================================================
_mun_dict      = _load_catalogo()
_municipios_ok = _build_municipios_validos(_mun_dict)

app = FastAPI(
    title       = "SINA API",
    description = "Sistema de Información de precios y anotaciones",
    version     = "1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/datos",  StaticFiles(directory=str(DATA)),       name="datos")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ============================================================
#  HELPERS
# ============================================================
def _validar_ubicacion(estado: str, municipio: str) -> tuple[str, str]:
    """Valida y normaliza estado/municipio. Lanza 400 si no son válidos."""
    e = estado.strip().lower()
    m = municipio.strip().lower()
    if e not in _municipios_ok or m not in _municipios_ok:
        raise HTTPException(status_code=400, detail="Estado o municipio no válido.")
    return e, m


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
    catalogo = _build_catalogo_js(_mun_dict)
    return templates.TemplateResponse("gasolina.html", {
        "request" : request,
        "catalogo": json.dumps(catalogo, ensure_ascii=False),
    })

# ============================================================
#  API · GASOLINA
# ============================================================
@app.get("/api/v1/gasolina")
async def get_gasolina(estado: str, municipio: str):
    """
    Consulta precios de gasolineras desde la DB.
    Fuente: scraping (lat/lng) + CRE API (precios).
    """
    estado, municipio = _validar_ubicacion(estado, municipio)

    try:
        repo      = GasolinaRepository(db_url=DB_URL)
        registros = repo.obtener_por_municipio(estado, municipio)

        if not registros:
            raise HTTPException(
                status_code=404,
                detail=f"Sin datos para {municipio}, {estado}. "
                       f"Ejecuta POST /api/v1/gasolina/update primero."
            )

        return {
            "status"   : "ok",
            "estado"   : estado,
            "municipio": municipio,
            "total"    : len(registros),
            "datos"    : registros,
        }

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
    estado, municipio = _validar_ubicacion(estado, municipio)

    try:
        repo      = GasolinaRepository(db_url=DB_URL)
        registros = transform_gas_prices(estado, municipio)
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


# @app.post("/api/v1/gasolina/pipeline")
# async def run_pipeline_gasolina(estados: list[str] | None = None):
#     """
#     Dispara el pipeline nacional de scraping de ubicaciones.
#     Filtra por estados si se especifican.
#     """
#     try:
#         resultado = await pipeline_nacional(estados_filtro=estados)
#         return {"status": "ok", **resultado}
#     except Exception as e:
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))

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
        registros = df_to_dict(df, column_map=QQP_COLUMN_MAP, float_cols=QQP_FLOAT_COLS)

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