"""
Soriana Scraper

Módulo principal para la extracción de productos de Soriana.
Integra con la clase Supermercado de sina.db.models y repository.py

Departamentos y categorías se definen dinámicamente en la función scrape_soriana().
"""

from typing import List, Dict, Any
from sina.db.models import Supermercado
from sina.scraping.helpers import (
    scrape_soriana_page,
    guardar_productos_en_db,
    no_esta_duplicado,
    contar_productos,
)
from playwright.sync_api import sync_playwright


def scrape_soriana(
    departments: List[str] = None,
    categories: List[str] = None,
    subcategories: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Extrae productos de Soriana iterando sobre departamentos y categorías.
    
    Args:
        departments: Lista de departamentos a extraer (opcional)
        categories: Lista de categorías a extraer (opcional)
        subcategories: Lista de subcategorías a extraer (opcional)
        
    Returns:
        Lista de productos extraídos (guardados en DB)
    """
    productos_extraidos = []
    
    # URLs base por departamento
    urls_base = {
        "vinos-licores-y-cervezas": "https://www.soriana.com/vinos-licores-y-cervezas/",
        "despensa": "https://www.soriana.com/despensa/arroz-frijol-y-semillas/",
        "frutas-y-verduras": "https://www.soriana.com/frutas-verduras/",
        "lacteos-y-huevo": "https://www.soriana.com/lacteos-huevo/",
    }
    
    # Categorías por departamento
    categorias_por_departamento = {
        "vinos-licores-y-cervezas": ["destilados-y-licores", "vinos", "cervezas", "coolers", "mezcladores", "sidras"],
        "despensa": ["Arroz", "Frijol", "Leguminosas", "Semillas"],
        "frutas-y-verduras": ["Frutas", "Verduras", "Legumbres"],
        "lacteos-y-huevo": ["Lácteos", "Huevos", "Yogures", "Leches"],
    }
    
    # Filtrar por parámetros
    if departments:
        urls_base = {k: v for k, v in urls_base.items() if k in departments}
        categorias_por_departamento = {k: v for k, v in categorias_por_departamento.items() if k in departments}
    
    print(f"Iniciando Spider Soriana: {len(urls_base)} departamentos")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            for depto, categorias in categorias_por_departamento.items():
                url_base = urls_base.get(depto)
                if not url_base:
                    continue
                
                print(f"\n{'='*60}")
                print(f"Departamento: {depto.capitalize()}")
                print(f"{'='*60}")
                
                for categoria in categorias:
                    print(f"\n  Categoría: {categoria}")
                    
                    # URL de la categoría (sin subcategoría)
                    categoria_url = f"{url_base}{categoria}/"
                    
                    page.goto(categoria_url, wait_until="domcontentloaded")
                    page.wait_for_timeout(random.uniform(2000, 3500))
                    
                    # Extraer productos de esta página
                    productos_pagina = scrape_soriana_page(
                        page=page,
                        url=categoria_url,
                        depto=depto,
                        categoria=categoria,
                        subcategoria_definida=None
                    )
                    
                    # Guardar en DB
                    guardados = guardar_productos_en_db(productos_pagina)
                    print(f"  → Guardados en DB: {guardados} productos")
                    
                    # Agregar a lista
                    productos_extraidos.extend(productos_pagina)
            
            print(f"\n{'='*60}")
            print(f"EXTRACCIÓN FINALIZADA: {len(productos_extraidos)} productos en total.")
            print(f"  Total en DB: {contar_productos()}")
            print(f"{'='*60}")
        
        except Exception as e:
            print(f"Ocurrió un error general: {e}")
        
        finally:
            browser.close()
    
    return productos_extraidos


def main():
    """Ejemplo de uso básico."""
    # Opción 1: Extraer todo
    productos = scrape_soriana()
    
    # Opción 2: Solo vinos
    # productos = scrape_soriana(departments=["vinos-licores-y-cervezas"])
    
    # Opción 3: Solo categoría específica
    # productos = scrape_soriana(categories=["vinos"])
    
    # Opción 4: Solo subcategorías específicas
    # productos = scrape_soriana(categories=["vinos"], subcategories=["vino-tinto", "vino-blanco"])
    
    print(f"\nTotal de productos: {len(productos)}")
    for p in productos[:5]:  # Mostrar primeros 5
        print(f"  - {p['producto']} (${p['precio']}) - {p['categoria']} > {p['subcategoria']}")


if __name__ == "__main__":
    import random
    main()
