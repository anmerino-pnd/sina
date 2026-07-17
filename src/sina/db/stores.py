"""
Stores chicos sobre MongoDB (mismo patrón degradable que ChatStore):
si Mongo no está disponible, cada método falla suave (lista vacía / no-op)
y la app sigue funcionando con lo que tenga en disco.

Qué vive aquí y por qué (ver "Mapa de almacenamiento" en quarto/3_datos.qmd):
- `flyer_ciudades`: las ciudades que el usuario añade desde la UI del anotador
  ("Añadir otra…"). El JSON versionado (`config/flyer_ciudades.json`) queda como
  SEMILLA de solo lectura; las añadidas en runtime van a Mongo — antes se usaban
  al vuelo y se perdían al recargar.
- `registro_jobs`: auditoría de corridas del scheduler (qué job corrió, cuándo,
  cuánto tardó, qué hizo). Antes solo existía en logs; con TTL de 90 días.
- `moderacion_usuarios` / `moderacion_log`: estado del baneo progresivo por
  identidad (TTL 30 días desde el último incidente) y auditoría de cada
  decisión de moderación (TTL 90 días). Ver `sina/moderacion/`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sina.config.timezone import get_mexico_now
from sina.db.mongo import (
    COL_FLYER_CIUDADES,
    COL_MODERACION_LOG,
    COL_MODERACION_USUARIOS,
    COL_REGISTRO_JOBS,
    get_mongo_db,
)
from sina.moderacion.baneo import (
    ahora_utc,
    calcular_sancion,
    mensaje_sancion,
    mensaje_tiempo_restante,
)

log = logging.getLogger(__name__)


def _normalizar_ciudad(nombre: str) -> str:
    """Clave de dedup: misma normalización que usan los spiders para la carpeta."""
    return (
        nombre.strip().lower()
        .replace(" ", "_")
        .replace("á", "a").replace("é", "e")
        .replace("í", "i").replace("ó", "o").replace("ú", "u")
    )


class FlyerCiudadesStore:
    def __init__(self) -> None:
        self.db = get_mongo_db()

    @property
    def disponible(self) -> bool:
        return self.db is not None

    def listar(self) -> list[str]:
        """Nombres tal cual los escribió el usuario, orden alfabético."""
        if not self.disponible:
            return []
        cur = self.db[COL_FLYER_CIUDADES].find({}, {"nombre": 1}).sort("nombre", 1)
        return [d["nombre"] for d in cur if d.get("nombre")]

    def agregar(self, nombre: str) -> bool:
        """Guarda una ciudad nueva (idempotente por clave normalizada)."""
        nombre = (nombre or "").strip()
        if not self.disponible or not nombre:
            return False
        try:
            self.db[COL_FLYER_CIUDADES].update_one(
                {"clave": _normalizar_ciudad(nombre)},
                {"$setOnInsert": {"nombre": nombre, "creado_en": get_mexico_now()}},
                upsert=True,
            )
            return True
        except Exception:  # noqa: BLE001 — degradar, la descarga ya ocurrió
            log.exception("No se pudo guardar la ciudad de flyer en Mongo")
            return False


def ciudades_flyers(semilla: list[str]) -> list[str]:
    """
    Lista para el selector del anotador: la SEMILLA del JSON (en su orden) más
    las ciudades añadidas en runtime (Mongo), sin duplicados por clave normalizada.
    Con Mongo caído devuelve solo la semilla (comportamiento previo).
    """
    vistas = {_normalizar_ciudad(c) for c in semilla}
    extras = [
        c for c in FlyerCiudadesStore().listar()
        if _normalizar_ciudad(c) not in vistas
    ]
    return list(semilla) + extras


class RegistroJobsStore:
    def __init__(self) -> None:
        self.db = get_mongo_db()

    @property
    def disponible(self) -> bool:
        return self.db is not None

    def registrar(
        self, job: str, inicio, fin, ok: bool, detalles: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        if not self.disponible:
            return
        try:
            self.db[COL_REGISTRO_JOBS].insert_one({
                "job": job,
                "inicio": inicio,
                "fin": fin,
                "duracion_s": round((fin - inicio).total_seconds(), 2),
                "ok": ok,
                "detalles": detalles or {},
                "error": error,
            })
        except Exception:  # noqa: BLE001 — la auditoría nunca tumba al job
            log.exception("No se pudo registrar la corrida del job %s", job)

    def ultimos(self, job: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
        if not self.disponible:
            return []
        filtro = {"job": job} if job else {}
        cur = self.db[COL_REGISTRO_JOBS].find(filtro).sort("inicio", -1).limit(limit)
        corridas = []
        for d in cur:
            d["_id"] = str(d["_id"])
            for k in ("inicio", "fin"):
                if d.get(k) is not None:
                    d[k] = d[k].isoformat()
            corridas.append(d)
        return corridas


def _como_utc(dt: datetime) -> datetime:
    """pymongo devuelve datetimes naive (UTC); los normaliza a aware."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


