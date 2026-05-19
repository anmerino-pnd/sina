"""
Helpers para scraping de Del Sol (Woolworth)
Funciones auxiliares para integrar scraping con base de datos PostgreSQL.
"""

from typing import List, Dict, Any

async def scrape_delsol_page(page, url: str, depto: str, categoria: str) -> List[Dict[str, Any]]:
    """
    Extrae productos de una categoria de Del Sol, manejando la paginacion.
    
    Args:
        page: Objeto Page de Playwright (ya instanciado y con stealth)
        url: URL de la categoria
        depto: Departamento
        categoria: Categoria
        
    Returns:
        Lista de productos extraidos
    """
    productos = []
    
    print(f"  [+] Navegando a la categoria: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(4000)

    try:
        btn_cookies = page.locator("button:has-text('Aceptar'), button:has-text('Entendido')").first
        if await btn_cookies.is_visible(timeout=2000):
            await btn_cookies.click()
    except:
        pass

    pagina_actual = 1

    while True:
        print(f"  [+] Extrayendo pagina {pagina_actual}...")

        # Scroll progresivo 
        for i in range(1, 6):
            await page.evaluate(f"window.scrollTo(0, {i * 800});")
            await page.wait_for_timeout(600)

        productos_pagina = await page.evaluate("""() => {
            let cards = Array.from(document.querySelectorAll('div.product'));
            
            return cards.map(card => {
                let a_name = card.querySelector('.product_name a');
                let nombre = a_name ? a_name.innerText.trim() : 'Desconocido';
                
                let span_price = card.querySelector('.product_price .price');
                let precio_str = span_price ? span_price.innerText : '0';
                precio_str = precio_str.replace('$', '').replace('MXN', '').replace(/,/g, '').trim();
                let precio = parseFloat(precio_str) || 0.0;
                
                let price_div = card.querySelector('.product_price');
                let pid_str = price_div ? price_div.id.replace('product_price_', '') : '0';
                let pid = parseInt(pid_str) || 0;
                
                return { producto: nombre, precio: precio, pid_origen: pid };
            }).filter(p => p.precio > 0 && p.producto !== 'Desconocido');
        }""")

        for p in productos_pagina:
            p['tienda'] = 'Del Sol'
            p['departamento'] = depto
            p['categoria'] = categoria
            p['subcategoria'] = None # Del Sol no parece tener subcategorias en este nivel
            productos.append(p)

        print(f"  [+] Se extrajeron {len(productos_pagina)} productos.")

        siguiente_num = pagina_actual + 1
        
        # Paginacion WebSphere
        next_url = await page.evaluate(f"""(num) => {{
            let btn = document.querySelector(`a[data-page-number="${{num}}"]`);
            return btn ? btn.href : null;
        }}""", siguiente_num)

        if next_url:
            print(f"  [->] Avanzando a la pagina {siguiente_num}...")
            await page.goto(next_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)
            pagina_actual += 1
        else:
            print("  [!] Fin de paginacion.")
            break

    return productos