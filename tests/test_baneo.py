"""Casos límite de la lógica pura del baneo progresivo (sina/moderacion/baneo.py)."""
from datetime import datetime, timedelta, timezone

import pytest

from sina.moderacion.baneo import (
    aplica_perdon,
    calcular_sancion,
    mensaje_sancion,
    mensaje_tiempo_restante,
)

AHORA = datetime(2026, 7, 17, 12, 0, 0, tzinfo=timezone.utc)


# ── Tabla de escalamiento ────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("tries", "esperada"),
    [
        (1, None),                     # solo advertencia
        (2, timedelta(minutes=1)),
        (3, timedelta(minutes=3)),
        (4, timedelta(minutes=10)),
        (5, timedelta(hours=1)),
        (6, timedelta(days=1)),
        (7, timedelta(days=7)),
        (8, timedelta(days=7)),        # tope
        (100, timedelta(days=7)),      # tope
        (0, None),                     # defensivo: se trata como 1
        (-3, None),                    # defensivo: se trata como 1
    ],
)
def test_calcular_sancion(tries, esperada):
    assert calcular_sancion(tries) == esperada


# ── Perdón ───────────────────────────────────────────────────────────────
def test_perdon_sin_historial_no_aplica():
    assert aplica_perdon(AHORA, None, None) is False


def test_perdon_justo_en_1h_no_aplica():
    # La espec exige MÁS de 1 hora: exactamente 1 h no perdona.
    assert aplica_perdon(AHORA, AHORA - timedelta(hours=1), None) is False


def test_perdon_1h_y_1s_sin_baneo_previo_aplica():
    assert aplica_perdon(AHORA, AHORA - timedelta(hours=1, seconds=1), None) is True


def test_perdon_con_sancion_corta_aplica():
    ultimo = AHORA - timedelta(hours=2)
    assert aplica_perdon(AHORA, ultimo, timedelta(minutes=59)) is True


def test_perdon_con_sancion_de_1h_no_aplica():
    # Sanción previa >= 1 h nunca se perdona por el paso del tiempo.
    ultimo = AHORA - timedelta(days=3)
    assert aplica_perdon(AHORA, ultimo, timedelta(hours=1)) is False


def test_perdon_con_sancion_larga_no_aplica():
    ultimo = AHORA - timedelta(days=30)
    assert aplica_perdon(AHORA, ultimo, timedelta(days=7)) is False


def test_reincidencia_inmediata_no_aplica():
    assert aplica_perdon(AHORA, AHORA - timedelta(minutes=5), timedelta(minutes=1)) is False


# ── Mensajes ─────────────────────────────────────────────────────────────
def test_mensaje_advertencia():
    assert "advertencia" in mensaje_sancion(None)


@pytest.mark.parametrize(
    ("sancion", "texto"),
    [
        (timedelta(minutes=1), "1 minuto"),
        (timedelta(minutes=3), "3 minutos"),
        (timedelta(minutes=10), "10 minutos"),
        (timedelta(hours=1), "1 hora"),
        (timedelta(days=1), "1 día"),
        (timedelta(days=7), "7 días"),
    ],
)
def test_mensaje_sancion_duraciones(sancion, texto):
    assert texto in mensaje_sancion(sancion)


def test_tiempo_restante_solo_minutos_redondea_arriba():
    # 90 s restantes → "2 minutos" (nunca reporta de menos ni "0 minutos").
    assert "2 minutos" in mensaje_tiempo_restante(AHORA + timedelta(seconds=90), AHORA)


def test_tiempo_restante_minimo_1_minuto():
    assert "1 minuto" in mensaje_tiempo_restante(AHORA + timedelta(seconds=10), AHORA)


def test_tiempo_restante_horas_y_minutos():
    restante = mensaje_tiempo_restante(AHORA + timedelta(hours=1, minutes=30), AHORA)
    assert "1 hora y 30 minutos" in restante


def test_tiempo_restante_horas_exactas():
    assert "2 horas" in mensaje_tiempo_restante(AHORA + timedelta(hours=2), AHORA)
