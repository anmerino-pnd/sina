import os
from dotenv import load_dotenv
from sina.config.paths import DB

load_dotenv()

qqp_url : str = os.getenv('QQP_DATOS_URL', "")
datos_abiertos_url: str = os.getenv('DATOS_ABIERTOS_URL', "")
gasolina_hmo_url: str = os.getenv('GASOLINA_HMO_URL', "")
casa_ley_url: str = os.getenv('CASA_LEY_URL', "")
gasolina_api_rest: str = os.getenv('GASOLINA_API_REST', '')
gasolineras_ubi: str = os.getenv('GASOLINERAS_UBI', '')

ollama_api_key : str = os.getenv('OLLAMA_API_KEY', "")
google_api_key: str = os.getenv('GOOGLE_API_KEY', "")

cne_refere : str = os.getenv('CNE_REFER', "")

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
    print(f"🗄️  Usando SQLite local: {db_path}")
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