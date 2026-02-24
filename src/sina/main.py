# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from typing import List
import json

from sina.config.paths import TEMPLATES_DIR, STATIC_DIR, DATA, CLASSES
from sina.processing_img.image_segmentation import process_annotations
from sina.scraping.casa_ley import get_flyer
from sina.config.settings import (
    get_classes_config,
    build_filesystem_tree
)

app = FastAPI(title="SINA - Data Annotation & Scraping Hub")

# ============================================================
#  STATIC MOUNTS
# ============================================================
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/datos", StaticFiles(directory=str(DATA)), name="datos")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ============================================================
#  DATA MODELS (Pydantic Validation)
# ============================================================

class BoundingBox(BaseModel):
    label: str
    x: int
    y: int
    w: int
    h: int

class AnnotationPayload(BaseModel):
    store_name: str       
    image_filename: str   
    boxes: List[BoundingBox]

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
    
    # 1. Load dynamic classes
    class_config = get_classes_config()
    annotation_classes = list(class_config.keys())
    
    # 2. Build dynamic file tree
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