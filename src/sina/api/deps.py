"""Dependencias compartidas de FastAPI: sesión, usuario actual y CSRF."""
from fastapi import Depends, HTTPException, Request

from sina.api.session import CSRF_HEADER, SESSION_COOKIE, leer_sesion
from sina.db.repository import UsuarioRepository


def sesion_actual(request: Request) -> dict | None:
    """Payload de sesión verificado, o None si es anónimo."""
    return leer_sesion(request.cookies.get(SESSION_COOKIE))


def require_session(sesion: dict | None = Depends(sesion_actual)) -> dict:
    """Exige sesión válida. Solo para rutas que tocan datos del usuario."""
    if sesion is None:
        raise HTTPException(status_code=401, detail="Sesión requerida.")
    return sesion


def require_csrf(
    request: Request, sesion: dict = Depends(require_session)
) -> dict:
    """
    Double-submit: el header X-CSRF-Token debe coincidir con el `csrf` ligado
    a la sesión firmada. Se aplica a rutas mutantes (POST/PATCH/DELETE).
    """
    enviado = request.headers.get(CSRF_HEADER)
    esperado = sesion.get("csrf")
    if not enviado or not esperado or not secrets_equal(enviado, esperado):
        raise HTTPException(status_code=403, detail="Token CSRF inválido.")
    return sesion


def usuario_actual(sesion: dict = Depends(require_session)) -> dict:
    """Carga el usuario de la sesión desde la DB (401 si ya no existe)."""
    u = UsuarioRepository().obtener_por_sub(sesion["sub"])
    if u is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")
    return u


def secrets_equal(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a, b)
