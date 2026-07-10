"""
Extractor de productos de una categoria de Farmacias Benavides (Magento).

Equivalente a `woolworth_02.py` (Del Sol), pero mas simple: Benavides renderiza
el grid de productos en el servidor, asi que curl_cffi + BeautifulSoup basta y NO
necesitamos Playwright.

Notas de scraping (verificadas contra el sitio):
  - Tarjeta:  li.product-item  (12 por pagina)
  - Nombre:   strong.product-item-name a
  - Precio:   dentro de .price-box hay uno o dos <span class="price"> ($445, $495 si
              hay descuento). El precio que paga el cliente es el MENOR -> tomamos min().
  - PID:      elemento con atributo [data-product-id]
  - Paginacion: ?p=N ; el enlace "siguiente" es li.pages-item-next a (href absoluto).

Fallback: si en el futuro Benavides mete un reto anti-bot (Cloudflare/Akamai) y
curl_cffi empieza a recibir 403, migrar a Playwright-stealth como en soriana_spider.

Instalar: uv add curl_cffi beautifulsoup4
"""
import re
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://www.benavides.com.mx"


def _parsear_precio_min(card) -> float:
    """Devuelve el precio efectivo (el menor de los que muestre la tarjeta)."""
    precios = []
    for span in card.select(".price-box span.price"):
        texto = span.get_text()
        limpio = re.sub(r"[^\d.]", "", texto.replace(",", ""))
        try:
            valor = float(limpio)
            if valor > 0:
                precios.append(valor)
        except ValueError:
            continue
    return min(precios) if precios else 0.0


def extraer_categoria_benavides(url_path: str, departamento: str, categoria: str) -> list[dict]:
    print(f"[*] Extrayendo Benavides: {departamento} > {categoria} ({url_path})")
    productos_extraidos: list[dict] = []

    url = f"{BASE_URL}{url_path}"
    pagina_actual = 1

    while True:
        url_pagina = url if pagina_actual == 1 else f"{url}?p={pagina_actual}"
        print(f"\n[*] Pagina {pagina_actual}: {url_pagina}")

        try:
            r = requests.get(url_pagina, impersonate="chrome120", timeout=30)
        except Exception as e:
            print(f"[X] Error de red: {e}")
            break

        if r.status_code != 200:
            print(f"[X] HTTP {r.status_code}, fin.")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("li.product-item")

        if not cards:
            print("[!] Sin productos en esta pagina. Fin.")
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
                producto = {
                    "producto": nombre,
                    "precio": precio,
                    "pid": pid,
                    "tienda": "Benavides",
                    "departamento": departamento,
                    "categoria": categoria,
                }
                productos_extraidos.append(producto)
                # Imprime como el modelo SQLAlchemy Supermercado
                print(
                    f"<Supermercado(id=None, producto='{producto['producto']}', "
                    f"precio={producto['precio']}, pid={producto['pid']}, "
                    f"tienda='Benavides', departamento='{departamento}', categoria='{categoria}')>"
                )

        print(f"[OK] {len(cards)} tarjetas en la pagina {pagina_actual}.")

        # Paginacion: seguir mientras exista el enlace "siguiente".
        siguiente = soup.select_one("li.pages-item-next a")
        if siguiente and siguiente.get("href"):
            pagina_actual += 1
            time.sleep(1.5)  # cortesia: no martillar el servidor
        else:
            print("[!] No hay pagina siguiente. Fin de la categoria.")
            break

    print(f"\n[OK] EXTRACCION FINALIZADA: {len(productos_extraidos)} productos.")
    return productos_extraidos


if __name__ == "__main__":
    # Categoria de prueba: Medicamentos > Dolor
    datos = extraer_categoria_benavides(
        url_path="/medicamentos-dolor",
        departamento="medicamentos",
        categoria="dolor",
    )
    print("\n--- MUESTRA ---")
    for item in datos[:5]:
        print(f"- {item['producto']}: ${item['precio']}")
