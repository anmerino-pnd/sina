from sina.config.paths import TEMPLATES_DIR, STATIC_DIR, DATA, CLASSES
from pathlib import Path
import json 

def get_classes_config() -> dict:
    """Reads the classes and colors from the JSON configuration file."""
       
    with open(CLASSES, "r", encoding="utf-8") as f:
        return json.load(f)
    
def build_filesystem_tree(base_path: Path) -> dict:
    """
    Scans the DATA directory and builds a nested dictionary:
    { "casa_ley": { "hermosillo": { "2026-02-19": ["pagina_01.jpg", ...] } } }
    Ignores non-store folders like 'vectorstores' or 'dataset'.
    """
    tree = {}
    ignore_dirs = {"vectorstores", "dataset", "recortes"}
    
    if not base_path.exists():
        return tree

    for store_dir in base_path.iterdir():
        if store_dir.is_dir() and store_dir.name not in ignore_dirs:
            store = store_dir.name
            tree[store] = {}
            
            for city_dir in store_dir.iterdir():
                if city_dir.is_dir() and city_dir.name not in ignore_dirs:
                    city = city_dir.name
                    tree[store][city] = {}
                    
                    for date_dir in city_dir.iterdir():
                        if date_dir.is_dir():
                            date_str = date_dir.name
                            # Find all jpg/png files
                            images = [img.name for img in date_dir.glob("*.[jp][pn]*g")]
                            if images:
                                tree[store][city][date_str] = sorted(images)
    return tree