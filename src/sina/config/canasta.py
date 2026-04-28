"""
Configuración de la canasta básica y lógica de procesamiento.
"""

CANASTA_BASICA: dict[str, list[str]] = {
    "Aceite":          ["Aceite"],
    "Arroz":           ["Arroz"],
    "Frijol":          ["Frijol", "Frijoles"],
    "Azúcar":          ["Azúcar"],
    "Huevo":           ["Huevo"],
    "Leche":           ["Leche Ultrapasteurizada", "Leche Condensada",
                        "Leche Evaporada", "Leche en Polvo"],
    "Pan":             ["Pan Blanco Bolillo", "Pan de Caja",
                        "Pan Dulce", "Pastellios y Pan Dulce Empaquetado"],
    "Tortilla":        ["Tortilla de Maíz"],
    "Pollo":           ["Carne Pollo"],
    "Atún":            ["Atún"],
    "Jabón de pasta":  ["Jabón de Pasta"],
    "Papel higiénico": ["Papel Higiénico"],
    "Pasta para sopa": ["Pasta para Sopa"],
    "Sal":             ["Sal Molida de Mesa"],
}

# ── Cache del mapeo inverso ──────────────────────────
_PRODUCTO_A_ITEM: dict[str, str] | None = None


def _build_producto_a_item() -> dict[str, str]:
    global _PRODUCTO_A_ITEM
    if _PRODUCTO_A_ITEM is None:
        _PRODUCTO_A_ITEM = {}
        for item, productos in CANASTA_BASICA.items():
            for producto in productos:
                _PRODUCTO_A_ITEM[producto] = item
    return _PRODUCTO_A_ITEM


def producto_a_item(producto: str) -> str | None:
    """Dado un nombre de producto de la DB, devuelve el item de canasta o None."""
    return _build_producto_a_item().get(producto)


def todos_los_productos() -> list[str]:
    """Lista plana de todos los nombres de producto que forman la canasta."""
    return [p for productos in CANASTA_BASICA.values() for p in productos]


def estructurar_canasta(registros: list[dict]) -> dict:
    """
    Transforma registros crudos de QQP (ya filtrados por productos de canasta)
    en la estructura JSON que consume el frontend.
    """
    if not registros:
        return {"items": {}, "cadenas": [], "resumen": _resumen_vacio()}

    items_data: dict[str, list[dict]] = {}
    cadenas_set: set[str] = set()

    for r in registros:
        item = producto_a_item(r["producto"])
        if item is None:
            continue
        items_data.setdefault(item, []).append(r)
        cadenas_set.add(r["cadena_comercial"])

    items_resultado: dict[str, dict] = {}
    costo_canasta_minima = 0.0

    for item_name in CANASTA_BASICA:
        registros_item = items_data.get(item_name, [])
        if not registros_item:
            continue

        presentaciones: dict[str, list[dict]] = {}
        for r in registros_item:
            presentaciones.setdefault(r["presentacion"], []).append(r)

        pres_resultado: dict[str, dict] = {}
        for pres_name, opciones in presentaciones.items():
            opciones_ordenadas = sorted(opciones, key=lambda x: x["precio"])
            pres_resultado[pres_name] = {
                "opciones": [
                    {
                        "precio": o["precio"],
                        "marca":  o["marca"],
                        "cadena": o["cadena_comercial"],
                        "tienda": o["nombre_comercial"],
                    }
                    for o in opciones_ordenadas
                ]
            }

        mejor_global = min(registros_item, key=lambda x: x["precio"])

        items_resultado[item_name] = {
            "presentaciones":       pres_resultado,
            "default_presentacion": mejor_global["presentacion"],
            "default_precio":       mejor_global["precio"],
            "default_cadena":       mejor_global["cadena_comercial"],
            "default_marca":        mejor_global["marca"],
        }

        costo_canasta_minima += mejor_global["precio"]

    return {
        "items":   items_resultado,
        "cadenas": sorted(cadenas_set),
        "resumen": {
            "costo_canasta_minima": round(costo_canasta_minima, 2),
            "n_cadenas":            len(cadenas_set),
            "n_items":              len(items_resultado),
            "n_productos_total":    len(registros),
        },
    }


def _resumen_vacio() -> dict:
    return {
        "costo_canasta_minima": 0,
        "n_cadenas": 0,
        "n_items": 0,
        "n_productos_total": 0,
    }