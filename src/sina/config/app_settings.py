"""
Configuración tipada de la aplicación (auth, sesión, seguridad).

Se separa de `credentials.py` (que sigue exponiendo DB_URL, HEADERS y las URLs
de scraping) para introducir validación fail-fast con pydantic-settings sin
tocar el resto del arranque. En GCP estos valores llegan por Secret Manager →
variables de entorno.
"""
import logging
import secrets

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Entorno: "dev" | "prod". Controla flags de seguridad de cookies.
    environment: str = Field(default="dev", alias="SINA_ENV")

    # OAuth de Google. El client_id es PÚBLICO (se sirve al frontend y es el
    # `aud` que verificamos). Vacío → login deshabilitado (feature flag).
    google_oauth_client_id: str = Field(default="", alias="GOOGLE_OAUTH_CLIENT_ID")

    # Clave de firma de la sesión (HMAC). Obligatoria en prod, alta entropía.
    secret_key: str = Field(default="", alias="SECRET_KEY")

    # Vida de la sesión firmada (segundos). Por defecto 14 días.
    session_ttl_seconds: int = Field(default=60 * 60 * 24 * 14, alias="SESSION_TTL")

    # Orígenes permitidos por CORS (coma-separados). Vacío → mismo origen.
    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_prod(self) -> bool:
        return self.environment.lower() in {"prod", "production"}

    @property
    def cookie_secure(self) -> bool:
        # En dev sobre http://localhost, las cookies Secure no viajarían.
        return self.is_prod

    def resolved_secret_key(self) -> str:
        """
        Devuelve la clave de firma. Si falta:
        - en prod: error (no arrancar sin secreto).
        - en dev: genera una efímera (las sesiones no sobreviven reinicios).
        """
        if self.secret_key:
            return self.secret_key
        if self.is_prod:
            raise RuntimeError(
                "SECRET_KEY es obligatoria en producción para firmar sesiones."
            )
        log.warning(
            "SECRET_KEY no configurada; usando una clave efímera de desarrollo. "
            "Las sesiones se invalidarán al reiniciar el servidor."
        )
        return secrets.token_urlsafe(48)


settings = AppSettings()
# Se resuelve una vez al importar para fijar la clave de firma del proceso.
SESSION_SECRET: str = settings.resolved_secret_key()
