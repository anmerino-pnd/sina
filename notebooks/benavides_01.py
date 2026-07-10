"""
Explorador de arbol de categorias de Farmacias Benavides (Magento).

Equivalente a `woolworth_01.py` (Del Sol) pero para Benavides:
  - Del Sol corre sobre VTEX; Benavides corre sobre Magento (tema "Never8").
  - El menu de Benavides SI se renderiza en el HTML del servidor, asi que
    curl_cffi + BeautifulSoup basta (no necesitamos navegador).

Genera src/sina/config/benavides_config.json con la forma:
    {
        "medicamentos": {
            "dolor": {
                "url_path": "/medicamentos-dolor",
                "nombre_visible": "Dolor",
                "prioridad": 1
            },
            ...
        },
        ...
    }

Ese archivo lo consume el seeder (`seed_catalogo_tienda`) para poblar
catalogos_config con tienda="Benavides".

Instalar: uv add curl_cffi beautifulsoup4
"""
import json
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from curl_cffi import requests
from pathlib import Path

BASE_URL = "https://www.benavides.com.mx"
CONFIG_PATH = Path("src/sina/config/benavides_config.json")


def _url_path(href: str) -> str:
    """Deja solo el path de un href absoluto o relativo (sin dominio ni query)."""
    if not href:
        return ""
    partes = urlsplit(href)
    return partes.path.rstrip("/") or "/"


def extraer_arbol_benavides() -> None:
    print("Iniciando Explorador para Benavides (Magento, curl_cffi)...")

    try:
        print("Descargando HTML de la home...")
        response = requests.get(BASE_URL, impersonate="chrome120", timeout=30)

        if response.status_code != 200:
            print(f"Error al conectar: HTTP {response.status_code}")
            return

        print("Parseando el DOM con BeautifulSoup...")
        soup = BeautifulSoup(response.text, "html.parser")

        # Menu principal de Magento
        nav = soup.select_one("nav.navigation")
        if not nav:
            print("No se encontro 'nav.navigation'. Cambio el sitio o fuimos bloqueados?")
            with open("error_benavides.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("   Revisa 'error_benavides.html' para depurar.")
            return

        departamentos_li = nav.select("li.level0")
        print(f"Se detectaron {len(departamentos_li)} departamentos (level0).")

        config_final: dict = {}
        contador_prioridad = 1

        for li_depto in departamentos_li:
            # Enlace principal del departamento (level-top)
            a_depto = li_depto.select_one("a.level-top") or li_depto.find("a")
            if not a_depto:
                continue

            depto_path = _url_path(a_depto.get("href", ""))
            depto_key = depto_path.strip("/")
            if not depto_key:
                continue

            config_final.setdefault(depto_key, {})

            # Categorias del departamento (level1 anidados en su submenu)
            categorias_a = li_depto.select("li.level1 > a")

            # Algunos departamentos (Bienestar Sexual, Alimentos y Hogar, Promociones)
            # no tienen subcategorias, pero SU propia pagina si lista productos.
            # En ese caso registramos el departamento como una ruta "general".
            if not categorias_a:
                config_final[depto_key]["general"] = {
                    "url_path": depto_path,
                    "nombre_visible": a_depto.get_text(strip=True),
                    "prioridad": contador_prioridad,
                }
                contador_prioridad += 1
                continue

            for a_cat in categorias_a:
                cat_nombre = a_cat.get_text(strip=True)
                cat_path = _url_path(a_cat.get("href", ""))
                cat_slug = cat_path.strip("/")
                if not cat_slug:
                    continue

                # La URL de Benavides es de un solo segmento: "/medicamentos-dolor".
                # Como categoria usamos el slug sin el prefijo del departamento.
                if cat_slug.startswith(depto_key + "-"):
                    categoria_key = cat_slug[len(depto_key) + 1:]
                else:
                    categoria_key = cat_slug

                config_final[depto_key][categoria_key] = {
                    "url_path": cat_path,
                    "nombre_visible": cat_nombre,
                    "prioridad": contador_prioridad,
                }
                contador_prioridad += 1

    except Exception as e:
        print(f"Ocurrio un error inesperado: {e}")
        return

    print("\nGuardando benavides_config.json...")
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Filtramos departamentos sin categorias
    config_limpia = {k: v for k, v in config_final.items() if v}

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_limpia, f, ensure_ascii=False, indent=4)

    total_cats = sum(len(v) for v in config_limpia.values())
    print("PROCESO FINALIZADO!")
    print(f" Departamentos guardados: {len(config_limpia)}")
    print(f" Categorias guardadas: {total_cats}")


if __name__ == "__main__":
    extraer_arbol_benavides()
