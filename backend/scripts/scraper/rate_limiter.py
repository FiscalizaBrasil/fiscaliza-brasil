"""
Rate limiter global (token bucket) para APIs externas.

Cada API tem sua própria instância com taxa máxima de requisições por segundo.
O controle é thread-safe e garante que o limite seja respeitado somando
todas as threads do worker.
"""

import time
import threading
from urllib.parse import urlparse


class RateLimiter:
    """Token bucket rate limiter, thread-safe."""

    def __init__(self, max_rate: float):
        self.rate = max_rate
        self.tokens = float(max_rate)
        self.max_tokens = float(max_rate)
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self):
        """Aguarda até que uma requisição possa ser feita, respeitando o rate."""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_tokens, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
            else:
                wait = (1.0 - self.tokens) / self.rate
                time.sleep(wait)
                self.tokens = 0.0
                self.last_refill = time.monotonic()


# Instâncias por API (compartilhadas entre todas as threads)
camara_limiter = RateLimiter(max_rate=10)           # dadosabertos.camara.leg.br
senado_legis_limiter = RateLimiter(max_rate=5)       # legis.senado.leg.br
senado_adm_limiter = RateLimiter(max_rate=1)         # adm.senado.gov.br
portal_limiter = RateLimiter(max_rate=10)            # api.portaldatransparencia.gov.br


def get_limiter_for_url(url: str) -> RateLimiter:
    """Retorna o rate limiter apropriado para uma URL, baseado no hostname."""
    hostname = urlparse(url).hostname or ""
    if "camara.leg.br" in hostname:
        return camara_limiter
    if "legis.senado.leg.br" in hostname:
        return senado_legis_limiter
    if "adm.senado.gov.br" in hostname:
        return senado_adm_limiter
    if "portaldatransparencia.gov.br" in hostname:
        return portal_limiter
    # Default: retorna o da Câmara como fallback conservador
    return camara_limiter
