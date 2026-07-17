"""
Router de la capa de moderación: baneo → pre-filtro → clasificador → decisión.

Orden (paridad con el sistema original):
1. Si la identidad ya está baneada, corta de inmediato con el tiempo restante
   (sin llamar al clasificador ni al agente).
2. Pre-filtro determinista (regex) para lo obviamente inapropiado.
3. Clasificador LLM (`relevante` | `irrelevante` | `inapropiado`).
4. `relevante` pasa al agente; `irrelevante` responde texto cortés predefinido;
   `inapropiado` aplica el baneo progresivo; cualquier otra cosa pide reformular.

Toda decisión se audita en `moderacion_log`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from sina.db.stores import ModeracionStore
from sina.moderacion.clasificador import clasificar
from sina.moderacion.prefiltro import prefiltrar
from sina.moderacion.textos import TEXTO_IRRELEVANTE, TEXTO_NO_ENTENDI


@dataclass
class ResultadoModeracion:
    permitido: bool
    etiqueta: str
    origen: str      # "baneo" | "prefiltro" | "llm" | "fallback"
    accion: str      # "paso" | "rechazo_irrelevante" | "advertencia" | "baneo_*" | ...
    respuesta: str | None = None  # texto al usuario cuando NO pasa al agente


def moderar(
    mensaje: str,
    historial: list[dict] | None,
    identidad: str,
    store: ModeracionStore | None = None,
    clasificar_fn=None,
) -> ResultadoModeracion:
    """
    Decide qué hacer con la consulta ANTES de que llegue al agente principal.
    `store` y `clasificar_fn` son inyectables para pruebas unitarias.
    """
    inicio = time.time()
    store = store if store is not None else ModeracionStore()
    clasificar_fn = clasificar_fn or clasificar

    # 1. Baneo vigente: corta antes de clasificar.
    msg_baneo = store.revisar_baneo(identidad)
    if msg_baneo is not None:
        resultado = ResultadoModeracion(
            permitido=False, etiqueta="baneado", origen="baneo",
            accion="bloqueado_por_baneo", respuesta=msg_baneo,
        )
        store.auditar(identidad, mensaje, resultado.etiqueta, resultado.origen,
                      resultado.accion, (time.time() - inicio) * 1000.0)
        return resultado

    # 2. Pre-filtro determinista; 3. clasificador LLM.
    etiqueta = prefiltrar(mensaje)
    if etiqueta is not None:
        origen = "prefiltro"
    else:
        etiqueta, origen = clasificar_fn(mensaje, historial)

    # 4. Enrutar según la etiqueta.
    if etiqueta == "relevante":
        resultado = ResultadoModeracion(
            permitido=True, etiqueta=etiqueta, origen=origen, accion="paso"
        )
    elif etiqueta == "irrelevante":
        resultado = ResultadoModeracion(
            permitido=False, etiqueta=etiqueta, origen=origen,
            accion="rechazo_irrelevante", respuesta=TEXTO_IRRELEVANTE,
        )
    elif etiqueta == "inapropiado":
        respuesta, accion = store.registrar_inapropiado(identidad)
        resultado = ResultadoModeracion(
            permitido=False, etiqueta=etiqueta, origen=origen,
            accion=accion, respuesta=respuesta,
        )
    else:
        # Con el schema del clasificador es prácticamente inalcanzable;
        # se mantiene por paridad con el sistema original.
        resultado = ResultadoModeracion(
            permitido=False, etiqueta=etiqueta, origen=origen,
            accion="etiqueta_desconocida", respuesta=TEXTO_NO_ENTENDI,
        )

    store.auditar(identidad, mensaje, resultado.etiqueta, resultado.origen,
                  resultado.accion, (time.time() - inicio) * 1000.0)
    return resultado
