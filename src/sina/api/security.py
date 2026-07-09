"""Middleware de cabeceras de seguridad + gate para endpoints administrativos."""
import os

from fastapi import Header, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from sina.config.app_settings import settings

# CSP: self + Google Identity Services (login) + tiles de mapas (dashboards).
# 'unsafe-inline' en style-src es necesario por estilos inline de GIS/Leaflet.
_CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' https://accounts.google.com https://apis.google.com",
    "style-src 'self' 'unsafe-inline' https://accounts.google.com",
    "frame-src https://accounts.google.com",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https://accounts.google.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
])


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(self), microphone=(), camera=()"
        )
        response.headers.setdefault("Content-Security-Policy", _CSP)
        if settings.is_prod:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )
        return response


def require_admin(x_admin_key: str = Header(default="")) -> None:
    """
    Gate para endpoints que disparan scraping/escrituras (antes públicos).
    Compara contra ADMIN_API_KEY (Secret Manager en prod). Sin clave configurada
    → 503 (cerrado por defecto, nunca abierto).
    """
    import hmac

    esperado = os.getenv("ADMIN_API_KEY", "")
    if not esperado:
        raise HTTPException(status_code=503, detail="Operación no disponible.")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, esperado):
        raise HTTPException(status_code=403, detail="No autorizado.")
