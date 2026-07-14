"""
Endpoints del asistente (Fase 3).

- `POST /api/v1/chat` — responde en **streaming SSE**; funciona anónimo (sin
  persistencia) o con sesión (persiste en Mongo al completar). Si el cliente
  pausa/aborta, no se persiste nada.
- CRUD mínimo de conversaciones (requiere sesión) con paginación por puntero.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from sina.agent.agent import responder_stream
from sina.agent.llm.factory import get_llm_provider
from sina.agent.tools.base import ContextoConsulta
from sina.api.deps import require_csrf, require_csrf_si_sesion, require_session, sesion_actual
from sina.api.ratelimit import limiter
from sina.config.app_settings import settings
from sina.db.chat_store import ChatStore, ConversacionesLlenas

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class UbicacionIn(BaseModel):
    estado: str | None = Field(default=None, max_length=100)
    municipio: str | None = Field(default=None, max_length=100)
    localidad: str | None = Field(default=None, max_length=100)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


# Topes defensivos: acotan el costo en tokens/recursos de una sola petición
# (el historial lo provee el cliente; sin límite permitiría payloads enormes).
_MAX_MENSAJE = 4000
_MAX_HISTORIAL = 50
_MAX_CONTENIDO_HISTORIAL = 8000


class ChatIn(BaseModel):
    mensaje: str = Field(min_length=1, max_length=_MAX_MENSAJE)
    conversacion_id: str | None = None
    historial: list[dict] | None = Field(default=None, max_length=_MAX_HISTORIAL)
    ubicacion: UbicacionIn | None = None

    @field_validator("historial")
    @classmethod
    def _validar_historial(cls, v: list[dict] | None) -> list[dict] | None:
        if v is None:
            return v
        for item in v:
            contenido = item.get("contenido") or item.get("content") or ""
            if isinstance(contenido, str) and len(contenido) > _MAX_CONTENIDO_HISTORIAL:
                raise ValueError(
                    f"El contenido de un mensaje del historial excede {_MAX_CONTENIDO_HISTORIAL} caracteres."
                )
        return v


class TituloIn(BaseModel):
    titulo: str | None = "Nueva conversación"


def _sse(evento: str, dato) -> str:
    return f"event: {evento}\ndata: {json.dumps(dato, ensure_ascii=False, default=str)}\n\n"


def _guard_chat():
    if not settings.enable_chat:
        raise HTTPException(status_code=503, detail="El asistente está deshabilitado.")
    provider = get_llm_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="El asistente no está disponible ahora mismo.")
    return provider


@router.post("")
@limiter.limit("20/minute")
def chat(
    request: Request,
    body: ChatIn,
    sesion: dict | None = Depends(sesion_actual),
    _csrf=Depends(require_csrf_si_sesion),
):
    provider = _guard_chat()
    u = body.ubicacion or UbicacionIn()
    ctx = ContextoConsulta(
        estado=u.estado, municipio=u.municipio, localidad=u.localidad, lat=u.lat, lng=u.lng
    )

    # Resolver conversación (solo con sesión + Mongo disponible).
    store = ChatStore() if sesion is not None else None
    conv_id = body.conversacion_id
    conv_autocreada = False
    if store is not None and store.disponible and not conv_id:
        try:
            conv_id = store.crear_conversacion(sesion["sub"])["id"]
            conv_autocreada = True
        except ConversacionesLlenas:
            conv_id = None  # sin espacio → responde sin persistir

    def stream():
        done = None
        persistido = False
        try:
            for ev in responder_stream(body.mensaje, ctx, body.historial, provider):
                if ev.tipo == "done":
                    done = ev.dato
                    if conv_id:
                        done["conversacion_id"] = conv_id
                yield _sse(ev.tipo, ev.dato)
            # Solo llega aquí si el stream terminó completo (no hubo pausa/abort).
            if done and store is not None and store.disponible and conv_id:
                store.append_mensajes(
                    sesion["sub"], conv_id,
                    [
                        {"rol": "user", "contenido": body.mensaje},
                        {"rol": "assistant", "contenido": done["respuesta"],
                         "metadatos": done.get("metadatos")},
                    ],
                )
                persistido = True
        finally:
            # Si autocreamos la conversación y no se persistió nada (p. ej. pausa),
            # la borramos para no dejar conversaciones vacías ocupando el cupo.
            if conv_autocreada and not persistido and store is not None and conv_id:
                store.borrar_conversacion(sesion["sub"], conv_id)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Conversaciones (requieren sesión) ─────────────────────────────────
@router.get("/conversaciones")
def listar_conversaciones(sesion: dict = Depends(require_session)):
    return {"conversaciones": ChatStore().listar_conversaciones(sesion["sub"])}


@router.post("/conversaciones")
def crear_conversacion(body: TituloIn, sesion: dict = Depends(require_csrf)):
    store = ChatStore()
    if not store.disponible:
        raise HTTPException(status_code=503, detail="El historial no está disponible.")
    try:
        conv = store.crear_conversacion(sesion["sub"], body.titulo or "Nueva conversación")
    except ConversacionesLlenas as e:
        raise HTTPException(status_code=409, detail=str(e))
    return conv


@router.delete("/conversaciones/{conversacion_id}")
def borrar_conversacion(conversacion_id: str, sesion: dict = Depends(require_csrf)):
    ok = ChatStore().borrar_conversacion(sesion["sub"], conversacion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return {"ok": True}


@router.get("/conversaciones/{conversacion_id}/mensajes")
def cargar_mensajes(
    conversacion_id: str,
    chunk: str | None = None,
    sesion: dict = Depends(require_session),
):
    chunk_data = ChatStore().cargar_chunk(sesion["sub"], conversacion_id, chunk)
    if chunk_data is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return chunk_data
