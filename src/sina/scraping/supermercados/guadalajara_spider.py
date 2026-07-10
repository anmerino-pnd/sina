"""
Spider de Farmacias Guadalajara (Super Farmacia).

Lee las rutas activas de `catalogos_config` (tienda="Farmacias Guadalajara"),
scrapea cada categoria con curl_cffi + BeautifulSoup (SFCC server-side, sin
navegador) y hace upsert de los productos.

Ejecutar:  python -m sina.scraping.supermercados.guadalajara_spider
"""
from typing import List, Dict, Any

from sina.config.credentials import guadalajara_base_url
from sina.db.repository import CatalogoRepository, SupermercadoRepository
from sina.scraping.supermercados.guadalajara_helper import scrape_guadalajara_page

TIENDA = "Farmacias Guadalajara"


def scrape_guadalajara() -> List[Dict[str, Any]]:
    """Extraccion completa de Farmacias Guadalajara usando el catalogo de rutas."""
    print("[*] Iniciando Spider Farmacias Guadalajara...")

    repo_catalogo = CatalogoRepository()
    rutas_activas = repo_catalogo.obtener_rutas_activas(tienda=TIENDA)

    if not rutas_activas:
        print(f"[!] No hay rutas activas en el catalogo para {TIENDA}.")
        return []

    print(f"[*] Encontradas {len(rutas_activas)} rutas activas")
    productos_extraidos: List[Dict[str, Any]] = []
    repo_sup = SupermercadoRepository()

    for route in rutas_activas:
        print(f"\n[*] Procesando: {route['departamento']} > {route['categoria']}")
        try:
            productos = scrape_guadalajara_page(
                base_url=guadalajara_base_url,
                url_path=route["url_path"],
                depto=route["departamento"],
                categoria=route["categoria"],
            )
        except Exception as e:
            print(f"[X] Error en {route['url_path']}: {e}")
            continue

        if productos:
            repo_sup.upsert_productos(productos)
            productos_extraidos.extend(productos)
            repo_catalogo.actualizar_ultima_extraccion(route["id"])

    print(f"\n[OK] EXTRACCION FINALIZADA: {len(productos_extraidos)} productos extraidos.")
    return productos_extraidos


def main() -> None:
    print("[*] Ejecutando orquestador Farmacias Guadalajara...")
    productos = scrape_guadalajara()
    for p in productos[:3]:
        print(f"   - {p['producto']} (${p['precio']})")


if __name__ == "__main__":
    main()
