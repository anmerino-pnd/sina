from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from sina.config.credentials import soriana_base_url
from sina.db.repository import CatalogoRepository, SupermercadoRepository
from sina.scraping.supermercados.soriana_helper import scrape_soriana_page
from sina.scraping.supermercados.interfaces import BrowserConfig

def scrape_soriana(config: BrowserConfig = BrowserConfig()) -> List[Dict[str, Any]]:
    """
    Extracción completa de Soriana usando el catálogo de rutas.
    """
    print("🐝 Iniciando Spider Soriana...")
    
    repo_catalogo = CatalogoRepository()
    rutas_activas = repo_catalogo.obtener_rutas_activas(tienda="Soriana")
    
    if not rutas_activas:
        print("❌ No hay rutas activas en el catálogo.")
        return []
    
    print(f"📋 Encontradas {len(rutas_activas)} rutas activas")
    
    productos_extraidos: List[Dict[str, Any]] = []
    
    with sync_playwright() as p:
        browser: Browser = p.chromium.launch(headless=config.headless)
        context: BrowserContext = browser.new_context(**config.to_playwright_context())
        page: Page = context.new_page()
        
        try:
            for route in rutas_activas:
                print(f"\n📦 {route['departamento']} > {route['categoria']}")
                
                url = f"{soriana_base_url}{route['url_path']}"
                
                page.goto(url, wait_until="domcontentloaded", timeout=config.timeout_ms)
                page.wait_for_timeout(2000)
                
                productos = scrape_soriana_page(
                    page=page,
                    url=url,
                    depto=route['departamento'],
                    categoria=route['categoria']
                )
                productos_extraidos.extend(productos)
                
                repo_sup = SupermercadoRepository()
                repo_sup.upsert_productos(productos)
                repo_catalogo.actualizar_ultima_extraccion(route['id'])
            
            print(f"\n✅ EXTRACCIÓN FINALIZADA: {len(productos_extraidos)} productos")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            browser.close()
    
    return productos_extraidos

def main() -> None:
    print("🚀 Ejecutando scraper Soriana...")
    productos = scrape_soriana()
    
    print(f"\n✅ Total productos: {len(productos)}")
    for p in productos[:5]:
        print(f"   - {p['producto']} (${p['precio']}) - {p['departamento']} > {p['categoria']}")

if __name__ == "__main__":
    main()
