from playwright.sync_api import sync_playwright
import json
import time
from pathlib import Path

CONFIG_PATH = Path("src/sina/config/soriana_config.json")

def extraer_arbol_soriana():
    print("MAPA Iniciando Explorador de Categorias de Soriana...")
    categorias_encontradas = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )
        page = context.new_page()
        
        try:
            print("UBICACION Entrando a la pagina principal...")
            page.goto("https://www.soriana.com/", wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            
            print("RATON Buscando el menu de 'Departamentos'...")
            try:
                btn_menu = page.locator("text='Departamentos'").first
                if btn_menu.is_visible():
                    btn_menu.hover()
                    page.wait_for_timeout(1000)
                    btn_menu.click()
                    page.wait_for_timeout(3000)
            except Exception as e:
                print(" ⚠️ No se pudo interactuar con el menu, continuando sin el.")

            print("BUSCAR Escaneando todos los enlaces de la pagina...")
            enlaces = page.locator("a").all()
            
            for enlace in enlaces:
                try:
                    texto = enlace.inner_text().strip()
                    url = enlace.get_attribute("href")
                    
                    if url and texto and url.startswith("/"):
                        # Separar la URL eliminando espacios vacíos
                        partes_url = [p for p in url.split("/") if p]
                        
                        # EL TRUCO: Solo URLs con exactamente 2 niveles (Departamento -> Categoría)
                        # Ej: ['vinos-licores-y-cervezas', 'destilados-y-licores'] -> len() == 2
                        if len(partes_url) == 2:
                            
                            palabras_ignoradas = [
                                "login", "cart", "account", "wishlist", "on/demandware", 
                                "ayuda", "sucursales", "contacto", "facturacion", "terminos",
                                ".pdf", "aviso-de-privacidad", "promociones", "ofertas"
                            ]
                            
                            if not any(palabra in url.lower() for palabra in palabras_ignoradas):
                                texto_limpio = " ".join(texto.split())
                                
                                if len(texto_limpio) > 2:
                                    # Usamos la URL como clave única para evitar sobreescrituras raras
                                    categorias_encontradas[url] = {
                                        "departamento": partes_url[0],
                                        "categoria": partes_url[1],
                                        "nombre_visible": texto_limpio
                                    }
                except Exception:
                    continue
            
            print(f"CHECK Escaneo completado. Se filtraron {len(categorias_encontradas)} categorias principales.")

        except Exception as e:
            print(f"ERROR Error durante el escaneo: {e}")
        finally:
            browser.close()

    print("DISCO Generando soriana_config.json...")
    
    # Asegurarnos de que exista el directorio
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if CONFIG_PATH.exists():
        print(" BRILLO Cargando configuracion existente...")
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config_existente = json.load(f)
    else:
        print(" BRILLO Configuracion no existe, creando nueva...")
        config_existente = {}
    
    contador_prioridad = 1
    
    for url, info in categorias_encontradas.items():
        departamento = info["departamento"]
        categoria_db = info["categoria"]
        
        if departamento not in config_existente:
            config_existente[departamento] = {}
        
        # Guardamos de forma plana (sin subcategorías)
        config_existente[departamento][categoria_db] = {
            "url_path": url,
            "nombre_visible": info["nombre_visible"],
            "prioridad": contador_prioridad
        }
        contador_prioridad += 1
            
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_existente, f, ensure_ascii=False, indent=4)
    
    total_categorias = sum(len(v) for v in config_existente.values())
    
    print(f"\nFELICIDAD PROCESO FINALIZADO!")
    print(f" ESTADISTICA Departamentos encontrados: {len(config_existente)}")
    print(f" ESTADISTICA Categorias principales guardadas: {total_categorias}")
    print(f" DISCO Configuracion guardada en: {CONFIG_PATH}")

if __name__ == "__main__":
    extraer_arbol_soriana()
