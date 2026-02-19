# main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
from typing import List

from sina.config.settings import TEMPLATES_DIR, STATIC_DIR, CASA_LEY_DATA
from sina.processing_img.image_segmentation import process_annotations
from sina.scraping.casa_ley import get_flyer


app = FastAPI(title="SINA - Data Annotation & Scraping Hub")

# ============================================================
#  STATIC MOUNTS
# ============================================================
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/datos", StaticFiles(directory=str(CASA_LEY_DATA)), name="datos")

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
    store_name: str       # ej. "casa_ley", "walmart"
    image_filename: str   # ej. "2026-02-19_pagina_01.jpg"
    boxes: List[BoundingBox]

# ============================================================
#  FRONTEND ROUTES
# ============================================================

@app.get("/annotator", response_class=HTMLResponse)
async def get_annotator(request: Request):
    """Renders the HTML UI for the bounding box annotator."""
    
    # Ideally, you will read the actual files inside CASA_LEY_DATA dynamically here.
    # For now, we pass dummy data so the UI renders correctly.
    available_images = [
        "2026-02-19/pagina_01.jpg", 
        "2026-02-19/pagina_02.jpg"
    ]
    
    # The categories you want to train your model on
    annotation_classes = ["frutas_verduras", "carnes", "abarrotes", "ofertas_especiales", "otros"]
    
    # Matching HEX colors for the UI and OpenCV drawing
    class_colors = {
        "frutas_verduras": "#2ecc71", # Green
        "carnes": "#e74c3c",          # Red
        "abarrotes": "#f1c40f",       # Yellow
        "ofertas_especiales": "#9b59b6", # Purple
        "otros": "#95a5a6"            # Gray
    }
    
    return templates.TemplateResponse("annotator.html", {
        "request": request,
        "images": available_images,
        "classes": annotation_classes,
        "colors": class_colors
    })

# ============================================================
#  API ENDPOINTS
# ============================================================

@app.post("/sina/scraper/{store_name}")
def trigger_scraper(store_name: str, city: str, url: str):
    """
    Generic endpoint to trigger web scraping for different retailers.
    Implements the Factory pattern to route to the correct scraper.
    """
    match store_name:
        case "casa_ley":
            # Asumiendo que get_flyer guarda en la ruta correcta configurada en settings
            get_flyer(city, url, str(CASA_LEY_DATA))
            return {"status": "success", "message": f"Scraping completado para {store_name} en {city}"}
        case "walmart":
            # from sina.scraping.walmart import get_walmart_flyer
            # get_walmart_flyer(...)
            return {"status": "pending", "message": "Scraper de Walmart en desarrollo"}
    
    raise HTTPException(status_code=404, detail="Supermercado no soportado")

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