"""Tools de supermercados: búsqueda de productos y comparación de una lista."""
from __future__ import annotations

from typing import Any

from sina.agent.tools.base import ContextoConsulta, Tool
from sina.db.repository import SupermercadoRepository


def _tools(ctx: ContextoConsulta) -> list[Tool]:
    repo = SupermercadoRepository()

    def buscar_producto(
        producto: str,
        tienda: str | None = None,
        categoria: str | None = None,
        top_n: int = 5,
    ) -> dict[str, Any]:
        if not producto or not producto.strip():
            return {"error": "falta el nombre del producto."}
        top_n = max(1, min(int(top_n), 20))
        filas = repo.buscar(q=producto.strip(), tienda=tienda, categoria=categoria, limit=top_n)
        return {
            "producto_buscado": producto,
            "total": len(filas),
            "resultados": [
                {"producto": f["producto"], "precio": f["precio"],
                 "tienda": f["tienda"], "categoria": f.get("categoria")}
                for f in filas
            ],
        }

    def comparar_lista(items: list[str], municipio: str | None = None) -> dict[str, Any]:
        # Nota: los productos de supermercado no tienen ubicación; `municipio` se ignora.
        if not items:
            return {"error": "la lista de items está vacía."}
        detalle = []
        total_mejor = 0.0
        for item in items:
            filas = repo.buscar(q=str(item).strip(), limit=5)
            if not filas:
                detalle.append({"item": item, "encontrado": False})
                continue
            mejor = min(filas, key=lambda f: f["precio"])
            total_mejor += mejor["precio"]
            detalle.append({
                "item": item,
                "encontrado": True,
                "mas_barato": {"producto": mejor["producto"], "precio": mejor["precio"],
                               "tienda": mejor["tienda"]},
            })
        return {
            "items": detalle,
            "total_estimado_mas_barato": round(total_mejor, 2),
            "encontrados": sum(1 for d in detalle if d.get("encontrado")),
            "solicitados": len(items),
        }

    return [
        Tool(
            nombre="buscar_producto",
            descripcion=(
                "Busca un producto de supermercado por nombre (búsqueda semántica o por texto) "
                "y devuelve las opciones más baratas, con su tienda. Filtros opcionales por tienda/categoría."
            ),
            parametros={
                "properties": {
                    "producto": {"type": "string", "description": "Qué producto buscar, p. ej. 'leche', 'aceite'."},
                    "tienda": {"type": "string", "description": "Filtrar por tienda (Soriana, Del Sol, Benavides, Farmacias Guadalajara)."},
                    "categoria": {"type": "string", "description": "Filtrar por categoría."},
                    "top_n": {"type": "integer", "description": "Cuántos resultados (1-20)."},
                },
                "required": ["producto"],
            },
            fn=buscar_producto,
        ),
        Tool(
            nombre="comparar_lista",
            descripcion=(
                "Dada una lista de la compra (varios productos), encuentra el más barato de cada uno "
                "y estima el total mínimo."
            ),
            parametros={
                "properties": {
                    "items": {"type": "array", "items": {"type": "string"},
                              "description": "Lista de productos a comparar."},
                    "municipio": {"type": "string", "description": "Ignorado por ahora (los productos no tienen ubicación)."},
                },
                "required": ["items"],
            },
            fn=comparar_lista,
        ),
    ]
