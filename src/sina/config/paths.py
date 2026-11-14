# sina/config/paths.py

from pathlib import Path
import locale
locale.setlocale(locale.LC_TIME, "es_MX.UTF-8")


def find_project_root(start_path: Path, marker_file: str = "pyproject.toml") -> Path:
    current = start_path.resolve()
    while not (current / marker_file).exists() and current != current.parent:
        current = current.parent
    return current

BASE_DIR = find_project_root(Path(__file__))

# --- Datos existentes ---
DATA = BASE_DIR / "datos"
DB = DATA / "db"
SEEDS_DATA = DATA / "seeds"
# Volantes (flyers) agrupados bajo datos/flyers/ para que el anotador liste solo
# tiendas de volantes (no db/ ni seeds/).
FLYERS_DATA = DATA / "flyers"
CASA_LEY_DATA = FLYERS_DATA / "casa_ley"
ABARREY_DATA = FLYERS_DATA / "abarrey"

# --- Logs ---
LOGS = BASE_DIR / "logs"

# --- Templates y estáticos ---
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

CLASSES = BASE_DIR / "src" / "sina" / "config" / "classes.json"
FLYER_CIUDADES = BASE_DIR / "src" / "sina" / "config" / "flyer_ciudades.json"
SORIANA_CONFIG = BASE_DIR / "src" / "sina" / "config" / "soriana_config.json"
DELSOL_CONFIG = BASE_DIR / "src" / "sina" / "config" / "delsol_config.json"
BENAVIDES_CONFIG = BASE_DIR / "src" / "sina" / "config" / "benavides_config.json"
GUADALAJARA_CONFIG = BASE_DIR / "src" / "sina" / "config" / "guadalajara_config.json"

for path in [
    DB,
    DATA,
    SEEDS_DATA,
    FLYERS_DATA,
    CASA_LEY_DATA,
    ABARREY_DATA,
    TEMPLATES_DIR,
    STATIC_DIR,
    LOGS,
]:
    path.mkdir(parents=True, exist_ok=True)

CATALOGO_MUNICIPIOS_PATH = SEEDS_DATA / "catalogo_municipios.json"
LOCALIDADES_PARQUET_PATH = SEEDS_DATA / "cne_localidades.parquet"
UBICACIONES_GASOLINERAS_PARQUET_PATH = SEEDS_DATA / "ubicaciones_gasolineras.parquet"
CLASES_JSON_PATH = CLASSES
SORIANA_CONFIG_PATH = SORIANA_CONFIG
DELSOL_CONFIG_PATH = DELSOL_CONFIG
BENAVIDES_CONFIG_PATH = BENAVIDES_CONFIG
GUADALAJARA_CONFIG_PATH = GUADALAJARA_CONFIG

