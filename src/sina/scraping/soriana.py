"""
Orquestador de scraping Soriana.
Consulta el catálogo de rutas y ejecuta extracciones basadas en esos datos.
"""

from typing import List, Dict, Any
from sina.db.repository import CatalogoRepository
from sina.scraping.helpers import scrape_soriana_page, guardar_productos_en_db, contar_productos
from sina.config.credentials import DB_URL
from playwright.sync_api import sync_playwright


def scrape_soriana() -> List[Dict[str, Any]]:
    """
    Extracción completa de Soriana usando el catálogo de rutas.
    
    Complejidad: O(r) donde r = número de rutas activas en DB.
    """
    print("🐝 Iniciando Spider Soriana...")
    
    # 1. Obtener rutas activas de DB
    repo = CatalogoRepository()
    rutas_activas = repo.obtener_rutas_activas()
    
    if not rutas_activas:
        print("❌ No hay rutas activas en el catálogo.")
        return []
    
    print(f"📋 Encontradas {len(rutas_activas)} rutas activas")
    
    productos_extraidos = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            for route in rutas_activas:
                print(f"\n📦 {route['departamento']} > {route['categoria']}")
                
                # 2. Construir URL completa desde el catálogo
                url = f"{route['tienda']}{route['url_path']}"
                
                # 3. Navegar y extraer
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                
                productos = scrape_soriana_page(
                    page=page,
                    url=url,
                    depto=route['departamento'],
                    categoria=route['categoria']
                )
                
                # 4. Guardar en DB
                guardados = guardar_productos_en_db(productos)
                productos_extraidos.extend(productos)
            
            print(f"\n✅ EXTRACCIÓN FINALIZADA: {len(productos_extraidos)} productos")
            print(f"   Total en DB: {contar_productos()}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            browser.close()
    
    return productos_extraidos


def main():
    """Ejemplo de uso."""
    print("🚀 Ejecutando scraper Soriana...")
    productos = scrape_soriana()
    
    print(f"\n✅ Total productos: {len(productos)}")
    for p in productos[:5]:
        print(f"   - {p['producto']} (${p['precio']}) - {p['departamento']} > {p['categoria']}")


if __name__ == "__main__":
    main()
