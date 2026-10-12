"""
Limite simples de tentativas, em memória (o app roda em 1 processo).
Protege o cadastro aberto e o login contra robôs e adivinhação de senha.
"""
import threading
import time
from collections import deque


class SlidingWindow:
    """No máximo `limit` marcações por `window_seconds` para cada chave."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _fresh(self, key: str, now: float) -> deque:
        q = self._hits.get(key)
        if q is None:
            q = self._hits[key] = deque()
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._fresh(key, time.monotonic())) >= self.limit

    def add(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._fresh(key, now).append(now)
            if len(self._hits) > 10_000:  # não deixa a memória crescer sem fim
                for k in [k for k, q in self._hits.items() if not q or now - q[-1] > self.window]:
                    self._hits.pop(k, None)

    def clear(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


def client_ip(request) -> str:
    return request.client.host if request.client else "desconhecido"
