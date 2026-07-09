"""
Rate limiting con slowapi (por IP). Límite base generoso para lecturas públicas
(los GET de precios ya van cacheados) y estricto en auth para frenar
enumeración/credential-stuffing. Para límites GLOBALES al escalar
horizontalmente, respaldar con Redis (storage_uri) — en memoria es por-instancia.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["240/minute"],
    headers_enabled=True,
)
