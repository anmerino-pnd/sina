"""
Helper de scraping para Farmacias Guadalajara (Salesforce Commerce Cloud).

Misma plataforma que Soriana, pero aqui NO necesitamos navegador: los productos
se renderizan server-side y la paginacion es un endpoint HTML ("Show More" ->
Search-UpdateGrid?...&start=N&sz=20). Vamos siguiendo ese enlace hasta agotarlo.

Devuelve dicts con el formato que consume
`SupermercadoRepository.upsert_productos` (clave `pid_origen`).
"""
import re
import time
from typing import List, Dict, Any

from bs4 import BeautifulSoup
from curl_cffi import requests

_DELAY_ENTRE_BLOQUES_S = 1.2


def _parsear_precio(card) -> float:
    """Precio: preferimos el atributo `content` de .sales .value; fallback al texto."""
    val = card.select_one(".sales .value")
    if val is not None and val.get("content"):
        try:
            return float(val.get("content"))
        except ValueError:
            pass
    price = card.select_one(".price .sales") or card.select_one(".price")
    if price is not None:
        limpio = re.sub(r"[^\d.]", "", price.get_text().replace(",", ""))
        try:
            return float(limpio)
        except ValueError:
            pass
    return 0.0


def _parsear_tarjetas(soup, depto: str, categoria: str) -> List[Dict[str, Any]]:
    productos: List[Dict[str, Any]] = []
    for card in soup.select("div.product[data-pid]"):
        try:
            pid = int(card.get("data-pid"))
        except (ValueError, TypeError):
            continue
        a = card.select_one(".pdp-link a")
        nombre = (a.get("title") or a.get_text(strip=True)) if a else "Desconocido"
        precio = _parsear_precio(card)
        if precio > 0 and nombre != "Desconocido" and pid:
            productos.append({
                "producto": nombre,
                "precio": precio,
                "pid_origen": pid,
                "tienda": "Farmacias Guadalajara",
                "departamento": depto,
                "categoria": categoria,
                "subcategoria": None,
            })
    return productos


def scrape_guadalajara_page(
    base_url: str,
    url_path: str,
    depto: str,
    categoria: str,
    impersonate: str = "chrome120",
    timeout: int = 40,
) -> List[Dict[str, Any]]:
    """
    Extrae todos los productos de una categoria siguiendo la paginacion
    "Show More" de SFCC hasta que ya no exista el boton.
    """
    productos: List[Dict[str, Any]] = []
    vistos: set[int] = set()
    url = f"{base_url}{url_path}"
    bloque = 1

    while url:
        print(f"  [+] Bloque {bloque}: {url[:80]}")
        try:
            r = requests.get(url, impersonate=impersonate, timeout=timeout)
        except Exception as e:
            print(f"  [X] Error de red: {e}")
            break
        if r.status_code != 200:
            print(f"  [X] HTTP {r.status_code}, fin de la categoria.")
            break

        soup = BeautifulSoup(r.text, "html.parser")
        tarjetas = _parsear_tarjetas(soup, depto, categoria)

        nuevos = 0
        for p in tarjetas:
            if p["pid_origen"] in vistos:
                continue
            vistos.add(p["pid_origen"])
            productos.append(p)
            nuevos += 1

        print(f"  [+] {len(tarjetas)} tarjetas ({nuevos} nuevas) en el bloque {bloque}.")

        if nuevos == 0:  # nada nuevo -> fin (evita bucles infinitos)
            break

        btn = soup.select_one(".show-more button[data-url]")
        siguiente = btn.get("data-url") if btn else None
        if siguiente:
            url = siguiente
            bloque += 1
            time.sleep(_DELAY_ENTRE_BLOQUES_S)
        else:
            print("  [!] Fin de paginacion.")
            break

    return productos
