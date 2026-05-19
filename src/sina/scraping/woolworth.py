"""
Orquestador de scraping Del Sol (Woolworth).
Consulta el catalogo de rutas y ejecuta extracciones asincronas.
"""

import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from sina.db.repository import CatalogoRepository, SupermercadoRepository
from sina.scraping.helper_woolworth import scrape_delsol_page

async def scrape_delsol() -> List[Dict[str, Any]]:
    """Extraccion completa de Del Sol usando el catalogo de rutas."""
    print("[*] Iniciando Spider Del Sol...")
    
    repo_catalogo = CatalogoRepository(tienda="Del Sol")
    rutas_activas = repo_catalogo.obtener_rutas_activas()
    
    if not rutas_activas:
        print("[!] No hay rutas activas en el catalogo para Del Sol.")
        return []
    
    print(f"[*] Encontradas {len(rutas_activas)} rutas activas")
    productos_extraidos = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, # Pon True en produccion
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        )
        page = await context.new_page()
        await stealth_async(page)
        
        try:
            for route in rutas_activas:
                print(f"\\n[*] Procesando: {route['departamento']} > {route['categoria']}")
                
                # Asume que el url_path inicia con '/'
                url = f"https://www.delsol.com.mx{route['url_path']}"
                
                productos = await scrape_delsol_page(
                    page=page,
                    url=url,
                    depto=route['departamento'],
                    categoria=route['categoria']
                )
                
                if productos:
                    # Guardar en DB
                    repo_sup = SupermercadoRepository()
                    await asyncio.gather(*[
                        repo_sup.upsert_productos([p])
                        for p in productos
                    ])
                    productos_extraidos.extend(productos)
                    repo_catalogo.actualizar_ultima_extraccion(route['id'])
                    
        except Exception as e:
            print(f"[X] Error en el orquestador: {e}")
        finally:
            await browser.close()
    
    print(f"\\n[OK] EXTRACCION FINALIZADA: {len(productos_extraidos)} productos extraidos.")
    return productos_extraidos

def main():
    print("[*] Ejecutando orquestador Del Sol...")
    productos = asyncio.run(scrape_delsol())
    for p in productos[:3]:
        print(f"   - {p['producto']} (${p['precio']})")

if __name__ == "__main__":
    main()