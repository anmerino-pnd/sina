"""Tool de gasolina: precios por municipio, con orden por precio o cercanía."""
from __future__ import annotations

from typing import Any

from sina.agent.geo import haversine_km
from sina.agent.tools.base import ContextoConsulta, Tool
from sina.db.repository import MunicipioRepository
from sina.scraping.gobierno.cre_gasolina import get_precios_gasolina

# Sinónimos de tipo de combustible → columna del modelo.
_TIPO_A_COLUMNA = {
    "regular": "magna", "magna": "magna", "verde": "magna",
    "premium": "premium", "roja": "premium",
    "diesel": "diesel", "diésel": "diesel",
}


def _tools(ctx: ContextoConsulta) -> list[Tool]:
    def buscar_gasolina(
        tipo: str = "regular",
        municipio: str | None = None,
        estado: str | None = None,
        ordenar_por: str = "precio",
        top_n: int = 5,
    ) -> dict[str, Any]:
        estado = (estado or ctx.estado or "").strip()
        municipio = (municipio or ctx.municipio or "").strip()
        if not estado or not municipio:
            return {"necesita": "municipio",
                    "mensaje": "Necesito el estado y municipio para buscar gasolina."}

        columna = _TIPO_A_COLUMNA.get(tipo.strip().lower())
        if columna is None:
            return {"error": f"tipo de combustible no reconocido: {tipo}",
                    "tipos_validos": ["regular", "premium", "diesel"]}

        ids = MunicipioRepository().obtener_ids(estado, municipio)
        if ids is None:
            return {"error": f"no encontré el municipio '{municipio}' en '{estado}'."}
        entidad_id, municipio_id = ids

        res = get_precios_gasolina(estado, municipio, entidad_id, municipio_id)
        if res.get("status") != "ok":
            return {"error": res.get("detail", "no pude obtener precios de gasolina.")}

        filas = [d for d in res.get("datos", []) if d.get(columna) is not None]
        if not filas:
            return {"total": 0,
                    "mensaje": f"no hay precios de {tipo} en {municipio}, {estado}."}

        usar_cercania = ordenar_por == "cercania" and ctx.tiene_coordenadas
        resultados = []
        for d in filas:
            item = {
                "nombre": d.get("nombre"),
                "direccion": d.get("direccion"),
                "precio": d.get(columna),
                "latitud": d.get("latitud"),
                "longitud": d.get("longitud"),
            }
            if usar_cercania and d.get("latitud") is not None and d.get("longitud") is not None:
                item["distancia_km"] = round(
                    haversine_km(ctx.lat, ctx.lng, d["latitud"], d["longitud"]), 2
                )
            resultados.append(item)

        if usar_cercania:
            resultados = [r for r in resultados if "distancia_km" in r]
            resultados.sort(key=lambda r: r["distancia_km"])
        else:
            resultados.sort(key=lambda r: r["precio"])

        top_n = max(1, min(int(top_n), 10))
        return {
            "tipo": tipo,
            "estado": estado,
            "municipio": municipio,
            "fuente": res.get("fuente"),
            "fecha_datos": res.get("fecha_datos"),
            "ordenado_por": "cercania" if usar_cercania else "precio",
            "total": len(resultados),
            "resultados": resultados[:top_n],
        }

    return [
        Tool(
            nombre="buscar_gasolina",
            descripcion=(
                "Precios de gasolina (regular/premium/diesel) en un municipio. "
                "Ordena por precio (más barata primero) o por cercanía si el usuario "
                "compartió su ubicación. Si no se da municipio/estado, usa el del contexto."
            ),
            parametros={
                "properties": {
                    "tipo": {"type": "string", "enum": ["regular", "premium", "diesel"],
                             "description": "Tipo de combustible."},
                    "municipio": {"type": "string", "description": "Municipio (opcional; usa el del contexto si falta)."},
                    "estado": {"type": "string", "description": "Estado (opcional; usa el del contexto si falta)."},
                    "ordenar_por": {"type": "string", "enum": ["precio", "cercania"],
                                    "description": "Criterio de orden. 'cercania' requiere ubicación del usuario."},
                    "top_n": {"type": "integer", "description": "Cuántas estaciones devolver (1-10)."},
                },
                "required": ["tipo"],
            },
            fn=buscar_gasolina,
        )
    ]
