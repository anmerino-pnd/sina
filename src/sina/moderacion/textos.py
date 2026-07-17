"""
Respuestas predefinidas de la capa de moderación (sin LLM).

Los mensajes de advertencia/baneo/tiempo restante viven en `baneo.py` porque
dependen de la sanción calculada; aquí van los textos fijos del router.
"""

TEXTO_IRRELEVANTE = (
    "Soy SINA, el asistente de ahorro para familias mexicanas: puedo ayudarte a "
    "encontrar precios de gasolina, gas LP y productos de supermercado o farmacia, "
    "comparar tiendas y armar tu canasta básica. Esa consulta queda fuera de mi "
    "alcance; ¿me preguntas algo sobre precios o ahorro?"
)

TEXTO_NO_ENTENDI = (
    "No entendí tu consulta. ¿Puedes reformularla? Recuerda que puedo ayudarte con "
    "precios de gasolina, gas LP y productos de supermercado en México."
)
