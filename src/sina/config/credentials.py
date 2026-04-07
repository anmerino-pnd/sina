import os
from dotenv import load_dotenv

load_dotenv()

qqp_url : str = os.getenv('QQP_DATOS_URL', "")
datos_abiertos_url: str = os.getenv('DATOS_ABIERTOS_URL', "")
gasolina_hmo_url: str = os.getenv('GASOLINA_HMO_URL', "")
casa_ley_url: str = os.getenv('CASA_LEY_URL', "")
gasolina_api_rest: str = os.getenv('GASOLINA_API_REST', '')

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

    print("🗄️  Usando SQLite local: sina_data.db")
    return "sqlite:///sina_data.db"

DB_URL: str = get_db_url()