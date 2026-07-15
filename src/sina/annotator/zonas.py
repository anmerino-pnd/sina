"""
Pre-anotación de ZONAS de un flyer con visión clásica (OpenCV).

Los volantes de Casa Ley NO tienen pasillos anchos en blanco entre productos:
usan **paneles de color** (verde en frutas, blanco en carnes, etc.) separados por
**líneas-pasillo delgadas y claras**. Por eso el enfoque no es "binarizar contenido
y cerrar" (eso funde todo el flyer en un bloque), sino el inverso:

  1. Detectar los **pasillos** = líneas claras LARGAS (horizontales y verticales),
     quedándonos solo con lo lineal (un `open` morfológico con kernels alargados
     descarta los reflejos/empaques blancos, que son manchas, no líneas).
  2. Los **paneles** son lo que queda entre pasillos (el negativo de los pasillos).
  3. Sacar las cajas de esos paneles.

Abarrey no tiene ni pasillos blancos largos ni paneles de color: es una rejilla
densa de filas de producto separadas por listones de color y huecos blancos
DISCONTINUOS (los empaques los interrumpen), así que ninguna "línea larga"
sobrevive el open morfológico. Para ese layout existe un segundo modo, "bandas":
perfil de blancura por FILA (fracción de píxeles claros en cada renglón de la
imagen); los renglones mayormente blancos son separadores y las bandas entre
ellos —a lo ancho de la página— son las zonas (≈ una fila/departamento de
productos, granularidad ideal para el VLM). El modo se elige por tienda en
`_PARAMS` ("modo": "paneles" | "bandas").

Son PROPUESTAS: el humano las ajusta / fusiona / borra en el anotador. Los
parámetros son por tienda. No entrena nada: es el paso barato antes de YOLO,
que a futuro lo reemplaza. Las cajas corregidas por el humano se guardan como
dataset para entrenar ese YOLO.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Parámetros por tienda (fracciones del tamaño de la imagen → resolución-agnósticos).
_PARAMS: dict[str, dict] = {
    "_default": {
        "gutter": 222,          # brillo mínimo (0-255) para considerar "pasillo claro"
        "lin": 0.05,            # longitud mínima de línea-pasillo (frac. del lado)
        "sep_dilate": 0.003,    # engrosado del pasillo antes de cortar (frac. del ancho)
        "panel_open": 0.01,     # apertura para limpiar ruido dentro del panel (frac.)
        "area_min_frac": 0.006, # descarta paneles muy chicos (ruido)
        "area_max_frac": 0.55,  # descarta el marco/fondo casi completo
        "w_min_frac": 0.035,
        "h_min_frac": 0.035,
    },
    "casa_ley": {
        "gutter": 222,
        "lin": 0.05,
        "sep_dilate": 0.003,
        "panel_open": 0.01,
        "area_min_frac": 0.006,
        "area_max_frac": 0.55,
        "w_min_frac": 0.035,
        "h_min_frac": 0.035,
    },
    # Rejilla densa sin pasillos continuos → modo "bandas" (perfil por fila).
    # Tuning validado con los flyers vigentes de 2026-07-15 (6 y 4 bandas limpias).
    "abarrey": {
        "modo": "bandas",
        "blanco": 185,          # brillo mínimo (0-255) para contar un píxel como claro
        "corte": 0.75,          # frac. de píxeles claros por fila para marcar separador
        "banda_min_frac": 0.04, # descarta bandas más bajas que esto (frac. de la altura)
    },
}


def _norm_tienda(tienda: str) -> str:
    t = (tienda or "").strip().lower().replace(" ", "_")
    return t if t in _PARAMS else "_default"


def detectar_zonas(
    image_path, tienda: str = "casa_ley", max_zonas: int = 80, fusion: float = 0.0
) -> list[dict]:
    """
    Devuelve una lista de cajas `{"label": "zona", "x", "y", "w", "h"}` (píxeles)
    propuestas para el flyer. Import perezoso de OpenCV (pesado, solo este flujo).

    `fusion` (0.0–0.05, fracción del ancho) consolida cajas cercanas en bloques
    más grandes: útil en flyers de rejilla densa (fondo claro, muchas celdas), donde
    la detección cruda deja cajas fragmentadas. 0.0 = sin fusión (mejor para flyers
    de paneles de color grandes). Es una perilla que el humano sube por flyer.
    """
    import cv2  # noqa: PLC0415 — lazy, igual que process_annotations
    import numpy as np

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"OpenCV no pudo abrir la imagen: {image_path}")

    H, W = img.shape[:2]
    p = _PARAMS[_norm_tienda(tienda)]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if p.get("modo", "paneles") == "bandas":
        zonas = _zonas_por_bandas(gray, W, H, p)
        return _consolidar_y_ordenar(zonas, W, H, fusion, max_zonas, cv2, np)

    # 1. Pasillos = líneas claras LARGAS (horizontales y verticales).
    blanco = (gray > p["gutter"]).astype(np.uint8) * 255
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, int(W * p["lin"])), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(1, int(H * p["lin"]))))
    horiz = cv2.morphologyEx(blanco, cv2.MORPH_OPEN, hk)
    vert = cv2.morphologyEx(blanco, cv2.MORPH_OPEN, vk)
    pasillos = cv2.bitwise_or(horiz, vert)
    d = max(1, int(W * p["sep_dilate"]))
    pasillos = cv2.dilate(pasillos, cv2.getStructuringElement(cv2.MORPH_RECT, (d, d)), iterations=1)

    # 2. Paneles = negativo de los pasillos, limpiado de ruido chico.
    paneles = cv2.bitwise_not(pasillos)
    ok = max(1, int(W * p["panel_open"]))
    ov = max(1, int(H * p["panel_open"]))
    paneles = cv2.morphologyEx(
        paneles, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (ok, ov))
    )

    # 3. Cajas de los paneles.
    contornos, _ = cv2.findContours(paneles, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    area_min = W * H * p["area_min_frac"]
    area_max = W * H * p["area_max_frac"]
    w_min = W * p["w_min_frac"]
    h_min = H * p["h_min_frac"]

    zonas: list[dict] = []
    for c in contornos:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h
        if area < area_min or area > area_max:
            continue
        if w < w_min or h < h_min:
            continue
        zonas.append({"label": "zona", "x": int(x), "y": int(y), "w": int(w), "h": int(h)})

    return _consolidar_y_ordenar(zonas, W, H, fusion, max_zonas, cv2, np)


def _zonas_por_bandas(gray, W: int, H: int, p: dict) -> list[dict]:
    """
    Modo "bandas": fracción de píxeles claros por fila; los renglones mayormente
    blancos separan, y cada tramo continuo no-blanco es una zona a lo ancho.
    """
    blanco_por_fila = (gray > p["blanco"]).mean(axis=1)
    es_separador = blanco_por_fila > p["corte"]

    zonas: list[dict] = []
    inicio: int | None = None
    for y in range(H):
        if not es_separador[y] and inicio is None:
            inicio = y
        elif es_separador[y] and inicio is not None:
            zonas.append((inicio, y))
            inicio = None
    if inicio is not None:
        zonas.append((inicio, H))

    h_min = H * p["banda_min_frac"]
    return [
        {"label": "zona", "x": 0, "y": int(a), "w": int(W), "h": int(b - a)}
        for a, b in zonas
        if (b - a) >= h_min
    ]


def _consolidar_y_ordenar(
    zonas: list[dict], W: int, H: int, fusion: float, max_zonas: int, cv2, np
) -> list[dict]:
    """Fusión opcional (une cajas cercanas dilatando una máscara) + orden de lectura."""
    fusion = max(0.0, min(0.05, fusion))
    if fusion > 0 and len(zonas) > 1:
        mask = np.zeros((H, W), np.uint8)
        for z in zonas:
            cv2.rectangle(mask, (z["x"], z["y"]), (z["x"] + z["w"], z["y"] + z["h"]), 255, -1)
        d = max(1, int(W * fusion))
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_RECT, (d, d)), iterations=1)
        cont, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pad = d // 2
        fusionadas: list[dict] = []
        for c in cont:
            x, y, w, h = cv2.boundingRect(c)
            # Revierte el margen que agregó la dilatación, acotando a la imagen.
            x = min(W - 1, x + pad); y = min(H - 1, y + pad)
            w = max(1, w - 2 * pad); h = max(1, h - 2 * pad)
            fusionadas.append({"label": "zona", "x": int(x), "y": int(y), "w": int(w), "h": int(h)})
        zonas = fusionadas

    # Orden de lectura: por bandas horizontales (arriba→abajo), luego izq→der.
    banda = max(1, int(H * 0.05))
    zonas.sort(key=lambda z: (z["y"] // banda, z["x"]))
    if len(zonas) > max_zonas:
        log.info("detectar_zonas: %d zonas → recortado a %d", len(zonas), max_zonas)
    return zonas[:max_zonas]
