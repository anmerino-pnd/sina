"""
Sesión de primera parte: cookie firmada (stateless) + CSRF double-submit.

Tras verificar el ID token de Google emitimos NUESTRA propia sesión, firmada con
`SESSION_SECRET` (HMAC vía itsdangerous). La cookie es httpOnly (inmune a robo
por XSS) y lleva un `csrf` que además se expone en una cookie legible por JS; el
cliente lo reenvía en el header X-CSRF-Token en cada request mutante. Como un
atacante cross-site no puede leer nuestras cookies ni fijar ese header, el CSRF
queda bloqueado. Nunca guardamos el token de Google ni contraseñas.
"""
import secrets

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from sina.config.app_settings import SESSION_SECRET, settings

SESSION_COOKIE = "sina_session"
CSRF_COOKIE = "sina_csrf"
CSRF_HEADER = "x-csrf-token"
_SALT = "sina.session.v1"

_serializer = URLSafeTimedSerializer(SESSION_SECRET, salt=_SALT)


def nuevo_csrf() -> str:
    return secrets.token_urlsafe(32)


def firmar_sesion(sub: str, csrf: str) -> str:
    """Serializa y firma el payload de sesión."""
    return _serializer.dumps({"sub": sub, "csrf": csrf})


def leer_sesion(token: str | None) -> dict | None:
    """Verifica firma y expiración (TTL). Devuelve el payload o None."""
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=settings.session_ttl_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict) or "sub" not in data:
        return None
    return data
