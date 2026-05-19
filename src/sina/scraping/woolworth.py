"""
Orquestador de scraping Del Sol (Woolworth).
Consulta el catalogo de rutas y ejecuta extracciones asincronas.
"""

import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
from sina.db.repository import CatalogoRepository
from sina.scraping.helper_woolworth import scrape_delsol_page
# Asumo que guardar_productos_en_db es generico y ya maneja el campo 'tienda'
from sina.scraping.helper_soriana import guardar_productos_en_db, contar_productos

async def scrape_delsol() -> List[Dict[str, Any]]:
    """Extraccion completa de Del Sol usando el catalogo de rutas."""
    print("[*] Iniciando Spider Del Sol...")
    
    repo = CatalogoRepository()
    # Importante: Asume que modificaste obtener_rutas_activas para filtrar por tienda
    # rutas_activas = repo.obtener_rutas_activas(tienda="Del Sol") 
    
    # Placeholder: Simulamos obtener las rutas de la DB (cambia esto por la llamada real)
    # Por ahora, usamos una ruta de prueba para no sobrecargar el sistema en desarrollo
    rutas_activas = [
        {
            "id": 1, "tienda": "Del Sol", "departamento": "Farmacia", 
            "categoria": "Cuidado-Personal-e-Higiene", 
            "url_path": "/Farmacia/Cuidado-Personal-e-Higiene", "prioridad": 1
        }
    ]
    
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
                    # guardados = guardar_productos_en_db(productos) # Descomenta cuando BD este lista
                    productos_extraidos.extend(productos)
                    # repo.actualizar_ultima_extraccion(route['id']) # Actualizar timestamp
                    
        except Exception as e:
            print(f"[X] Error en el orquestador: {e}")
        finally:
            await browser.close()
    
    print(f"\\n[OK] EXTRACCION FINALIZADA: {len(productos_extraidos)} productos extraidos.")
    # print(f"   Total en DB: {contar_productos()}")
    return productos_extraidos

def main():
    print("[*] Ejecutando orquestador Del Sol...")
    productos = asyncio.run(scrape_delsol())
    for p in productos[:3]:
        print(f"   - {p['producto']} (${p['precio']})")

if __name__ == "__main__":
    main()