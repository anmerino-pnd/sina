"""
Helpers para scraping de Soriana

Funciones auxiliares para integrar scraping con base de datos PostgreSQL.
"""

import time
import random
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy import create_engine, insert, select, distinct
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sina.db.models import Supermercado
from sina.config.credentials import DB_URL
from datetime import datetime, timezone
from datetime import datetime, timezone

# Engine global para Soriana
_soriana_engine = create_engine(
    DB_URL,
    connect_args={"timeout": 30} if DB_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)
_soriana_session = sessionmaker(bind=_soriana_engine, expire_on_commit=False)


def guardar_productos_en_db(productos: List[Dict[str, Any]]) -> int:
    """
    Guarda productos extraídos de Soriana en la tabla Supermercado.
    
    Args:
        productos: Lista de dicts con estructura:
            {
                "producto": str,
                "marca": str,
                "presentacion": str,
                "precio": float,
                "tienda": str,
                "categoria": str,
                "subcategoria": str,
                "departamento": str,
                "pid_origen": str
            }
            
    Returns:
        int: Número de productos guardados/actualizados
    """
    if not productos:
        return 0
    
    rows = []
    for p in productos:
        rows.append({
            "producto": p.get("producto", ""),
            "precio": float(p.get("precio", 0)),
            "pid": int(p.get("pid_origen", 0)),
            "tienda": p.get("tienda", "Soriana"),
            "departamento": p.get("departamento", ""),
            "categoria": p.get("categoria", ""),
            "subcategoria": p.get("subcategoria"),
            "fecha_actualizacion": datetime.now(timezone.utc),
        })
    
    base = sqlite_insert(Supermercado)
    stmt = base.values(rows).on_conflict_do_update(
        index_elements=["pid"],
        set_={
            "producto": base.excluded.producto,
            "precio": base.excluded.precio,
            "fecha_actualizacion": base.excluded.fecha_actualizacion,
        },
    )
    with _soriana_engine.begin() as conn:
        conn.execute(stmt)
    
    return len(rows)


def no_esta_duplicado(pid: str, lista_productos: List[Dict[str, Any]]) -> bool:
    """Verifica si un PID ya existe en la lista de productos extraídos."""
    for producto in lista_productos:
        if producto["pid_origen"] == pid:
            return False
    return True


def get_session() -> Any:
    """Obtiene session de SQLAlchemy."""
    session = _soriana_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def contar_productos() -> int:
    """Contador total de productos en tabla Supermercado."""
    with _soriana_session() as session:
        return session.query(Supermercado).count()


def borrar_productos() -> None:
    """Borra todos los productos de la tabla Supermercado."""
    with _soriana_engine.begin() as conn:
        conn.execute(delete(Supermercado))


# Funciones para scraping de categorías
def detect_subcategories(page, category_name: str) -> List[str]:
    """
    Detecta dinámicamente si una categoría tiene subcategorías activas.
    
    Args:
        page: Objeto de Playwright
        category_name: Nombre de la categoría actual
        
    Returns:
        Lista de subcategorías activas, o None si no hay subcategorías
    """
    page.wait_for_timeout(2000)
    
    try:
        subcategory_buttons = page.locator("button, a[href*='/']")
        buttons = subcategory_buttons.all()
        
        if len(buttons) > 0:
            texts = []
            for btn in buttons:
                text = btn.inner_text()
                if text and len(text.strip()) > 0:
                    texts.append(text.strip())
            
            possible_subcategories = [
                "Tinto", "Blanco", "Espumoso", "Rosado",
                "Destilados", "Licores", "Cervezas", "Coolers",
                "Mezcladores", "Sidras", "Jardín", "Flower Garden",
                "Premium", "Económico", "Integran", "Seco", "Blanco", "Rojo",
                "Lentejas", "Habas", "Soja", "Chícharo"
            ]
            
            detected = []
            for text in texts:
                text_lower = text.lower()
                for subcat in possible_subcategories:
                    if subcat.lower() in text_lower or text_lower in subcat.lower():
                        detected.append(text)
                        break
            
            if len(detected) > 0:
                print(f"  → Detectadas {len(detected)} subcategorías: {', '.join(detected)}")
                return detected
        
    except Exception as e:
        print(f"  Error detectando subcategorías: {e}")
    
    return None


