"""Tool de canasta básica: arma la canasta más económica con los precios de supermercado."""
from __future__ import annotations

from typing import Any

from sina.agent.tools.base import ContextoConsulta, Tool
from sina.config.canasta import CANASTA_BASICA
from sina.db.repository import SupermercadoRepository


def _tools(ctx: ContextoConsulta) -> list[Tool]:
    repo = SupermercadoRepository()

    def armar_canasta(presupuesto: float | None = None) -> dict[str, Any]:
        items = []
        total = 0.0
        for item, terminos in CANASTA_BASICA.items():
            # Usa el primer término de búsqueda del item (p. ej. "Aceite").
            filas = repo.buscar(q=terminos[0], limit=5)
            if not filas:
                items.append({"item": item, "encontrado": False})
                continue
            mejor = min(filas, key=lambda f: f["precio"])
            total += mejor["precio"]
            items.append({
                "item": item,
                "encontrado": True,
                "producto": mejor["producto"],
                "precio": mejor["precio"],
                "tienda": mejor["tienda"],
            })

        resultado: dict[str, Any] = {
            "items": items,
            "encontrados": sum(1 for i in items if i.get("encontrado")),
            "total_items": len(CANASTA_BASICA),
            "costo_canasta_minima": round(total, 2),
        }
        if presupuesto is not None:
            resultado["presupuesto"] = presupuesto
            resultado["alcanza"] = total <= presupuesto
            resultado["diferencia"] = round(presupuesto - total, 2)
        return resultado

    return [
        Tool(
            nombre="armar_canasta",
            descripcion=(
                "Arma la canasta básica (aceite, arroz, frijol, huevo, leche, etc.) eligiendo el "
                "producto más barato de cada rubro y suma el costo mínimo. Opcional: comparar contra un presupuesto."
            ),
            parametros={
                "properties": {
                    "presupuesto": {"type": "number", "description": "Presupuesto en pesos para comparar (opcional)."},
                },
                "required": [],
            },
            fn=armar_canasta,
        )
    ]
