"""Ensambla el registro de tools por request, ligado al contexto de la consulta."""
from __future__ import annotations

from typing import Any

from sina.agent.tools.base import ContextoConsulta, RegistroTools, Tool
from sina.agent.tools import (
    gasolina_tools, gas_lp_tools, supermercado_tools, canasta_tools,
)
from sina.db.repository import (
    GasolinaRepository, GasLPRepository, SupermercadoRepository,
)


def _tools_datos(ctx: ContextoConsulta) -> list[Tool]:
    def datos_disponibles() -> dict[str, Any]:
        """Frescura de cada fuente (para responder '¿cuándo se actualizó?')."""
        return {
            "gasolina": GasolinaRepository().estado_cache(),
            "gas_lp": GasLPRepository().estado_cache(),
            "supermercados": SupermercadoRepository().estado_cache(),
        }

    return [
        Tool(
            nombre="datos_disponibles",
            descripcion="Indica la última actualización y vigencia de cada fuente de datos.",
            parametros={"properties": {}, "required": []},
            fn=datos_disponibles,
        )
    ]


def construir_registro(contexto: ContextoConsulta) -> RegistroTools:
    """Crea un RegistroTools con todas las tools cerradas sobre el contexto."""
    registro = RegistroTools()
    for modulo in (gasolina_tools, gas_lp_tools, supermercado_tools, canasta_tools):
        for tool in modulo._tools(contexto):
            registro.registrar(tool)
    for tool in _tools_datos(contexto):
        registro.registrar(tool)
    return registro
