from playwright.sync_api import sync_playwright
import time
import random

def scrape_soriana_total(categoria_objetivo="Todo"):
    """
    Spider Maestro: Navega por sub-pestañas y pagina usando selectores exactos.
    """
    productos_extraidos = []
    base_url = "https://www.soriana.com/despensa/arroz-frijol-y-semillas"
    
    mapa_pestañas = {
        "Arroz": ["arroz"],
        "Frijol": ["frijol"],
        "Leguminosas": ["leguminosas"],
        "Semillas": ["semillas"],
        "Todo": ["leguminosas", "arroz", "frijol", "semillas"]
    }
    
    pestañas_a_visitar = mapa_pestañas.get(categoria_objetivo, ["arroz"])

    print(f"Iniciando Spider Total para: {categoria_objetivo}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) 
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            for pestaña in pestañas_a_visitar:
                url_pestaña = f"{base_url}/{pestaña}/"
                print(f"Navegando a pestaña: {pestaña.upper()}")
                
                page.goto(url_pestaña, wait_until="domcontentloaded")
                page.wait_for_timeout(random.uniform(2000, 3500))

                pagina_actual = 1
                
                while True:
                    print(f"Extrayendo datos de la página {pagina_actual} ({pestaña})...")
                    
                    # Scroll humano
                    for i in range(4):
                        page.evaluate("window.scrollBy(0, 700);")
                        page.wait_for_timeout(random.uniform(600, 1000))
                    
                    tarjetas = page.locator("div.list-item-product div.product").all()
                    extraidos_pagina = 0
                    
                    for tarjeta in tarjetas:
                        pid = tarjeta.get_attribute("data-pid")
                        
                        img_locator = tarjeta.locator("img.tile-image").first
                        nombre = img_locator.get_attribute("alt") if img_locator.count() > 0 else "Desconocido"
                        
                        precio_input = tarjeta.locator("input[name='clevertap-list-price']").first
                        precio = None
                        if precio_input.count() > 0:
                            try:
                                precio = float(precio_input.get_attribute("value"))
                            except (ValueError, TypeError):
                                pass

                        if precio and nombre != "Desconocido":
                            if no_esta_duplicado(pid, productos_extraidos):
                                productos_extraidos.append({
                                    "producto": nombre,
                                    "marca": "Por extraer",        
                                    "presentacion": "Por extraer", 
                                    "precio": precio,
                                    "tienda": "Soriana",
                                    "categoria": pestaña.capitalize(),
                                    "pid_origen": pid
                                })
                                extraidos_pagina += 1
                    
                    print(f"   Se extrajeron {extraidos_pagina} productos.")

                    # --- LÓGICA DE PAGINACIÓN ACTUALIZADA CON TUS CAPTURAS ---
                    siguiente_num = pagina_actual + 1
                    
                    # Usamos la clase exacta que mostraste en image_84755c.png
                    selector_exacto = f'button.btn.btn-link.more.page.new-plp-design[data-page-number="{siguiente_num}"]'
                    boton_numero = page.locator(selector_exacto).first
                    
                    if boton_numero.is_visible():
                        print(f"   Pasando a la página {siguiente_num}...")
                        boton_numero.scroll_into_view_if_needed()
                        page.wait_for_timeout(random.uniform(500, 1500))
                        
                        try:
                            boton_numero.click(force=True)
                            page.wait_for_timeout(random.uniform(3000, 4500))
                            pagina_actual += 1
                        except Exception as e:
                            print(f"   Error al clickear la página {siguiente_num}: {e}")
                            break
                    else:
                        print(f"   Fin de las páginas para la pestaña '{pestaña}'.\n")
                        break
            
            print(f"EXTRACCIÓN TOTAL FINALIZADA: {len(productos_extraidos)} productos en total.")

        except Exception as e:
            print(f" Ocurrió un error general: {e}")
        
        finally:
            browser.close()

    return productos_extraidos

def no_esta_duplicado(pid, lista_productos):
    for p in lista_productos:
        if p["pid_origen"] == pid:
            return False
    return True

if __name__ == "__main__":
    # Prueba la extracción total
    datos = scrape_soriana_total("Todo")
    
    print("\n=== RESUMEN FINAL ===")
    print(f"Total de productos extraídos: {len(datos)}")