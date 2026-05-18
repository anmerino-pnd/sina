import json
from bs4 import BeautifulSoup
from curl_cffi import requests
from pathlib import Path

CONFIG_PATH = Path("src/sina/config/delsol_config.json")

def extraer_arbol_delsol():
    print("Iniciando Explorador Ultrarrapido para Del Sol (Bypass TLS)...")
    url = "https://www.delsol.com.mx/"
    
    try:
        # Usamos curl_cffi simulando ser Chrome 120 para burlar antibots
        print("Descargando HTML maestro...")
        response = requests.get(url, impersonate="chrome120", timeout=30)
        
        if response.status_code != 200:
            print(f"Error al conectar: HTTP {response.status_code}")
            return
            
        print("Parseando el DOM con BeautifulSoup...")
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Encontrar la lista maestra de departamentos
        menu_principal = soup.find("ul", id="allDepartmentsMenu")
        
        if not menu_principal:
            print("No se encontro el id='allDepartmentsMenu'. Cambio el sitio o fuimos bloqueados?")
            # Guardamos un log para depurar
            with open("error_delsol.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("   Revisa 'error_delsol.html' para ver que nos devolvio el servidor.")
            return

        # 2. Extraer departamentos (son los hijos directos <li> del menu principal)
        # Usamos recursive=False para no agarrar los <li> anidados de las categorias
        departamentos_li = menu_principal.find_all("li", recursive=False)
        
        config_final = {}
        contador_prioridad = 1
        
        print(f"Se detectaron {len(departamentos_li)} departamentos potenciales.")
        
        for li_depto in departamentos_li:
            # El enlace principal del departamento tiene la clase 'link menuLink'
            a_depto = li_depto.find("a", class_="link menuLink")
            if not a_depto:
                continue
                
            depto_nombre = a_depto.get_text(strip=True)
            depto_url = a_depto.get("href", "")
            
            # Limpiamos la URL para sacar el ID del departamento (ej: /mujer-1)
            depto_path = depto_url.replace("https://www.delsol.com.mx", "").replace("/wcs/shop/es/delsol", "").split("?")[0]
            depto_key = depto_path.strip("/")
            
            if not depto_key:
                continue
                
            config_final[depto_key] = {}
            
            # 3. Buscar la lista de categorias dentro de este departamento
            ul_categorias = li_depto.find("ul", class_="dropNivel2")
            if not ul_categorias:
                continue
                
            # Las categorias son los <li> de nivel 2
            categorias_li = ul_categorias.find_all("li", class_="nivel2")
            
            for li_cat in categorias_li:
                # El enlace de la categoria es el primer 'a' dentro del 'li.nivel2'
                a_cat = li_cat.find("a", class_="menuLink")
                if not a_cat:
                    continue
                    
                cat_nombre = a_cat.get_text(strip=True)
                cat_url = a_cat.get("href", "")
                
                # Limpiamos la URL (VTEX a veces pone rutas largas)
                cat_path = cat_url.replace("https://www.delsol.com.mx", "").replace("/wcs/shop/es/delsol", "").split("?")[0]
                
                # Extraemos la clave de la categoria (ej: "Damas" de "/mujer-1/Damas")
                partes = [p for p in cat_path.split("/") if p]
                if len(partes) >= 2:
                    cat_key = partes[-1]
                    
                    config_final[depto_key][cat_key] = {
                        "url_path": cat_path,
                        "nombre_visible": cat_nombre,
                        "prioridad": contador_prioridad
                    }
                    contador_prioridad += 1
                    
    except Exception as e:
        print(f"Ocurrio un error inesperado: {e}")
        return

    print("\nGuardando delsol_config.json...")
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Filtramos departamentos vacios por si acaso
    config_limpia = {k: v for k, v in config_final.items() if v}
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_limpia, f, ensure_ascii=False, indent=4)
        
    total_cats = sum(len(v) for v in config_limpia.values())
    print("PROCESO FINALIZADO!")
    print(f" Departamentos guardados: {len(config_limpia)}")
    print(f" Categorias guardadas: {total_cats}")

if __name__ == "__main__":
    # Asegurate de instalar: uv add curl_cffi beautifulsoup4
    extraer_arbol_delsol()
