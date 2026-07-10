"""Tools de Gas LP: precios por localidad y listado de localidades."""
from __future__ import annotations

from typing import Any

from sina.agent.tools.base import ContextoConsulta, Tool
from sina.db.repository import MunicipioRepository
from sina.scraping.gobierno.cne_gas_lp import get_precios_gas_lp, get_localidades_by_municipio


def _tools(ctx: ContextoConsulta) -> list[Tool]:
    def buscar_gas_lp(
        localidad: str | None = None,
        municipio: str | None = None,
        estado: str | None = None,
        tipo: str | None = None,
        capacidad: int | None = None,
        top_n: int = 5,
    ) -> dict[str, Any]:
        estado = (estado or ctx.estado or "").strip()
        municipio = (municipio or ctx.municipio or "").strip()
        localidad = (localidad or ctx.localidad or "").strip()
        if not estado or not municipio:
            return {"necesita": "municipio", "mensaje": "Necesito estado y municipio."}
        if not localidad:
            return {"necesita": "localidad",
                    "mensaje": "El Gas LP se consulta por localidad. Usa listar_localidades_gas_lp."}

        res = get_precios_gas_lp(estado, municipio, localidad)
        if res.get("error"):
            return {"error": res["error"]}

        filas = list(res.get("autotanques", [])) + list(res.get("recipientes", []))
        if tipo:
            filas = [f for f in filas if f.get("tipo") == tipo.strip().lower()]
        if capacidad is not None:
            filas = [f for f in filas if f.get("capacidad_recipiente") == capacidad]
        filas.sort(key=lambda f: f.get("precio", 1e9))

        top_n = max(1, min(int(top_n), 10))
        return {
            "estado": estado, "municipio": municipio, "localidad": localidad,
            "fuente": res.get("fuente"), "fecha_datos": res.get("fecha_datos"),
            "total": len(filas),
            "resultados": [
                {
                    "marca": f.get("marca_comercial"),
                    "tipo": f.get("tipo"),
                    "capacidad": f.get("capacidad_recipiente"),
                    "precio": f.get("precio"),
                }
                for f in filas[:top_n]
            ],
        }

    def listar_localidades_gas_lp(
        municipio: str | None = None,
        estado: str | None = None,
    ) -> dict[str, Any]:
        estado = (estado or ctx.estado or "").strip()
        municipio = (municipio or ctx.municipio or "").strip()
        if not estado or not municipio:
            return {"necesita": "municipio", "mensaje": "Necesito estado y municipio."}
        ids = MunicipioRepository().obtener_ids(estado, municipio)
        if ids is None:
            return {"error": f"no encontré el municipio '{municipio}' en '{estado}'."}
        entidad_id, municipio_id = ids
        locs = get_localidades_by_municipio(entidad_id, municipio_id)
        return {"estado": estado, "municipio": municipio,
                "localidades": [l.get("nombre") for l in locs]}

    return [
        Tool(
            nombre="buscar_gas_lp",
            descripcion=(
                "Precios de Gas LP (por kilo) por localidad. Se puede filtrar por tipo "
                "('autotanque'|'recipiente') y por capacidad del recipiente. Requiere la "
                "localidad; si no la conoces, llama antes a listar_localidades_gas_lp."
            ),
            parametros={
                "properties": {
                    "localidad": {"type": "string", "description": "Localidad (obligatoria para Gas LP)."},
                    "municipio": {"type": "string", "description": "Municipio (opcional; usa el del contexto)."},
                    "estado": {"type": "string", "description": "Estado (opcional; usa el del contexto)."},
                    "tipo": {"type": "string", "enum": ["autotanque", "recipiente"]},
                    "capacidad": {"type": "integer", "description": "Capacidad del recipiente en kg (solo recipientes)."},
                    "top_n": {"type": "integer", "description": "Cuántos proveedores devolver (1-10)."},
                },
                "required": [],
            },
            fn=buscar_gas_lp,
        ),
        Tool(
            nombre="listar_localidades_gas_lp",
            descripcion="Lista las localidades disponibles de Gas LP para un municipio.",
            parametros={
                "properties": {
                    "municipio": {"type": "string"},
                    "estado": {"type": "string"},
                },
                "required": [],
            },
            fn=listar_localidades_gas_lp,
        ),
    ]
