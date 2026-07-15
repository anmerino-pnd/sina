"""
Spider de volantes (flyers) de Abarrey.

A diferencia de Casa Ley (Publitas, requiere Selenium), la pagina de ofertas de
Abarrey (ofertas.php) es server-rendered: las imagenes del volante son <img>
directos, asi que basta curl_cffi + BeautifulSoup (patron de benavides_helper).

Espeja la firma de `casaley_spider.download_flyer` (sin BrowserConfig, no hay
navegador) y escribe la misma estructura: base_dir/<ciudad>/<YYYY-MM-DD>/page_NN.jpg
+ metadata.json, para que el anotador la consuma sin cambios.
"""
import os
import re
import json
import time
import datetime
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse, quote

from bs4 import BeautifulSoup
from curl_cffi import requests

# Cortesia entre descargas para no martillar el servidor.
_DELAY_ENTRE_IMAGENES_S = 1.0

# Firmas magicas de los formatos que aceptamos como pagina de volante.
_MAGIC_JPEG = b"\xff\xd8\xff"
_MAGIC_PNG = b"\x89PNG"


def _es_imagen(contenido: bytes) -> bool:
    return contenido.startswith(_MAGIC_JPEG) or contenido.startswith(_MAGIC_PNG)


def _resolver_url_imagen(base_url: str, src: str) -> str:
    """Resuelve el src relativo contra la pagina y escapa espacios u otros
    caracteres que el HTML de Abarrey a veces trae crudos."""
    absoluta = urljoin(base_url, src.strip())
    partes = urlparse(absoluta)
    return absoluta.replace(partes.path, quote(partes.path), 1)


def _extraer_srcs_flyer(html: str) -> List[str]:
    """Los <img> del volante viven bajo ofertas/ (p. ej. ofertas/01_movil.jpg)."""
    soup = BeautifulSoup(html, "html.parser")
    srcs: List[str] = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if isinstance(src, str) and "ofertas/" in src and src not in srcs:
            srcs.append(src)
    return srcs


def _extraer_vigencia(html: str) -> Optional[str]:
    """Texto crudo de vigencia mostrado en la pagina (ej. 'Del 11 al 17 de Julio').

    La pagina lo publica estructurado: <div class="ofertas_vigencia"> con
    "Vigencia:" y el rango en divs hijos; fallback a regex sobre el texto plano.
    """
    soup = BeautifulSoup(html, "html.parser")
    div = soup.find("div", class_="ofertas_vigencia")
    if div is not None:
        texto = div.get_text(" ", strip=True)
        texto = re.sub(r"(?i)^\s*vigencia[:\s]*", "", texto).strip()
        if texto:
            return texto
    texto = soup.get_text(" ", strip=True)
    m = re.search(r"(?i)vigencia[:\s]*(.{5,80}?)(?=\s*Ciudad:|\s*\*|$)", texto)
    return m.group(1).strip() if m else None


def _descargar_imagen(url: str, impersonate: str, timeout: int) -> Optional[bytes]:
    try:
        r = requests.get(url, impersonate=impersonate, timeout=timeout)
    except Exception as e:
        print(f"  [X] Error de red en {url}: {e}")
        return None
    if r.status_code != 200 or not _es_imagen(r.content):
        return None
    return r.content


def download_flyer(
    base_url: str,
    city: str,
    base_dir: str,
    impersonate: str = "chrome120",
    timeout: int = 30,
) -> bool:
    """
    Descarga el volante vigente de Abarrey a base_dir/<ciudad>/<hoy>/page_NN.jpg
    y escribe metadata.json (mismo esquema que Casa Ley + vigencia_texto).
    Devuelve True solo si TODAS las paginas encontradas se descargaron.
    """
    print(f"[+] Descargando volante Abarrey para: {city}")

    try:
        r = requests.get(base_url, impersonate=impersonate, timeout=timeout)
    except Exception as e:
        print(f"[X] Error de red al abrir {base_url}: {e}")
        return False
    if r.status_code != 200:
        print(f"[X] HTTP {r.status_code} en {base_url}")
        return False

    srcs = _extraer_srcs_flyer(r.text)
    if not srcs:
        print("[!] No se encontraron imagenes de ofertas en la pagina.")
        return False

    vigencia = _extraer_vigencia(r.text)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().isoformat()

    clean_city = (
        city.lower()
        .replace(" ", "_")
        .replace("á", "a").replace("é", "e")
        .replace("í", "i").replace("ó", "o").replace("ú", "u")
    )
    output_dir = os.path.join(base_dir, clean_city, today)
    os.makedirs(output_dir, exist_ok=True)

    print(f"[+] {len(srcs)} paginas encontradas -> {output_dir}")

    metadata: Dict[str, Any] = {
        "city": city,
        "extracting_date": timestamp,
        "base_url": base_url,
        "vigencia_texto": vigencia,
        "total_pages_found": len(srcs),
        "pages": {},
    }

    success = 0
    for idx, src in enumerate(srcs, start=1):
        file_name = f"page_{idx:02d}.jpg"
        url_movil = _resolver_url_imagen(base_url, src)

        # Best-effort: probar la variante sin sufijo _movil (mayor resolucion).
        contenido = None
        url_usada = url_movil
        if "_movil" in url_movil:
            url_grande = url_movil.replace("_movil", "")
            contenido = _descargar_imagen(url_grande, impersonate, timeout)
            if contenido is not None:
                url_usada = url_grande
        if contenido is None:
            contenido = _descargar_imagen(url_movil, impersonate, timeout)
            url_usada = url_movil

        if contenido is None:
            print(f"  [X] {file_name}: no se pudo descargar ({url_movil})")
            continue

        with open(os.path.join(output_dir, file_name), "wb") as f:
            f.write(contenido)
        print(f"  [+] {file_name} ({len(contenido) // 1024} KB)")
        success += 1

        metadata["pages"][file_name] = {
            "source_url": url_usada,
            "page_url": base_url,
            "size_bytes": len(contenido),
        }
        time.sleep(_DELAY_ENTRE_IMAGENES_S)

    metadata["total_pages_downloaded"] = success
    metadata["status"] = (
        "success" if success == len(srcs)
        else "partial" if success > 0
        else "failed"
    )

    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"[+] Metadata: {metadata_path}")
    print(f"[+] {success}/{len(srcs)} descargadas")
    return success == len(srcs)
