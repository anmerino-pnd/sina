"""
Configuración de logging unificada para SINA (Fase 1).

Envía los logs tanto a consola como a un archivo rotativo en `logs/sina.log`.
Como todos los módulos usan `logging.getLogger(__name__)`, basta con configurar
el logger raíz una sola vez al arrancar la app.
"""
import logging
from logging.handlers import RotatingFileHandler

from sina.config.paths import LOGS

_configurado = False


def configurar_logging(level: int = logging.INFO) -> None:
    """Configura el logger raíz (consola + archivo rotativo). Idempotente."""
    global _configurado
    if _configurado:
        return

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    archivo = RotatingFileHandler(
        LOGS / "sina.log",
        maxBytes=5_000_000,   # ~5 MB por archivo
        backupCount=3,
        encoding="utf-8",
    )
    archivo.setFormatter(formato)

    root = logging.getLogger()
    root.setLevel(level)
    # Reemplazamos handlers previos para no duplicar líneas.
    root.handlers.clear()
    root.addHandler(consola)
    root.addHandler(archivo)

    _configurado = True
