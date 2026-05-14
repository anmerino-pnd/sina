from playwright.sync_api import sync_playwright
import time

def scrape_soriana_navegacion(categoria_objetivo="Arroz"):
    """
    Simula la navegación humana en Soriana usando Playwright.
    Entra a la sección general, busca la subcategoría deseada, hace clic y extrae.
    """
    productos_extraidos = []
    
    # URL principal de la familia de productos (como vimos en tu imagen)
    url_base = "https://www.soriana.com/despensa/arroz-frijol-y-semillas/"

    print("Iniciando Spider de Soriana...")

    # Iniciamos Playwright
    with sync_playwright() as p:
        # headless=False te permite ver cómo el robot mueve la página. 
        # (En producción para SINA, cambiar a headless=True)
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # 1. Entrar a la categoría general
            print(f"Navegando a: {url_base}")
            page.goto(url_base, wait_until="domcontentloaded")
            
            # Esperamos un poco para que Cloudflare nos valide como humanos
            page.wait_for_timeout(3000) 

            # 2. Buscar el enlace de la subcategoría (ej. "Arroz")
            print(f"Buscando el botón/enlace para: '{categoria_objetivo}'...")
            
            # Buscamos enlaces (a) que contengan el texto "Arroz", "Frijol", etc.
            # Según tu imagen, hay botones que dicen "Arroz" y "Ver más"
            enlace_subcategoria = page.locator(f"a:has-text('{categoria_objetivo}')").first

            if not enlace_subcategoria.is_visible():
                print(f"❌ No se encontró la subcategoría {categoria_objetivo} en la pantalla.")
                browser.close()
                return []

            # 3. Hacer clic y auto-dirigirse
            print(f"Botón encontrado! Haciendo clic en '{categoria_objetivo}'...")
            enlace_subcategoria.click()
            
            # Esperamos a que la nueva página cargue completamente los productos
            page.wait_for_load_state("networkidle", timeout=60000)
            page.wait_for_timeout(5000) # Pausa extra por seguridad

            # 4. Scrapear la página de destino (Grid de productos)
            print(f"Extrayendo productos de la página de {categoria_objetivo}...")
            
            # Ubicamos todas las tarjetas usando el HTML que analizamos antes
            tarjetas = page.locator("div.product").all()
            
            for tarjeta in tarjetas:
                pid = tarjeta.get_attribute("data-pid")
                
                # Nombre del producto
                img_locator = tarjeta.locator("img.tile-image").first
                nombre = img_locator.get_attribute("alt") if img_locator.count() > 0 else "Desconocido"
                
                # Precio (usando nuestro truco del input de clevertap)
                precio_input = tarjeta.locator("input[name='clevertap-list-price']").first
                precio = None
                if precio_input.count() > 0:
                    try:
                        precio = float(precio_input.get_attribute("value")) # type: ignore
                    except (ValueError, TypeError):
                        pass

                # Guardar si encontramos precio
                if precio and nombre != "Desconocido":
                    productos_extraidos.append({
                        "producto": nombre,
                        "marca": "Por extraer",
                        "presentacion": "Por extraer",
                        "precio": precio,
                        "tienda": "Soriana",
                        "vigente": True,
                        "pid_origen": pid
                    })
            
            print(f"Se extrajeron {len(productos_extraidos)} productos exitosamente!")

        except Exception as e:
            print(f"Ocurrió un error durante la navegación: {e}")
        
        finally:
            browser.close()

    return productos_extraidos

# --- Prueba del Spider ---
if __name__ == "__main__":
    # Puedes cambiar "Arroz" por "Frijol" o "Leguminosas" para probar otras secciones
    datos = scrape_soriana_navegacion("Arroz")
    
    print("\n--- MUESTRA DE DATOS ---")
    for item in datos[:5]:
        print(f"- {item['producto']}: ${item['precio']}")