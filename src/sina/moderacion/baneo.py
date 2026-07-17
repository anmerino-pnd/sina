"""
Lógica PURA del baneo progresivo: escalamiento, perdón y mensajes.

Sin IO ni acceso a Mongo (eso vive en `ModeracionStore`, `sina/db/stores.py`)
para poder cubrirla con pruebas unitarias de casos límite. Todas las fechas
se manejan en UTC (aware); el store normaliza lo que Mongo devuelva naive.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Sanción por número de intento inapropiado acumulado (tries). El intento 1 es
# solo advertencia (None); a partir del 7º se queda en el tope de 7 días.
SANCIONES: dict[int, timedelta | None] = {
    1: None,
    2: timedelta(minutes=1),
    3: timedelta(minutes=3),
    4: timedelta(minutes=10),
    5: timedelta(hours=1),
    6: timedelta(days=1),
    7: timedelta(days=7),
}
SANCION_TOPE = SANCIONES[7]

# Umbral de "sanción corta" para el perdón: menos de 1 hora.
_UMBRAL_SANCION_CORTA = timedelta(hours=1)
# Tiempo sin incidentes tras el cual aplica el perdón: más de 1 hora.
_VENTANA_PERDON = timedelta(hours=1)


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def calcular_sancion(tries: int) -> timedelta | None:
    """Sanción que corresponde al intento número `tries` (None = solo advertencia)."""
    if tries >= 7:
        return SANCION_TOPE
    return SANCIONES.get(max(tries, 1))


def aplica_perdon(
    ahora: datetime,
    last_inappropriate: datetime | None,
    sancion_previa: timedelta | None,
) -> bool:
    """
    El contador de strikes se reinicia si pasó MÁS de 1 hora desde el último
    incidente Y la sanción previa fue corta (< 1 h) o no hubo (solo advertencia).
    Un baneo largo (≥ 1 h) nunca se perdona por el simple paso del tiempo.
    """
    if last_inappropriate is None:
        return False  # sin historial no hay nada que perdonar
    if ahora - last_inappropriate <= _VENTANA_PERDON:
        return False
    return sancion_previa is None or sancion_previa < _UMBRAL_SANCION_CORTA


def _formatear_duracion(sancion: timedelta) -> str:
    segundos = int(sancion.total_seconds())
    if segundos < 3600:
        minutos = max(segundos // 60, 1)
        return f"{minutos} minuto{'s' if minutos != 1 else ''}"
    if segundos < 86400:
        horas = segundos // 3600
        return f"{horas} hora{'s' if horas != 1 else ''}"
    dias = segundos // 86400
    return f"{dias} día{'s' if dias != 1 else ''}"


def mensaje_sancion(sancion: timedelta | None) -> str:
    """Mensaje al usuario según la sanción aplicada (None = advertencia)."""
    if sancion is None:
        return (
            "Tu mensaje fue marcado como inapropiado. Esta es una advertencia: "
            "si continúas, tu acceso al asistente se suspenderá temporalmente."
        )
    return (
        "Tu mensaje fue marcado como inapropiado. Tu acceso al asistente queda "
        f"suspendido por {_formatear_duracion(sancion)}."
    )


def mensaje_tiempo_restante(banned_until: datetime, ahora: datetime) -> str:
    """Mensaje con el tiempo restante del baneo, en horas y minutos."""
    restante = banned_until - ahora
    total_min = max(int(restante.total_seconds() + 59) // 60, 1)  # redondeo hacia arriba
    horas, minutos = divmod(total_min, 60)
    if horas and minutos:
        detalle = f"{horas} hora{'s' if horas != 1 else ''} y {minutos} minuto{'s' if minutos != 1 else ''}"
    elif horas:
        detalle = f"{horas} hora{'s' if horas != 1 else ''}"
    else:
        detalle = f"{minutos} minuto{'s' if minutos != 1 else ''}"
    return (
        "Tu acceso al asistente está suspendido temporalmente. "
        f"Podrás volver a escribir en {detalle}."
    )
