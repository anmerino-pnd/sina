"""Router de moderación: orden baneo → prefiltro → clasificador y enrutamiento."""
import pytest

from sina.moderacion.moderar import moderar
from sina.moderacion.textos import TEXTO_IRRELEVANTE, TEXTO_NO_ENTENDI


class StoreFalso:
    """ModeracionStore de mentira: sin Mongo, registra lo que se le pide."""

    def __init__(self, mensaje_baneo=None, disponible=True):
        self.mensaje_baneo = mensaje_baneo
        self.disponible = disponible
        self.strikes = 0
        self.auditados = []

    def revisar_baneo(self, identidad):
        return self.mensaje_baneo

    def registrar_inapropiado(self, identidad):
        if not self.disponible:
            return "advertencia degradada", "advertencia_sin_persistir"
        self.strikes += 1
        if self.strikes == 1:
            return "advertencia", "advertencia"
        return "baneado 1 minuto", "baneo_60s"

    def auditar(self, identidad, mensaje, etiqueta, origen, accion, duracion_ms=None):
        self.auditados.append({"etiqueta": etiqueta, "origen": origen, "accion": accion})


def _clasificador_fijo(etiqueta):
    return lambda mensaje, historial: (etiqueta, "llm")


def _clasificador_prohibido(mensaje, historial):
    raise AssertionError("el clasificador NO debe llamarse en este caso")


def test_baneado_corta_antes_de_clasificar():
    store = StoreFalso(mensaje_baneo="suspendido, vuelve en 5 minutos")
    r = moderar("precio de la magna", None, "user:abc",
                store=store, clasificar_fn=_clasificador_prohibido)
    assert r.permitido is False
    assert r.accion == "bloqueado_por_baneo"
    assert "5 minutos" in r.respuesta
    assert store.auditados[-1]["accion"] == "bloqueado_por_baneo"


def test_relevante_pasa_al_agente():
    store = StoreFalso()
    r = moderar("precio de la magna", None, "user:abc",
                store=store, clasificar_fn=_clasificador_fijo("relevante"))
    assert r.permitido is True
    assert r.respuesta is None
    assert store.auditados[-1]["accion"] == "paso"


def test_irrelevante_texto_predefinido_sin_agente():
    store = StoreFalso()
    r = moderar("cuéntame un chiste", None, "user:abc",
                store=store, clasificar_fn=_clasificador_fijo("irrelevante"))
    assert r.permitido is False
    assert r.respuesta == TEXTO_IRRELEVANTE
    assert store.strikes == 0  # irrelevante NO acumula strikes


def test_inapropiado_escala_strikes():
    store = StoreFalso()
    r1 = moderar("insulto", None, "user:abc",
                 store=store, clasificar_fn=_clasificador_fijo("inapropiado"))
    r2 = moderar("insulto", None, "user:abc",
                 store=store, clasificar_fn=_clasificador_fijo("inapropiado"))
    assert (r1.accion, r2.accion) == ("advertencia", "baneo_60s")
    assert store.strikes == 2


def test_prefiltro_atrapa_sin_llamar_al_llm():
    store = StoreFalso()
    r = moderar("hijo de puta", None, "ip:1.2.3.4",
                store=store, clasificar_fn=_clasificador_prohibido)
    assert r.etiqueta == "inapropiado"
    assert r.origen == "prefiltro"
    assert store.strikes == 1


def test_etiqueta_desconocida_pide_reformular():
    store = StoreFalso()
    r = moderar("???", None, "user:abc",
                store=store, clasificar_fn=lambda m, h: ("rarisima", "llm"))
    assert r.permitido is False
    assert r.respuesta == TEXTO_NO_ENTENDI


def test_store_degradado_no_tumba():
    # Mongo caído: el strike no persiste pero el usuario recibe respuesta.
    store = StoreFalso(disponible=False)
    r = moderar("insulto", None, "user:abc",
                store=store, clasificar_fn=_clasificador_fijo("inapropiado"))
    assert r.permitido is False
    assert r.accion == "advertencia_sin_persistir"
