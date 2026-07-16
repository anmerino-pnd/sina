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
"""
from __future__ import annotations

import logging
from typing import Any

from sina.config.timezone import get_mexico_now
from sina.db.mongo import COL_FLYER_CIUDADES, COL_REGISTRO_JOBS, get_mongo_db

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
