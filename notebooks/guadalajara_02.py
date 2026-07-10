"""
Extractor de productos de una categoria de Farmacias Guadalajara (SFCC).

Plataforma Salesforce Commerce Cloud (igual que Soriana), pero aqui NO necesitamos
navegador: los productos vienen server-side y la paginacion es un endpoint HTML
("Show More" -> Search-UpdateGrid?cgid=...&start=N&sz=20) que devuelve el siguiente
bloque de tarjetas. Vamos siguiendo el boton "Ver mas" hasta que ya no exista.

Selectores verificados:
  - Tarjeta:  div.product[data-pid]
  - Nombre:   .pdp-link a  (title o texto)
  - Precio:   .sales .value  -> atributo `content` (float limpio); fallback: texto de .price
  - Paginacion: .show-more button[data-url]  (URL absoluta al siguiente bloque)

Instalar: uv add curl_cffi beautifulsoup4
"""
import re
import time
from bs4 import BeautifulSoup
from curl_cffi import requests

BASE_URL = "https://www.farmaciasguadalajara.com"


def _parsear_precio(card) -> float:
    """Precio del producto: preferimos el atributo `content` de .sales .value."""
    val = card.select_one(".sales .value")
    if val is not None:
        contenido = val.get("content")
        if contenido:
            try:
                return float(contenido)
            except ValueError:
                pass
    # Fallback: texto visible de .price ("$88.50")
    price = card.select_one(".price .sales") or card.select_one(".price")
    if price is not None:
        limpio = re.sub(r"[^\d.]", "", price.get_text().replace(",", ""))
        try:
            return float(limpio)
        except ValueError:
            pass
    return 0.0


def _parsear_tarjetas(soup) -> list[dict]:
    productos = []
    for card in soup.select("div.product[data-pid]"):
        try:
            pid = int(card.get("data-pid"))
        except (ValueError, TypeError):
            continue
        a = card.select_one(".pdp-link a")
        nombre = (a.get("title") or a.get_text(strip=True)) if a else "Desconocido"
        precio = _parsear_precio(card)
        if precio > 0 and nombre != "Desconocido" and pid:
            productos.append({"producto": nombre, "precio": precio, "pid": pid})
    return productos


def extraer_categoria_guadalajara(url_path: str, departamento: str, categoria: str) -> list[dict]:
    print(f"[*] Extrayendo GDL: {departamento} > {categoria} ({url_path})")
    productos_extraidos: list[dict] = []
    vistos: set[int] = set()

    url = f"{BASE_URL}{url_path}"
    pagina = 1

    while url:
        print(f"\n[*] Bloque {pagina}: {url[:90]}")
        try:
            r = requests.get(url, impersonate="chrome120", timeout=40)
        except Exception as e:
            print(f"[X] Error de red: {e}")
            break
        if r.status_code != 200:
            print(f"[X] HTTP {r.status_code}, fin.")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        tarjetas = _parsear_tarjetas(soup)
        nuevos = 0
        for p in tarjetas:
            if p["pid"] in vistos:
                continue
            vistos.add(p["pid"])
            nuevos += 1
            p.update({"tienda": "Farmacias Guadalajara",
                      "departamento": departamento, "categoria": categoria})
            productos_extraidos.append(p)
            print(
                f"<Supermercado(id=None, producto='{p['producto']}', precio={p['precio']}, "
                f"pid={p['pid']}, tienda='Farmacias Guadalajara', "
                f"departamento='{departamento}', categoria='{categoria}')>"
            )

        print(f"[OK] {len(tarjetas)} tarjetas ({nuevos} nuevas) en el bloque {pagina}.")

        # Sin productos nuevos = fin (evita bucles).
        if nuevos == 0:
            print("[!] Sin productos nuevos. Fin.")
            break

        btn = soup.select_one(".show-more button[data-url]")
        siguiente = btn.get("data-url") if btn else None
        if siguiente:
            url = siguiente
            pagina += 1
            time.sleep(1.2)  # cortesia
        else:
            print("[!] No hay 'Ver mas'. Fin de la categoria.")
            break

    print(f"\n[OK] EXTRACCION FINALIZADA: {len(productos_extraidos)} productos.")
    return productos_extraidos


if __name__ == "__main__":
    datos = extraer_categoria_guadalajara(
        url_path="/farmacia/medicina/dolor",
        departamento="farmacia/medicina",
        categoria="dolor",
    )
    print("\n--- MUESTRA ---")
    for item in datos[:5]:
        print(f"- {item['producto']}: ${item['precio']}")
