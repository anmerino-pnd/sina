"""Utilidades geográficas para las tools de cercanía."""
from __future__ import annotations

import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distancia en kilómetros entre dos coordenadas (fórmula de haversine).

    Espeja `frontend/src/lib/geo.ts` (R = 6371 km) para que el "cerca de mí" del
    chat coincida con el de la página de Gasolina.
    """
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
