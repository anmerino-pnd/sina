"""
Pre-filtro determinista (MEJORA #3): regex para lo OBVIAMENTE inapropiado,
que corta antes de gastar la llamada al clasificador LLM y funciona incluso
con Ollama caído.

Deliberadamente conservador: solo insultos fuertes dirigidos, lenguaje de odio
y amenazas explícitas. Lo ambiguo (groserías sueltas de frustración, dobles
sentidos) lo decide el LLM con el contexto del historial. NO intenta detectar
"irrelevante" por regex: demasiados falsos positivos.
"""
from __future__ import annotations

import re

_PATRONES_INAPROPIADOS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        # Insultos fuertes dirigidos a alguien (tú/usted/el asistente).
        r"\b(?:eres|son|est[uú]pido|vales)\s+(?:un[a]?\s+)?(?:mierda|basura|imb[eé]cil|idiota|pendej[oa])\b",
        r"\bhij[oa]\s+de\s+(?:puta|perra|tu\s+put[a-z]*\s+madre)\b",
        r"\bchinga\s+(?:tu|a\s+tu)\s+madre\b",
        r"\bvete\s+a\s+la\s+verga\b",
        r"\bp[uú]drete\b",
        # Amenazas explícitas de violencia.
        r"\bte\s+voy\s+a\s+(?:matar|golpear|partir|romper|violar)\b",
        r"\bvoy\s+a\s+matar(?:te|los|las)?\b",
        r"\bquiero\s+matar\s+a\b",
        # Solicitudes claramente ilegales.
        r"\bc[oó]mo\s+(?:hacer|fabricar|armar)\s+(?:una\s+)?(?:bomba|explosivo)s?\b",
        r"\b(?:comprar|conseguir|vender)\s+(?:droga|coca[ií]na|fentanilo|armas?\s+ilegal)\w*\b",
        # Slurs / lenguaje de odio.
        r"\bput[oa]s?\s+(?:indio|negro|gay|joto|marica)\w*\b",
        r"\bpinches?\s+(?:indios?|negros?|jotos?|maricas?)\b",
    )
]


def prefiltrar(mensaje: str) -> str | None:
    """Devuelve "inapropiado" si el mensaje matchea un patrón obvio; None si no."""
    for patron in _PATRONES_INAPROPIADOS:
        if patron.search(mensaje):
            return "inapropiado"
    return None
