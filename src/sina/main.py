# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json

from sina.config.paths import (
    TEMPLATES_DIR, 
    CASA_LEY_DATA,
    STATIC_DIR, 
    CLASSES,
    DATA, 
)
from sina.processing.image_segmentation import process_annotations
from sina.scraping.casa_ley import get_ley_flyer
from sina.config.settings import (
    get_classes_config,
    build_filesystem_tree
)
from sina.config.credentials import (
    AnnotationPayload,
    FlyerPayload,
    casa_ley_url
)

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
        # Pass the validated payload data to your heavy-lifting backend function
        result = process_annotations(
            store_name=payload.store_name,
            image_name=payload.image_filename,
            boxes=payload.boxes
        )
        return {"status": "success", "data": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/sina/flyer")
def get_flyer(payload: FlyerPayload):
    match payload.supermarket:
        case "Casa Ley":
            return get_ley_flyer(
                city = payload.city,
                url = casa_ley_url,
                folder = CASA_LEY_DATA
            )
        case "Walmart":
            pass
        case "Bodega Aurrera":
            pass
        case "Soriana":
            pass