class ModeracionStore:
    """
    Estado del baneo progresivo por identidad (`user:<sub>` o `ip:<ip>`) +
    auditoría de decisiones. La lógica de escalamiento/perdón vive en
    `sina/moderacion/baneo.py` (pura); aquí solo la persistencia.

    Con Mongo caído degrada suave: `revisar_baneo` deja pasar y
    `registrar_inapropiado` devuelve solo la advertencia sin persistir.
    """

    def __init__(self) -> None:
        self.db = get_mongo_db()

    @property
    def disponible(self) -> bool:
        return self.db is not None

    def revisar_baneo(self, identidad: str) -> str | None:
        """Mensaje de tiempo restante si sigue baneado; None si puede pasar."""
        if not self.disponible:
            return None
        try:
            doc = self.db[COL_MODERACION_USUARIOS].find_one({"identidad": identidad})
            if not doc or not doc.get("banned_until"):
                return None
            ahora = ahora_utc()
            banned_until = _como_utc(doc["banned_until"])
            if banned_until > ahora:
                return mensaje_tiempo_restante(banned_until, ahora)
            # Baneo expirado: limpiar y dejar pasar.
            self.db[COL_MODERACION_USUARIOS].update_one(
                {"identidad": identidad}, {"$unset": {"banned_until": ""}}
            )
            return None
        except Exception:  # noqa: BLE001 — la moderación nunca tumba el chat
            log.exception("No se pudo revisar el baneo de %s", identidad)
            return None

    def registrar_inapropiado(self, identidad: str) -> tuple[str, str]:
        """
        Aplica perdón + strike + escalamiento. Devuelve `(mensaje, accion)` con
        accion "advertencia" | "baneo_<segundos>s" | "advertencia_sin_persistir".

        El paso crítico (strike) es un `$inc` atómico: dos mensajes inapropiados
        concurrentes del mismo usuario cuentan 2, no 1 (defecto del original).
        """
        ahora = ahora_utc()
        if not self.disponible:
            log.warning("Mongo no disponible; strike de %s no se persiste.", identidad)
            return mensaje_sancion(None), "advertencia_sin_persistir"
        try:
            col = self.db[COL_MODERACION_USUARIOS]
            # 1. Perdón (espejo en Mongo de `baneo.aplica_perdon`): reinicia el
            #    contador si pasó MÁS de 1 h del último incidente Y la sanción
            #    previa fue corta (< 1 h) o no hubo. Update condicional atómico.
            col.update_one(
                {
                    "identidad": identidad,
                    "last_inappropriate": {"$lt": ahora - timedelta(hours=1)},
                    "$or": [
                        {"sancion_previa_s": {"$exists": False}},
                        {"sancion_previa_s": None},
                        {"sancion_previa_s": {"$lt": 3600}},
                    ],
                },
                {"$set": {"inappropriate_tries": 0}},
            )
            # 2. Strike atómico.
            from pymongo import ReturnDocument

            doc = col.find_one_and_update(
                {"identidad": identidad},
                {
                    "$inc": {"inappropriate_tries": 1},
                    "$set": {"last_inappropriate": ahora, "actualizado_en": ahora},
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            tries = int(doc["inappropriate_tries"])
            # 3. Escalamiento (carrera residual benigna: last-writer-wins entre
            #    dos sanciones casi simultáneas del mismo usuario).
            sancion = calcular_sancion(tries)
            if sancion is None:
                col.update_one(
                    {"identidad": identidad}, {"$set": {"sancion_previa_s": None}}
                )
                return mensaje_sancion(None), "advertencia"
            col.update_one(
                {"identidad": identidad},
                {"$set": {
                    "banned_until": ahora + sancion,
                    "sancion_previa_s": sancion.total_seconds(),
                }},
            )
            return mensaje_sancion(sancion), f"baneo_{int(sancion.total_seconds())}s"
        except Exception:  # noqa: BLE001
            log.exception("No se pudo registrar el strike de %s", identidad)
            return mensaje_sancion(None), "advertencia_sin_persistir"

    def auditar(
        self,
        identidad: str,
        mensaje: str,
        etiqueta: str,
        origen: str,
        accion: str,
        duracion_ms: float | None = None,
    ) -> None:
        """Log de auditoría de CADA decisión (para revisar falsos positivos)."""
        if not self.disponible:
            return
        try:
            self.db[COL_MODERACION_LOG].insert_one({
                "identidad": identidad,
                "mensaje": mensaje[:500],
                "etiqueta": etiqueta,
                "origen": origen,
                "accion": accion,
                "duracion_ms": round(duracion_ms, 1) if duracion_ms is not None else None,
                "creado_en": ahora_utc(),
            })
        except Exception:  # noqa: BLE001 — la auditoría nunca tumba el chat
            log.exception("No se pudo auditar la decisión de moderación")
