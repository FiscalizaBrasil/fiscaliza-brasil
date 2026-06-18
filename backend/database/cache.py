"""
Decorator de cache com TTL (time-to-live) para endpoints FastAPI.

Combina:
- Cache em memória com expiração automática (TTL)
- Headers HTTP Cache-Control para controle do navegador
- Suporte a invalidação via query parameter `_t` (timestamp)
"""

import time
import threading
import logging
from functools import wraps
from typing import Optional, Callable, Any

_log = logging.getLogger(__name__)


class TTLCache:
    """
    Cache thread-safe com TTL (time-to-live) em segundos.
    """

    def __init__(self, maxsize: int = 128, ttl: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: dict = {}
        self._lock = threading.Lock()

    def get(self, key: tuple) -> Optional[Any]:
        """Retorna o valor do cache se ainda estiver válido."""
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    return result
                # Expirado, remove
                del self._cache[key]
        return None

    def set(self, key: tuple, value: Any):
        """Armazena valor no cache."""
        with self._lock:
            # Se atingiu o limite, remove o mais antigo
            if len(self._cache) >= self.maxsize:
                oldest_key = min(self._cache.keys(),
                                 key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (value, time.time())

    def clear(self):
        """Limpa todo o cache."""
        with self._lock:
            self._cache.clear()

    def invalidate(self, key_prefix: Optional[str] = None):
        """
        Invalida entradas do cache que começam com key_prefix.
        Se key_prefix for None, limpa tudo.
        """
        with self._lock:
            if key_prefix is None:
                self._cache.clear()
            else:
                keys_to_delete = [
                    k for k in self._cache
                    if str(k).startswith(key_prefix)
                ]
                for k in keys_to_delete:
                    del self._cache[k]


# Cache global compartilhado entre todos os endpoints
_cache_instances: dict[str, TTLCache] = {}


def get_cache(name: str = "default", maxsize: int = 128, ttl: int = 300) -> TTLCache:
    """Retorna ou cria uma instância de cache com o nome especificado."""
    if name not in _cache_instances:
        _cache_instances[name] = TTLCache(maxsize=maxsize, ttl=ttl)
    return _cache_instances[name]


def ttl_cache(maxsize: int = 128, ttl: int = 300, cache_name: Optional[str] = None):
    """
    Decorator para cache com TTL.

    Args:
        maxsize: Número máximo de entradas no cache.
        ttl: Tempo de vida em segundos.
        cache_name: Nome do cache (opcional, para agrupar endpoints).

    Uso:
        @router.get("/exemplo")
        @ttl_cache(ttl=300)
        def meu_endpoint():
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Nome do cache baseado na função se não especificado
        name = cache_name or f"{func.__module__}.{func.__qualname__}"
        cache = get_cache(name, maxsize=maxsize, ttl=ttl)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Se o primeiro argumento for Response, extrai para poder
            # adicionar headers de cache
            response = None
            filtered_args = []
            for arg in args:
                from fastapi import Response
                if isinstance(arg, Response):
                    response = arg
                else:
                    filtered_args.append(arg)

            # Ignora o parâmetro _t (timestamp) para cache,
            # mas permite que ele force bypass no navegador
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k != "_t"
            }

            key = (tuple(filtered_args), tuple(sorted(filtered_kwargs.items())))

            # Tenta obter do cache
            cached = cache.get(key)
            if cached is not None:
                result = cached
            else:
                result = func(*args, **kwargs)
                cache.set(key, result)

            # Adiciona headers de cache na resposta
            if response is not None:
                response.headers["Cache-Control"] = (
                    f"public, max-age={ttl}, must-revalidate"
                )
                response.headers["X-Cache-TTL"] = str(ttl)

            return result

        # Expõe o cache para permitir invalidação manual
        wrapper.cache = cache
        wrapper.cache_name = name

        return wrapper

    return decorator


def invalidate_cache(cache_name: Optional[str] = None):
    """
    Invalida um cache específico ou todos os caches.

    Args:
        cache_name: Nome do cache a invalidar. Se None, invalida todos.
    """
    if cache_name:
        if cache_name in _cache_instances:
            _cache_instances[cache_name].clear()
            _log.info(f"Cache '{cache_name}' invalidado manualmente")
    else:
        for name, cache in _cache_instances.items():
            cache.clear()
        _log.info("Todos os caches invalidados manualmente")


def get_cache_stats() -> dict:
    """Retorna estatísticas de todos os caches ativos."""
    stats = {}
    for name, cache in _cache_instances.items():
        with cache._lock:
            stats[name] = {
                "size": len(cache._cache),
                "maxsize": cache.maxsize,
                "ttl": cache.ttl,
            }
    return stats
