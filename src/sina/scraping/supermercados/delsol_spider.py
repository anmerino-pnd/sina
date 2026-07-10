import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async
from sina.config.credentials import delsol_base_url
from sina.db.repository import CatalogoRepository, SupermercadoRepository
from sina.scraping.supermercados.delsol_helper import scrape_delsol_page
from sina.scraping.supermercados.interfaces import BrowserConfig

async def scrape_delsol(config: BrowserConfig = BrowserConfig()) -> List[Dict[str, Any]]:
    """Extraccion completa de Del Sol usando el catalogo de rutas."""
    print("[*] Iniciando Spider Del Sol...")
    
    repo_catalogo = CatalogoRepository()
    rutas_activas = repo_catalogo.obtener_rutas_activas(tienda="Del Sol")
    
    if not rutas_activas:
        print("[!] No hay rutas activas en el catalogo para Del Sol.")
        return []
    
    print(f"[*] Encontradas {len(rutas_activas)} rutas activas")
    productos_extraidos: List[Dict[str, Any]] = []
    
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(
            headless=config.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context: BrowserContext = await browser.new_context(**config.to_playwright_context())
        page: Page = await context.new_page()
        await stealth_async(page)
        
        try:
            for route in rutas_activas:
                print(f"\n[*] Procesando: {route['departamento']} > {route['categoria']}")
                
                url = f"{delsol_base_url}{route['url_path']}"
                
                productos = await scrape_delsol_page(
                    page=page,
                    url=url,
                    depto=route['departamento'],
                    categoria=route['categoria']
                )
                
                if productos:
                    repo_sup = SupermercadoRepository()
                    repo_sup.upsert_productos(productos)
                    productos_extraidos.extend(productos)
                    repo_catalogo.actualizar_ultima_extraccion(route['id'])
                    
        except Exception as e:
            print(f"[X] Error en el orquestador: {e}")
        finally:
            await browser.close()
    
    print(f"\n[OK] EXTRACCION FINALIZADA: {len(productos_extraidos)} productos extraidos.")
    return productos_extraidos

def main() -> None:
    print("[*] Ejecutando orquestador Del Sol...")
    productos = asyncio.run(scrape_delsol())
    for p in productos[:3]:
        print(f"   - {p['producto']} (${p['precio']})")

if __name__ == "__main__":
    main()
