"""
Almacén de conversaciones de chat en MongoDB (patrón bucket / lista ligada).

Buenas prácticas a escala (estilo WhatsApp/Messenger):
- **Bucket pattern**: cada documento `chat_chunks` guarda hasta `CHAT_CHUNK_SIZE`
  mensajes → evita documentos ilimitados (límite de 16 MB) y mantiene el working
  set chico. Solo el chunk CABEZA se muta (`$push`); los llenos quedan inmutables.
- **Lista ligada por punteros**: la conversación apunta a su chunk más reciente
  (`cabeza_chunk_id`); cada chunk apunta al anterior (`anterior_id`). Paginar hacia
  atrás = seguir el puntero (O(1) por página, sin `skip/offset`).
- **Denormalización**: `ultimo_preview`/`num_mensajes` para pintar la lista de chats
  sin leer mensajes.

Todos los ids de puntero son `str(ObjectId)` para viajar en JSON sin fricción.
"""
from __future__ import annotations

import logging
from typing import Any

from sina.config.app_settings import settings
from sina.config.timezone import get_mexico_now
from sina.db.mongo import COL_CHUNKS, COL_CONVERSACIONES, get_mongo_db

log = logging.getLogger(__name__)


class ConversacionesLlenas(Exception):
    """Se alcanzó el tope de conversaciones por usuario."""


class ChatStore:
    def __init__(self) -> None:
        self.db = get_mongo_db()

    @property
    def disponible(self) -> bool:
        return self.db is not None

    # ── Conversaciones ────────────────────────────────────────────────
    def listar_conversaciones(self, google_sub: str) -> list[dict[str, Any]]:
        if not self.disponible:
            return []
        cur = (
            self.db[COL_CONVERSACIONES]
            .find({"google_sub": google_sub})
            .sort("actualizado_en", -1)
        )
        return [self._conv_publica(c) for c in cur]

    def crear_conversacion(self, google_sub: str, titulo: str = "Nueva conversación") -> dict[str, Any]:
        if not self.disponible:
            raise RuntimeError("Mongo no disponible")
        n = self.db[COL_CONVERSACIONES].count_documents({"google_sub": google_sub})
        if n >= settings.chat_max_conversaciones:
            raise ConversacionesLlenas(
                f"Máximo {settings.chat_max_conversaciones} conversaciones. Elimina una para crear otra."
            )
        ahora = get_mexico_now()
        doc = {
            "google_sub": google_sub,
            "titulo": titulo,
            "cabeza_chunk_id": None,
            "num_mensajes": 0,
            "ultimo_preview": "",
            "creado_en": ahora,
            "actualizado_en": ahora,
        }
        res = self.db[COL_CONVERSACIONES].insert_one(doc)
        doc["_id"] = res.inserted_id
        return self._conv_publica(doc)

    def borrar_conversacion(self, google_sub: str, conversacion_id: str) -> bool:
        if not self.disponible:
            return False
        oid = self._oid(conversacion_id)
        if oid is None:
            return False
        r = self.db[COL_CONVERSACIONES].delete_one({"_id": oid, "google_sub": google_sub})
        if r.deleted_count:
            self.db[COL_CHUNKS].delete_many({"conversacion_id": oid})
            return True
        return False

    def _obtener_conversacion(self, google_sub: str, conversacion_id: str) -> dict | None:
        oid = self._oid(conversacion_id)
        if oid is None:
            return None
        return self.db[COL_CONVERSACIONES].find_one({"_id": oid, "google_sub": google_sub})

    # ── Mensajes (bucket + puntero) ───────────────────────────────────
    def append_mensajes(
        self,
        google_sub: str,
        conversacion_id: str,
        mensajes: list[dict[str, Any]],
    ) -> None:
        """Agrega uno o más mensajes al chunk cabeza, creando chunks nuevos al llenar."""
        if not self.disponible or not mensajes:
            return
        conv = self._obtener_conversacion(google_sub, conversacion_id)
        if conv is None:
            return
        ahora = get_mexico_now()
        tam = settings.chat_chunk_size

        for m in mensajes:
            m = {**m, "ts": m.get("ts") or ahora}
            cabeza = None
            if conv.get("cabeza_chunk_id") is not None:
                cabeza = self.db[COL_CHUNKS].find_one({"_id": conv["cabeza_chunk_id"]})

            if cabeza is not None and len(cabeza.get("mensajes", [])) < tam:
                self.db[COL_CHUNKS].update_one(
                    {"_id": cabeza["_id"]}, {"$push": {"mensajes": m}}
                )
            else:
                nuevo = {
                    "conversacion_id": conv["_id"],
                    "google_sub": google_sub,
                    "mensajes": [m],
                    "anterior_id": conv.get("cabeza_chunk_id"),
                    "seq": (cabeza["seq"] + 1) if cabeza else 0,
                    "creado_en": ahora,
                }
                res = self.db[COL_CHUNKS].insert_one(nuevo)
                conv["cabeza_chunk_id"] = res.inserted_id

        preview = (mensajes[-1].get("contenido") or "")[:120]
        self.db[COL_CONVERSACIONES].update_one(
            {"_id": conv["_id"]},
            {
                "$set": {
                    "cabeza_chunk_id": conv["cabeza_chunk_id"],
                    "ultimo_preview": preview,
                    "actualizado_en": ahora,
                },
                "$inc": {"num_mensajes": len(mensajes)},
            },
        )

    def cargar_chunk(
        self,
        google_sub: str,
        conversacion_id: str,
        chunk_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Devuelve un chunk (cabeza si `chunk_id` es None) con sus mensajes y el
        puntero `anterior_id` para seguir paginando hacia atrás.
        """
        if not self.disponible:
            return None
        conv = self._obtener_conversacion(google_sub, conversacion_id)
        if conv is None:
            return None
        oid = self._oid(chunk_id) if chunk_id else conv.get("cabeza_chunk_id")
        if oid is None:
            return {"mensajes": [], "anterior_id": None, "chunk_id": None}
        chunk = self.db[COL_CHUNKS].find_one({"_id": oid, "conversacion_id": conv["_id"]})
        if chunk is None:
            return None
        return {
            "chunk_id": str(chunk["_id"]),
            "anterior_id": str(chunk["anterior_id"]) if chunk.get("anterior_id") else None,
            "mensajes": [self._msg_publico(m) for m in chunk.get("mensajes", [])],
        }

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _oid(valor: str | None):
        from bson import ObjectId
        from bson.errors import InvalidId
        try:
            return ObjectId(valor)
        except (InvalidId, TypeError):
            return None

    @staticmethod
    def _conv_publica(c: dict) -> dict[str, Any]:
        return {
            "id": str(c["_id"]),
            "titulo": c.get("titulo"),
            "num_mensajes": c.get("num_mensajes", 0),
            "ultimo_preview": c.get("ultimo_preview", ""),
            "actualizado_en": c.get("actualizado_en"),
        }

    @staticmethod
    def _msg_publico(m: dict) -> dict[str, Any]:
        return {
            "rol": m.get("rol"),
            "contenido": m.get("contenido"),
            "metadatos": m.get("metadatos"),
            "ts": m.get("ts"),
        }
