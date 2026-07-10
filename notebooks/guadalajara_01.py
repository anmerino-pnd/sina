"""
Explorador de arbol de categorias de Farmacias Guadalajara (Super Farmacia).

Plataforma: Salesforce Commerce Cloud (Demandware, "Sites-fragua-Site") — la
misma que Soriana. El menu se renderiza en el servidor, asi que curl_cffi +
BeautifulSoup basta (sin navegador).

Solo tomamos las pestañas SUPER, FARMACIA y DERMO. NO incluimos "Ofertas":
es una vista promocional que re-lista los mismos productos (mismos pid) de las
otras pestañas -> solaparia resultados. Los descuentos igual se capturan porque
el spider lee el precio vigente de cada categoria.

De Dermo excluimos las vistas de filtro (/dermo/marcas/*, /dermo/tipo-de-piel*)
porque tambien re-listan productos ya cubiertos por las categorias reales.

Genera src/sina/config/guadalajara_config.json con la forma:
    {
        "super/alimentos": {
            "despensa": {
                "url_path": "/super/alimentos/despensa",
                "nombre_visible": "Despensa",
                "prioridad": 1
            },
            ...
        },
        ...
    }

Instalar: uv add curl_cffi beautifulsoup4
"""
import json
from urllib.parse import urlsplit, unquote
from bs4 import BeautifulSoup
from curl_cffi import requests
from pathlib import Path

BASE_URL = "https://www.farmaciasguadalajara.com"
CONFIG_PATH = Path("src/sina/config/guadalajara_config.json")

TABS = ("super", "farmacia", "dermo")
# Segmentos de Dermo que son filtros (marca / tipo de piel), no categorias reales.
DERMO_EXCLUIR = ("marcas", "tipo-de-piel")


def _path_limpio(href: str) -> str:
    """Path decodificado, sin dominio, sin query, sin barra final."""
    if not href:
        return ""
    path = urlsplit(href).path
    path = unquote(path)
    return path.rstrip("/")


def _es_categoria(path: str) -> bool:
    """True si el path es una categoria scrapeable de super/farmacia/dermo."""
    if not path or path.endswith(".html"):
        return False
    segs = [s for s in path.split("/") if s]
    # /tab/departamento[/categoria] -> 2 o 3 segmentos
    if len(segs) < 2 or len(segs) > 3 or segs[0] not in TABS:
        return False
    if segs[0] == "dermo" and segs[1] in DERMO_EXCLUIR:
        return False
    return True


def extraer_arbol_guadalajara() -> None:
    print("Iniciando Explorador para Farmacias Guadalajara (SFCC, curl_cffi)...")

    try:
        print("Descargando HTML de la home...")
        response = requests.get(BASE_URL, impersonate="chrome120", timeout=40)

        if response.status_code != 200:
            print(f"Error al conectar: HTTP {response.status_code}")
            return

        print("Parseando el menu...")
        soup = BeautifulSoup(response.text, "html.parser")

        # Recolectar (path -> nombre_visible) de los enlaces de menu de las 3 pestañas.
        candidatos: dict[str, str] = {}
        for a in soup.select("a[href]"):
            path = _path_limpio(a.get("href", ""))
            if not _es_categoria(path):
                continue
            texto = a.get_text(strip=True)
            # Nos quedamos con el primer texto no vacio para cada path.
            if path not in candidatos or (not candidatos[path] and texto):
                candidatos[path] = texto

        if not candidatos:
            print("No se encontraron categorias. Cambio el sitio o fuimos bloqueados?")
            with open("error_guadalajara.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("   Revisa 'error_guadalajara.html' para depurar.")
            return

        # Poda de prefijos: si un path es padre (prefijo) de otro, es un
        # departamento-landing cuyas categorias ya cubren sus productos -> se descarta
        # para no solapar padre/hijo.
        todos = set(candidatos)
        hojas = {
            p for p in todos
            if not any(otro != p and otro.startswith(p + "/") for otro in todos)
        }

        print(f"Categorias hoja detectadas: {len(hojas)} (de {len(candidatos)} candidatas)")

        config_final: dict = {}
        contador_prioridad = 1
        for path in sorted(hojas):
            segs = [s for s in path.split("/") if s]
            departamento = "/".join(segs[:-1])   # p. ej. "super/alimentos" o "dermo"
            categoria = segs[-1]
            nombre = candidatos[path] or categoria

            config_final.setdefault(departamento, {})[categoria] = {
                "url_path": path,
                "nombre_visible": nombre,
                "prioridad": contador_prioridad,
            }
            contador_prioridad += 1

    except Exception as e:
        print(f"Ocurrio un error inesperado: {e}")
        return

    print("\nGuardando guadalajara_config.json...")
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config_limpia = {k: v for k, v in config_final.items() if v}

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_limpia, f, ensure_ascii=False, indent=4)

    total_cats = sum(len(v) for v in config_limpia.values())
    por_tab: dict[str, int] = {}
    for dep, cats in config_limpia.items():
        tab = dep.split("/")[0]
        por_tab[tab] = por_tab.get(tab, 0) + len(cats)

    print("PROCESO FINALIZADO!")
    print(f" Departamentos guardados: {len(config_limpia)}")
    print(f" Categorias guardadas: {total_cats}")
    print(f" Por pestaña: {por_tab}")


if __name__ == "__main__":
    extraer_arbol_guadalajara()
