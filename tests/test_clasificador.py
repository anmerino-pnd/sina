"""Clasificador: validación del enum, reintento y fail-open (mock de Ollama)."""
from types import SimpleNamespace

import pytest

from sina.moderacion import clasificador


class ClienteFalso:
    """Simula `ollama.Client.chat`: devuelve respuestas en orden, o lanza."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = 0

    def chat(self, **kwargs):
        self.llamadas += 1
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return SimpleNamespace(message=SimpleNamespace(content=r))


@pytest.fixture
def con_cliente(monkeypatch):
    def _instalar(respuestas):
        cliente = ClienteFalso(respuestas)
        monkeypatch.setattr(clasificador, "_get_client", lambda: cliente)
        return cliente
    return _instalar


def test_etiqueta_valida(con_cliente):
    con_cliente(['{"label": "irrelevante"}'])
    assert clasificador.clasificar("cuéntame un chiste", None) == ("irrelevante", "llm")


def test_json_basura_reintenta_y_fallback(con_cliente):
    cliente = con_cliente(["esto no es json", "tampoco esto"])
    assert clasificador.clasificar("hola", None) == ("relevante", "fallback")
    assert cliente.llamadas == 2  # 1 llamada + 1 reintento


def test_etiqueta_fuera_del_enum_fallback(con_cliente):
    con_cliente(['{"label": "banana"}', '{"label": "spam"}'])
    assert clasificador.clasificar("hola", None) == ("relevante", "fallback")


def test_excepcion_reintenta_y_recupera(con_cliente):
    cliente = con_cliente([TimeoutError("ollama no responde"), '{"label": "relevante"}'])
    assert clasificador.clasificar("precio de la magna", None) == ("relevante", "llm")
    assert cliente.llamadas == 2


def test_excepcion_doble_fallback_sin_propagar(con_cliente):
    con_cliente([ConnectionError("caído"), ConnectionError("caído")])
    # Nunca lanza: fail-open a relevante.
    assert clasificador.clasificar("hola", None) == ("relevante", "fallback")


def test_markdown_envuelto_se_parsea(con_cliente):
    con_cliente(['```json\n{"label": "inapropiado"}\n```'])
    assert clasificador.clasificar("x", None) == ("inapropiado", "llm")


def test_modelo_sin_think_se_recupera(monkeypatch):
    """Si el modelo rechaza `think=False`, se reintenta sin el parámetro."""
    class ClienteSinThink:
        def __init__(self):
            self.con_think = []

        def chat(self, **kwargs):
            self.con_think.append("think" in kwargs)
            if "think" in kwargs:
                raise RuntimeError('"qwen2" does not support thinking')
            return SimpleNamespace(message=SimpleNamespace(content='{"label": "relevante"}'))

    cliente = ClienteSinThink()
    monkeypatch.setattr(clasificador, "_get_client", lambda: cliente)
    monkeypatch.setattr(clasificador, "_pasar_think", True)
    assert clasificador.clasificar("hola", None) == ("relevante", "llm")
    assert cliente.con_think == [True, False]


# ── Preparación de la entrada ────────────────────────────────────────────
def test_turnos_usuario_filtra_y_limita():
    historial = (
        [{"rol": "assistant", "contenido": "hola"}]
        + [{"rol": "user", "contenido": f"msg{i}"} for i in range(8)]
        + [{"role": "user", "content": "en inglés"}]   # acepta ambas claves
    )
    turnos = clasificador._turnos_usuario(historial)
    assert len(turnos) == 5
    assert turnos[-1] == "en inglés"
    assert turnos[0] == "msg4"  # los últimos 5 de 9 turnos user


def test_turnos_usuario_historial_none():
    assert clasificador._turnos_usuario(None) == []
