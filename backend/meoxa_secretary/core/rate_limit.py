"""Rate limiter slowapi — storage Redis pour que tous les workers partagent l'état."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from meoxa_secretary.config import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_settings.redis_url,
    default_limits=["200/minute"],
    strategy="fixed-window",
)
