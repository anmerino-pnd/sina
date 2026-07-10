"""
Helper de scraping para Farmacias Benavides (Magento).

A diferencia de Del Sol (VTEX, requiere navegador), Benavides renderiza el grid
en el servidor, asi que basta curl_cffi + BeautifulSoup (sin Playwright).

Devuelve dicts con el formato que consume
`SupermercadoRepository.upsert_productos` (clave `pid_origen`).
"""
import re
import time
from typing import List, Dict, Any

from bs4 import BeautifulSoup
from curl_cffi import requests

# Cortesia entre paginas para no martillar el servidor.
_DELAY_ENTRE_PAGINAS_S = 1.5


def _parsear_precio_min(card) -> float:
    """Precio efectivo = el menor de los <span class="price"> de la tarjeta."""
    precios: List[float] = []
    for span in card.select(".price-box span.price"):
        limpio = re.sub(r"[^\d.]", "", span.get_text().replace(",", ""))
        try:
            valor = float(limpio)
            if valor > 0:
                precios.append(valor)
        except ValueError:
            continue
    return min(precios) if precios else 0.0


def scrape_benavides_page(
    base_url: str,
    url_path: str,
    depto: str,
    categoria: str,
    impersonate: str = "chrome120",
    timeout: int = 30,
) -> List[Dict[str, Any]]:
    """
    Extrae todos los productos de una categoria de Benavides, siguiendo la
    paginacion (?p=N) hasta que ya no exista enlace "siguiente".
    """
    productos: List[Dict[str, Any]] = []
    url = f"{base_url}{url_path}"
    pagina_actual = 1

    while True:
        url_pagina = url if pagina_actual == 1 else f"{url}?p={pagina_actual}"
        print(f"  [+] Pagina {pagina_actual}: {url_pagina}")

        try:
            r = requests.get(url_pagina, impersonate=impersonate, timeout=timeout)
        except Exception as e:
            print(f"  [X] Error de red: {e}")
            break

        if r.status_code != 200:
            print(f"  [X] HTTP {r.status_code}, fin de la categoria.")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("li.product-item")
        if not cards:
            print("  [!] Sin productos en esta pagina. Fin.")
            break

        for card in cards:
            a_name = card.select_one("strong.product-item-name a")
            nombre = a_name.get_text(strip=True) if a_name else "Desconocido"

            precio = _parsear_precio_min(card)

            pid_el = card.select_one("[data-product-id]")
            try:
                pid = int(pid_el.get("data-product-id")) if pid_el else 0
            except (ValueError, TypeError):
                pid = 0

            if precio > 0 and nombre != "Desconocido" and pid:
                productos.append({
                    "producto": nombre,
                    "precio": precio,
                    "pid_origen": pid,
                    "tienda": "Benavides",
                    "departamento": depto,
                    "categoria": categoria,
                    "subcategoria": None,
                })

        print(f"  [+] {len(cards)} tarjetas en la pagina {pagina_actual}.")

        siguiente = soup.select_one("li.pages-item-next a")
        if siguiente and siguiente.get("href"):
            pagina_actual += 1
            time.sleep(_DELAY_ENTRE_PAGINAS_S)
        else:
            print("  [!] Fin de paginacion.")
            break

    return productos
