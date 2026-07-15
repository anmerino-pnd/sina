"""
Configuración tipada de la aplicación (auth, sesión, seguridad).

Se separa de `credentials.py` (que sigue exponiendo DB_URL, HEADERS y las URLs
de scraping) para introducir validación fail-fast con pydantic-settings sin
tocar el resto del arranque. En GCP estos valores llegan por Secret Manager →
variables de entorno.
"""
import logging
import os
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

    # ── Chat / Agente (Fase 3) ────────────────────────────────────────────
    # Feature flag del asistente. Off → POST /api/v1/chat responde 503.
    enable_chat: bool = Field(default=False, alias="ENABLE_CHAT")
    # Proveedor de LLM: "ollama" (local) hoy; "gemini" (GCP) futuro.
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")
    # Ollama: host local por defecto; el modelo debe soportar tool-calling.
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_model: str = Field(default="qwen2.5:7b", alias="OLLAMA_MODEL")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    # Tope de iteraciones del grafo (rondas de tool-calling) por respuesta.
    llm_max_iters: int = Field(default=6, alias="LLM_MAX_ITERS")

    # ── Extracción de flyers por VLM (Fase 6) ─────────────────────────────
    # Feature flag del extractor de volantes. Off → POST /annotator/extract 503.
    enable_vlm: bool = Field(default=False, alias="ENABLE_VLM")
    # Proveedor de VLM: "ollama" (local) hoy; "gemini" (GCP) futuro.
    vlm_provider: str = Field(default="ollama", alias="VLM_PROVIDER")
    # Modelo de visión LOCAL por defecto; adaptable a nube con OLLAMA_API_KEY.
    vlm_model: str = Field(default="qwen2.5vl:7b", alias="VLM_MODEL")
    vlm_host: str = Field(default="http://localhost:11434", alias="VLM_HOST")

    # ── Historial de chat en MongoDB (Fase 3) ─────────────────────────────
    # Local por ahora; al patrocinar un servidor solo cambia la URI.
    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db: str = Field(default="sina", alias="MONGO_DB")
    # Conversaciones por usuario (tope) y tamaño del "chunk" (bucket pattern).
    chat_max_conversaciones: int = Field(default=5, alias="CHAT_MAX_CONVERSACIONES")
    chat_chunk_size: int = Field(default=15, alias="CHAT_CHUNK_SIZE")

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

# ── Guardas de credenciales por defecto ──────────────────────────────────
# Los valores de ejemplo de `.env.example`/`compose.yaml` son públicos (están
# en el repo); no deben llegar a producción.
_DEFAULT_DB_PASSWORDS = {"sina_password"}

if settings.is_prod:
    if os.getenv("DB_PASSWORD") in _DEFAULT_DB_PASSWORDS:
        raise RuntimeError(
            "DB_PASSWORD usa el valor de ejemplo del repositorio; "
            "cambia la contraseña antes de arrancar en producción."
        )
    if settings.mongo_uri.startswith("mongodb://localhost") or "@" not in settings.mongo_uri:
        log.warning(
            "MONGO_URI apunta a una instancia sin autenticación; "
            "en producción configura credenciales de MongoDB."
        )
