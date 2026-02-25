# sina/settings/config.py

from pathlib import Path
from datetime import date
import locale
locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def find_project_root(start_path: Path, marker_file: str = "pyproject.toml") -> Path:
    current = start_path.resolve()
    while not (current / marker_file).exists() and current != current.parent:
        current = current.parent
    return current

BASE_DIR = find_project_root(Path(__file__))

# --- Datos existentes ---
DATA = BASE_DIR / "datos"
CASA_LEY_DATA = DATA / "casa_ley" 
VECTORS_DIR = DATA / "vectorstores"

# --- Anotador (nuevo) ---
RECORTES_DIR = CASA_LEY_DATA / "recortes"
DATASET_DIR = DATA / "dataset"
DATASET_IMAGES = DATASET_DIR / "images"
DATASET_LABELS = DATASET_DIR / "labels"
DATASET_ANNOTATED = DATASET_DIR / "annotated"

# --- Templates y estáticos ---
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

CLASSES = BASE_DIR / "src" / "sina" / "config" / "classes.json"

for path in [
    DATA, 
    CASA_LEY_DATA, 
    VECTORS_DIR,
    RECORTES_DIR, 
    DATASET_IMAGES, 
    DATASET_LABELS, 
    DATASET_ANNOTATED,
    TEMPLATES_DIR, 
    STATIC_DIR,
]:
    path.mkdir(parents=True, exist_ok=True)

# --- Clases para anotación ---
ANNOTATION_CLASSES = [
    "frutas_verduras",
    "carnes",
    "abarrotes",
    "lacteos",
    "ofertas_especiales",
    "banner",
    "cosmeticos",
    "otros",
]


