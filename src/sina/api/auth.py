"""Router de autenticación con Google (Fase 4)."""
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from google.auth.transport import requests as g_requests
from google.oauth2 import id_token
from pydantic import BaseModel

from sina.api.ratelimit import limiter
from sina.api.session import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    firmar_sesion,
    nuevo_csrf,
)
from sina.config.app_settings import settings
from sina.db.repository import UsuarioRepository

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_google_request = g_requests.Request()


class GoogleAuthIn(BaseModel):
    credential: str


def _set_session_cookies(response: Response, sub: str) -> None:
    csrf = nuevo_csrf()
    token = firmar_sesion(sub, csrf)
    max_age = settings.session_ttl_seconds
    # Sesión: httpOnly (no accesible por JS). CSRF: legible por JS (double-submit).
    response.set_cookie(
        SESSION_COOKIE, token, max_age=max_age, path="/",
        httponly=True, secure=settings.cookie_secure, samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE, csrf, max_age=max_age, path="/",
        httponly=False, secure=settings.cookie_secure, samesite="lax",
    )


def _clear_session_cookies(response: Response) -> None:
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/")


@router.post("/google")
@limiter.limit("10/minute")
def auth_google(request: Request, body: GoogleAuthIn, response: Response) -> dict:
    """
    Verifica el ID token de Google Identity Services y abre sesión.
    Ruta síncrona (def) a propósito: hace I/O de DB bloqueante → threadpool.
    """
    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=503, detail="Login no disponible.")

    try:
        info = id_token.verify_oauth2_token(
            body.credential, _google_request, settings.google_oauth_client_id
        )
    except ValueError:
        # Firma inválida, aud/exp incorrectos, token manipulado, etc.
        raise HTTPException(status_code=401, detail="Token de Google inválido.")

    if info.get("iss") not in _ISSUERS:
        raise HTTPException(status_code=401, detail="Emisor no confiable.")

    sub = info.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token sin identidad.")

    email_verified = bool(info.get("email_verified"))
    email = info.get("email") if email_verified else None

    # `sub` (inmutable) es el user_id; NUNCA se usa el email como clave.
    usuario = UsuarioRepository().upsert_login(
        google_sub=sub,
        email=email,
        email_verified=email_verified,
        nombre=info.get("name"),
        foto_url=info.get("picture"),
    )
    _set_session_cookies(response, sub)
    return usuario


@router.post("/logout")
def logout(response: Response) -> dict:
    _clear_session_cookies(response)
    return {"status": "ok"}
