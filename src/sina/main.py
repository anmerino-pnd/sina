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
from sina.scraping.gas import df_gas_prices, GAS_COLUMN_MAP, GAS_FLOAT_COLS

from sina.config.credentials import (
    DB_URL,
    casa_ley_url
)
from sina.config.settings import (
    get_classes_config,
    build_filesystem_tree
)

from sina.config.paths import (
    TEMPLATES_DIR, 
    CASA_LEY_DATA,
    STATIC_DIR, 
    CLASSES,
    DATA, 
    GAS_DATA
)

try:
    from sina.ollama.extract_flyer_text import extract_text
except ImportError:
    extract_text = None 

from sina.db.repository import QQPRepository, GasolinaRepository

app = FastAPI(title="SINA - Data Annotation & Scraping Hub")

# ============================================================
#  STATIC MOUNTS
# ============================================================
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/datos", StaticFiles(directory=str(DATA)), name="datos")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def get_classes_config() -> dict:
    """Reads the classes and colors from the JSON configuration file."""
       
    with open(CLASSES, "r", encoding="utf-8") as f:
        return json.load(f)

# ============================================================
#  HELPERS GASOLINA
# ============================================================
MUNICIPIOS_JSON = GAS_DATA / "catalogo_municipios.json"

def _load_catalogo() -> dict:
    with open(MUNICIPIOS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def _build_catalogo_js(mun_dict: dict) -> dict:
    """
    Construye dos objetos para el frontend:
      - CATALOGO:         { estado: [municipio, ...] }
      - DATOS_DISPONIBLES ya se llena dinámicamente en la ruta
    """
    return {
        estado: sorted(info["municipios"].keys())
        for estado, info in mun_dict.items()
    }

# ============================================================
#  FRONTEND ROUTES
# ============================================================

@app.get("/annotator", response_class=HTMLResponse)
async def get_annotator(request: Request):
    """Renders the HTML UI dynamically passing the filesystem tree and config."""
    
    class_config = get_classes_config()
    annotation_classes = list(class_config.keys())
    
    file_tree = build_filesystem_tree(DATA)
    
    return templates.TemplateResponse("annotator.html", {
        "request": request,
        "file_tree": file_tree,  
        "classes": annotation_classes,
        "colors": class_config
    })

@app.get("/gasolina", response_class=HTMLResponse)
async def get_gasolina(request: Request):
    """
    Renderiza el mapa de gasolina inyectando el catálogo
    de estados/municipios en el template.
    """
    mun_dict = _load_catalogo()
    catalogo = _build_catalogo_js(mun_dict)

    return templates.TemplateResponse("gasolina.html", {
        "request":  request,
        "catalogo": json.dumps(catalogo,  ensure_ascii=False),
    })

# ============================================================
#  API ENDPOINTS
# ============================================================

@app.post("/sina/annotate")
def save_and_crop_annotations(payload: AnnotationPayload):
    """
    Receives bounding box coordinates from the UI, crops the image, 
    and saves the dataset files for future model training.
    """
    try:
        result = process_annotations(
            supermarket=payload.supermarket,
            city=payload.city,
            date=payload.date,
            image_name=payload.image_name,
            bboxes=payload.bboxes
        )
        return {"status": "success", "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # MAGIA: Esto imprimirá la línea exacta del error en tu terminal negra
        print("\nERROR INTERNO EN /sina/annotate:")
        traceback.print_exc()
        print("----------------------------------\n")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/sina/flyer")
def get_flyer(payload: FlyerPayload):
    match payload.supermarket:
        case "Casa Ley" | "casa_ley":
            return download_flyer(
                city = payload.city,
                base_url = casa_ley_url,
                base_dir = str(CASA_LEY_DATA)
            )
        case "Walmart":
            pass
        case "Bodega Aurrera":
            pass
        case "Soriana":
            pass

@app.post("/sina/extract_text")
def extract_crops_data(payload: ExtractPayload):
    """
    Checks if flyer_data.json exists. If not, runs the LLM extraction.
    Returns the JSON content to be displayed in the UI.
    """
    json_path = DATA / payload.supermarket / payload.city / payload.date / "flyer_data.json"

    if not json_path.exists():
        if extract_text is None:
            raise HTTPException(status_code=500, detail="Extraction module not found.")
            
        print(f"Inciando LLM para {payload.supermarket} - {payload.city} - {payload.date}")
        
        success = extract_text(
            supermarket=payload.supermarket,
            city=payload.city,
            date=payload.date
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to generate the document with the LLM.")
    else:
        print(f"flyer_data.json already exists for {payload.date}. Loading directly...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"status": "success", "data": data}
    except Exception as e:
        print("\nERROR READING JSON:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error reading JSON file: {e}")

@app.get("/sina/status")
def check_status(supermarket: str, city: str, date: str):
    """Verifica si existen recortes y si ya se generó el flyer_data.json"""
    base_dir = DATA / supermarket / city / date
    json_path = base_dir / "flyer_data.json"
    recortes_dir = base_dir / "recortes"

    has_json = json_path.exists()
    
    has_recortes = recortes_dir.exists() and any(recortes_dir.iterdir())

    return {
        "has_json": has_json,
        "has_recortes": has_recortes
    }

@app.get("/sina/gasolina")
async def get_precios_gasolina(estado: str, municipio: str):
    """
    Llama a la API de la CRE y devuelve los precios del municipio.
    El frontend llama a este endpoint al hacer clic en 'Ver precios'.
    """
    try:
        df = df_gas_prices(estado, municipio)

        cols_base = ["Numero", "Nombre", "Direccion", "Latitud", "Longitud",
                     "Magna", "Premium", "Diesel"]
        cols_out  = [c for c in cols_base if c in df.columns]

        registros = df[cols_out].where(df[cols_out].notna(), other=None).to_dict(orient="records")

        return {
            "status":    "ok",
            "estado":    estado,
            "municipio": municipio,
            "total":     len(registros),
            "datos":     registros,
        }

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró '{municipio}' en '{estado}' en el catálogo."
        )
    except Exception as e:
        print("\nERROR EN /sina/gasolina:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/sina/update/qqp")
async def actualizar_qqp():
    """
    Descarga el CSV más reciente de QQP, borra los datos anteriores
    y reinserta los nuevos.
    """
    try:
        repo = QQPRepository(db_url=DB_URL)

        print("Descargando datos QQP...")
        df = extract_qqp()

        print("Convirtiendo a registros...")
        registros = df_to_dict(
                    df,
                    column_map=QQP_COLUMN_MAP,
                    float_cols=QQP_FLOAT_COLS
                )

        print("Borrando datos anteriores...")
        repo.borrar_todo()

        print("Insertando nuevos datos...")
        repo.guardar_en_bulk(registros)

        total = repo.contar()

        return {
            "status": "ok",
            "registros_insertados": len(registros),
            "total_en_db": total
        }

    except Exception as e:
        print("\nERROR EN /sina/update/qqp:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/sina/update/gas")
async def actualizar_gas(estado: str, municipio: str):
    """
    Descarga el CSV más reciente de QQP, borra los datos anteriores
    y reinserta los nuevos.
    """
    try:
        repo = GasolinaRepository(db_url=DB_URL)

        print("Descargando datos Gas...")
        df = df_gas_prices(estado, municipio)

        print("Convirtiendo a registros...")
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

        print("Borrando datos anteriores...")
        repo.borrar_todo()

        print("Insertando nuevos datos...")
        repo.guardar_en_bulk(registros)

        total = repo.contar()

        return {
            "status": "ok",
            "registros_insertados": len(registros),
            "total_en_db": total
        }

    except Exception as e:
        print("\nERROR EN /sina/update/gas:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))