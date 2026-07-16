"""
Cliente de MongoDB para el historial de chat (Fase 3).

Perezoso y cacheado (mismo patrón que `embedder/embeddings.py:get_embedding_service`):
`get_mongo_db()` devuelve la Database o `None` si Mongo no está disponible — en ese
caso el chat sigue funcionando SIN persistencia (clave para "local hasta patrocinio").
Al patrocinar un servidor solo cambia `MONGO_URI` en el `.env`.
"""
from __future__ import annotations

import logging

from sina.config.app_settings import settings

log = logging.getLogger(__name__)

_db = None
_intentado = False

COL_CONVERSACIONES = "conversaciones"
COL_CHUNKS = "chat_chunks"
COL_FLYER_CIUDADES = "flyer_ciudades"   # ciudades añadidas desde la UI del anotador
COL_REGISTRO_JOBS = "registro_jobs"     # auditoría de corridas del scheduler


def get_mongo_db():
    """Devuelve la Database de Mongo, o None si no se pudo conectar."""
    global _db, _intentado
    if _intentado:
        return _db
    _intentado = True
    try:
        from pymongo import MongoClient, ASCENDING, DESCENDING

        client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=1500)
        client.admin.command("ping")  # verifica conexión de inmediato
        db = client[settings.mongo_db]
        # Índices (idempotentes): listar por usuario y navegar chunks/punteros.
        db[COL_CONVERSACIONES].create_index([("google_sub", ASCENDING), ("actualizado_en", DESCENDING)])
        db[COL_CHUNKS].create_index([("conversacion_id", ASCENDING), ("seq", ASCENDING)])
        # Ciudades de flyers: una por clave normalizada (dedup de "Cd. Obregón"/"cd obregon").
        db[COL_FLYER_CIUDADES].create_index("clave", unique=True)
        # Auditoría de jobs: consultar por job/fecha; TTL de 90 días para que no crezca sin tope.
        db[COL_REGISTRO_JOBS].create_index([("job", ASCENDING), ("inicio", DESCENDING)])
        db[COL_REGISTRO_JOBS].create_index("inicio", expireAfterSeconds=90 * 24 * 3600)
        _db = db
        log.info("MongoDB conectado (%s/%s).", settings.mongo_uri, settings.mongo_db)
    except Exception as e:  # noqa: BLE001 — degradar sin persistencia
        log.warning("MongoDB no disponible (%s); el chat funcionará sin historial.", e)
        _db = None
    return _db


def mongo_disponible() -> bool:
    return get_mongo_db() is not None
