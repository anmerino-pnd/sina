"""
Refresco en segundo plano (stale-while-revalidate) para las fuentes de gobierno.

Cuando la caché está vencida pero hay datos viejos, el endpoint los devuelve de
inmediato (fuente="cache_vencido", el frontend ya muestra el aviso de vencido) y
el refresco contra la API de gobierno corre en un hilo daemon. Así el usuario
nunca paga la latencia de CRE/CNE en el request path salvo la primera vez que
se consulta una ubicación.
"""
import logging
import threading
from typing import Callable

log = logging.getLogger(__name__)

_en_curso: set[str] = set()
_lock = threading.Lock()


def refrescar_en_background(clave: str, fn: Callable[[], None]) -> bool:
    """
    Ejecuta `fn` en un hilo daemon si no hay ya un refresco en curso para
    `clave` (dedupe por instancia). Devuelve True si se lanzó el refresco.
    """
    with _lock:
        if clave in _en_curso:
            return False
        _en_curso.add(clave)

    def _worker():
        try:
            fn()
            log.info("Refresco en background completado: %s", clave)
        except Exception:
            log.exception("Error refrescando %s en background", clave)
        finally:
            with _lock:
                _en_curso.discard(clave)

    threading.Thread(target=_worker, name=f"refresco-{clave}", daemon=True).start()
    return True
