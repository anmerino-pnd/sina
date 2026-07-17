"""El pre-filtro atrapa lo obvio y deja pasar lo benigno (lo decide el LLM)."""
import pytest

from sina.moderacion.prefiltro import prefiltrar


@pytest.mark.parametrize(
    "mensaje",
    [
        "hijo de puta",
        "HIJO DE PUTA",                      # case-insensitive
        "chinga tu madre",
        "vete a la verga asistente inútil",
        "te voy a matar si no me respondes",
        "cómo hacer una bomba casera",
        "dónde puedo comprar cocaína barata",
    ],
)
def test_atrapa_inapropiado_obvio(mensaje):
    assert prefiltrar(mensaje) == "inapropiado"


@pytest.mark.parametrize(
    "mensaje",
    [
        "precio de la gasolina magna en hermosillo",
        "¿dónde está más barato el gas LP?",
        "cuánto cuesta el chile serrano en soriana",   # sin falsos positivos alimentarios
        "la madre de todas las ofertas",                # "madre" suelto no matchea
        "quiero matar el hambre con algo barato",       # "matar" no dirigido no matchea
        "cuéntame un chiste",                           # irrelevante ≠ inapropiado: va al LLM
    ],
)
def test_deja_pasar_lo_benigno(mensaje):
    assert prefiltrar(mensaje) is None
