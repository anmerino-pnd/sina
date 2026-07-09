"""Router de usuario y config pública del cliente (Fase 4)."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sina.api.deps import require_csrf, usuario_actual
from sina.config.app_settings import settings
from sina.db.repository import UsuarioRepository

router = APIRouter(prefix="/api/v1", tags=["usuarios"])

_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")
_RESERVADOS = {
    "admin", "administrador", "sina", "soporte", "api", "me", "null", "root",
    "www", "chat", "gasolina", "gas-lp", "gaslp", "supermercados", "auth",
    "config", "health",
}


class UsernameIn(BaseModel):
    username: str


@router.get("/config")
def client_config() -> dict:
    """Config pública para el frontend. El client_id de Google es público."""
    return {"google_client_id": settings.google_oauth_client_id}


@router.get("/me")
def get_me(usuario: dict = Depends(usuario_actual)) -> dict:
    return usuario


@router.patch("/me")
def set_username(
    body: UsernameIn,
    usuario: dict = Depends(usuario_actual),
    _csrf: dict = Depends(require_csrf),
) -> dict:
    username = body.username.strip().lower()

    if not _USERNAME_RE.match(username):
        raise HTTPException(status_code=422, detail="Formato de usuario no válido.")
    if "__" in username or username.startswith("_") or username.endswith("_"):
        raise HTTPException(status_code=422, detail="Formato de usuario no válido.")
    if username in _RESERVADOS:
        raise HTTPException(status_code=409, detail="Nombre de usuario no disponible.")

    repo = UsuarioRepository()
    if repo.username_en_uso(username, excepto_sub=usuario["user_id"]):
        raise HTTPException(status_code=409, detail="Nombre de usuario en uso.")

    actualizado = repo.fijar_username(usuario["user_id"], username)
    if actualizado is None:
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")
    return actualizado
