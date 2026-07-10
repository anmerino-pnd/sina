import os
from dotenv import load_dotenv
from sina.config.paths import DB

load_dotenv()

qqp_url : str = os.getenv('QQP_DATOS_URL', "")
datos_abiertos_url: str = os.getenv('DATOS_ABIERTOS_URL', "")
gasolina_hmo_url: str = os.getenv('GASOLINA_HMO_URL', "")
casa_ley_url: str = os.getenv('CASA_LEY_URL', "")

ollama_api_key : str = os.getenv('OLLAMA_API_KEY', "")
google_api_key: str = os.getenv('GOOGLE_API_KEY', "")

gasolina_api_rest: str = os.getenv('GASOLINA_API_REST', '')
gasolineras_ubi: str = os.getenv('GASOLINERAS_UBI', '')

cne_refer : str = os.getenv('CNE_REFER', "")
cne_localidades_url: str = os.getenv('CNE_LOCALIDADES_URL', "")
cne_precios_gas_lp_url: str = os.getenv('CNE_PRECIOS_GAS_LP_URL', "")

# ── URLs base de supermercados (dominio; el url_path vive en los *_config.json) ──
# Con default para que el scraping funcione aunque el .env no las declare.
soriana_base_url: str = os.getenv('SORIANA_BASE_URL', "https://www.soriana.com").rstrip("/")
delsol_base_url: str = os.getenv('DELSOL_BASE_URL', "https://www.delsol.com.mx").rstrip("/")
benavides_base_url: str = os.getenv('BENAVIDES_BASE_URL', "https://www.benavides.com.mx").rstrip("/")
guadalajara_base_url: str = os.getenv('GUADALAJARA_BASE_URL', "https://www.farmaciasguadalajara.com").rstrip("/")

def get_db_url() -> str:
    """
    Si existen las variables de entorno de DB remota, construye la URL de PostgreSQL.
    Si no, usa SQLite local como fallback.
    """
    host     = os.getenv("DB_HOST")
    port     = os.getenv("DB_PORT", "5432")
    name     = os.getenv("DB_NAME")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if all([host, name, user, password]):
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        print(f"🐘 Conectando a PostgreSQL: {host}:{port}/{name}")
        return url

    db_path = DB / "sina_data.db"
    print(f"Usando SQLite local: {db_path}")
    return f"sqlite:///{db_path}"

DB_URL: str = get_db_url()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9",
}