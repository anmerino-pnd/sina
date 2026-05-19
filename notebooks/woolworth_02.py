import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def extraer_categoria_delsol(url, departamento, categoria):
    print(f"[*] Iniciando Extractor Async en: {url}")
    productos_extraidos = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
        )
        page = await context.new_page()
        await stealth_async(page)

        try:
            print("[*] Navegando a la categoria...")
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
                print(f"\\n[*] Extrayendo pagina {pagina_actual}...")

                for i in range(1, 6):
                    await page.evaluate(f"window.scrollTo(0, {i * 800});")
                    await page.wait_for_timeout(600)

                # Inyeccion JS mejorada para extraer PID y parsear Precio como Float
                productos_pagina = await page.evaluate("""() => {
                    let cards = Array.from(document.querySelectorAll('div.product'));
                    
                    return cards.map(card => {
                        let a_name = card.querySelector('.product_name a');
                        let nombre = a_name ? a_name.innerText.trim() : 'Desconocido';
                        
                        let span_price = card.querySelector('.product_price .price');
                        let precio_str = span_price ? span_price.innerText : '0';
                        precio_str = precio_str.replace('$', '').replace('MXN', '').replace(/,/g, '').trim();
                        let precio = parseFloat(precio_str) || 0.0;
                        
                        // Extraer PID del ID del contenedor de precio (ej. product_price_219059)
                        let price_div = card.querySelector('.product_price');
                        let pid_str = price_div ? price_div.id.replace('product_price_', '') : '0';
                        let pid = parseInt(pid_str) || 0;
                        
                        return { producto: nombre, precio: precio, pid: pid };
                    }).filter(p => p.precio > 0 && p.producto !== 'Desconocido');
                }""")

                for p in productos_pagina:
                    productos_extraidos.append(p)
                    # Printear EXACTAMENTE como el modelo SQLAlchemy Supermercado
                    print(f"<Supermercado(id=None, producto='{p['producto']}', precio={p['precio']}, pid={p['pid']}, tienda='Del Sol', departamento='{departamento}', categoria='{categoria}')>")

                print(f"[OK] Se extrajeron {len(productos_pagina)} productos en esta pagina.")

                # PAGINACION ROBUSTA (Bypass UI)
                siguiente_num = pagina_actual + 1
                
                # Extraemos el href directamente del boton usando JS
                next_url = await page.evaluate(f"""(num) => {{
                    let btn = document.querySelector(`a[data-page-number="${{num}}"]`);
                    return btn ? btn.href : null;
                }}""", siguiente_num)

                if next_url:
                    print(f"[->] Avanzando a la pagina {siguiente_num} usando URL directa...")
                    await page.goto(next_url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(4000)
                    pagina_actual += 1
                else:
                    print("[!] No se encontro enlace para la pagina siguiente. Fin de la categoria.")
                    break

        except Exception as e:
            print(f"[X] Ocurrio un error: {e}")
        finally:
            await browser.close()

    print(f"\\n[OK] EXTRACCION FINALIZADA: {len(productos_extraidos)} productos extraidos en total.")
    return productos_extraidos

if __name__ == "__main__":
    url_prueba = "https://www.delsol.com.mx/Farmacia/Cuidado-Personal-e-Higiene"
    asyncio.run(extraer_categoria_delsol(
        url=url_prueba, 
        departamento="Farmacia", 
        categoria="Cuidado-Personal-e-Higiene"
    ))