def scrape_soriana_page(page, url: str, depto: str, categoria: str, subcategoria_definida: str = None) -> List[Dict[str, Any]]:
    """
    Extrae productos de una sola página de Soriana.
    
    Args:
        page: Objeto de Playwright
        url: URL de la página
        depto: Departamento
        categoria: Categoría
        subcategoria_definida: Subcategoría (opcional)
        
    Returns:
        Lista de productos extraídos
    """
    productos = []
    
    page.wait_for_timeout(random.uniform(2000, 3500))
    
    # Detectar si hay subcategorías activas
    subcategorias_activas = detect_subcategories(page, categoria)
    
    if subcategorias_activas:
        print(f"  → Se detectaron {len(subcategorias_activas)} subcategorías activas")
        
        for subcategoria in subcategorias_activas:
            print(f"\n  Procesando subcategoría: {subcategoria}")
            subcat_url = url
            
            pagina_actual = 1
            
            while True:
                print(f"\n  Extrayendo página {pagina_actual} de {subcategoria}...")
                
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
                        if no_esta_duplicado(pid, productos):
                            producto = {
                                "producto": nombre,
                                "marca": "Por extraer",
                                "presentacion": "Por extraer",
                                "precio": precio,
                                "tienda": "Soriana",
                                "categoria": categoria.capitalize(),
                                "subcategoria": subcategoria,
                                "departamento": depto.capitalize(),
                                "pid_origen": pid
                            }
                            productos.append(producto)
                            extraidos_pagina += 1
                
                print(f"    Se extrajeron {extraidos_pagina} productos.")
                
                siguiente_num = pagina_actual + 1
                selector_exacto = f'button.btn.btn-link.more.page.new-plp-design[data-page-number="{siguiente_num}"]'
                boton_numero = page.locator(selector_exacto).first
                
                if boton_numero.is_visible():
                    print(f"    Pasando a la página {siguiente_num}...")
                    boton_numero.scroll_into_view_if_needed()
                    page.wait_for_timeout(random.uniform(500, 1500))
                    
                    try:
                        boton_numero.click(force=True)
                        page.wait_for_timeout(random.uniform(3000, 4500))
                        pagina_actual += 1
                    except Exception as e:
                        print(f"    Error al clickear: {e}")
                        break
                else:
                    print(f"    Fin de las páginas para {subcategoria}.")
                    break
        
        print(f"\n  Subcategoría '{categoria}' completada.\n")
    else:
        print(f"  → No se detectaron subcategorías, extrayendo directamente de {categoria}")
        
        pagina_actual = 1
        
        while True:
            print(f"\nExtrayendo página {pagina_actual}...")
            
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
                    if no_esta_duplicado(pid, productos):
                        producto = {
                            "producto": nombre,
                            "marca": "Por extraer",
                            "presentacion": "Por extraer",
                            "precio": precio,
                            "tienda": "Soriana",
                            "categoria": categoria.capitalize(),
                            "subcategoria": subcategoria_definida or "N/A",
                            "departamento": depto.capitalize(),
                            "pid_origen": pid
                        }
                        productos.append(producto)
                        extraidos_pagina += 1
            
            print(f"   Se extrajeron {extraidos_pagina} productos.")
            
            siguiente_num = pagina_actual + 1
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
                    print(f"   Error al clickear: {e}")
                    break
            else:
                print(f"   Fin de las páginas para {categoria}.")
                break
        
        print(f"\nCategoría '{categoria}' completada.\n")
    
    return productos
