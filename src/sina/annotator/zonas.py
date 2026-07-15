"""
Pre-anotación de ZONAS de un flyer con visión clásica (OpenCV).

Idea: las zonas de producto están separadas por espacios en blanco. Binarizamos
el contenido (lo que NO es fondo claro), lo cerramos morfológicamente para unir lo
que está dentro de una misma zona sin cruzar los pasillos en blanco, y sacamos las
cajas de los blobs resultantes. Son PROPUESTAS: el humano las ajusta/agrega/borra
en el anotador. Los parámetros son por tienda (Ley hoy; Abarrey luego, con su
propio tuning), porque cada cadena tiene un layout distinto.

No entrena nada: es el paso barato antes de YOLO. Las cajas corregidas por el
humano se guardan como dataset para entrenar YOLO a futuro.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Parámetros por tienda (fracciones del tamaño de la imagen → resolución-agnósticos).
_PARAMS: dict[str, dict] = {
    "_default": {
        "umbral": 235,          # > esto se considera fondo claro
        "kx": 0.020,            # cierre horizontal (frac. del ancho)
        "ky": 0.020,            # cierre vertical (frac. del alto)
        "area_min_frac": 0.004, # descarta blobs muy chicos (ruido)
        "w_min_frac": 0.03,
        "h_min_frac": 0.02,
    },
    "casa_ley": {
        "umbral": 235,
        "kx": 0.018,
        "ky": 0.016,
        "area_min_frac": 0.004,
        "w_min_frac": 0.03,
        "h_min_frac": 0.02,
    },
}


def _norm_tienda(tienda: str) -> str:
    t = (tienda or "").strip().lower().replace(" ", "_")
    return t if t in _PARAMS else "_default"


def detectar_zonas(image_path, tienda: str = "casa_ley", max_zonas: int = 80) -> list[dict]:
    """
    Devuelve una lista de cajas `{"label": "zona", "x", "y", "w", "h"}` (píxeles)
    propuestas para el flyer. Import perezoso de OpenCV (pesado, solo este flujo).
    """
    import cv2  # noqa: PLC0415 — lazy, igual que process_annotations
    import numpy as np

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"OpenCV no pudo abrir la imagen: {image_path}")

    H, W = img.shape[:2]
    p = _PARAMS[_norm_tienda(tienda)]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Contenido = lo que NO es fondo claro (INV: contenido → 255).
    _, binaria = cv2.threshold(gray, p["umbral"], 255, cv2.THRESH_BINARY_INV)

    kx = max(1, int(W * p["kx"]))
    ky = max(1, int(H * p["ky"]))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kx, ky))
    cerrada = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel, iterations=1)

    contornos, _ = cv2.findContours(cerrada, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    area_min = W * H * p["area_min_frac"]
    w_min = W * p["w_min_frac"]
    h_min = H * p["h_min_frac"]

    zonas: list[dict] = []
    for c in contornos:
        x, y, w, h = cv2.boundingRect(c)
        if w * h < area_min or w < w_min or h < h_min:
            continue
        # Descarta cajas que abarcan casi toda la imagen (marco/fondo completo).
        if w > W * 0.98 and h > H * 0.98:
            continue
        zonas.append({"label": "zona", "x": int(x), "y": int(y), "w": int(w), "h": int(h)})

    # Orden de lectura: por bandas horizontales (arriba→abajo), luego izq→der.
    banda = max(1, int(H * 0.05))
    zonas.sort(key=lambda z: (z["y"] // banda, z["x"]))
    if len(zonas) > max_zonas:
        log.info("detectar_zonas: %d zonas → recortado a %d", len(zonas), max_zonas)
    return zonas[:max_zonas]
