"""Shared HTTP client with timeouts, bounded retries and latency logging (docs/02 §6)."""

import asyncio
import logging
import random
import time
import weakref
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from planner.domain.errors import ProviderUnavailableError

log = logging.getLogger(__name__)

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RETRY_AFTER_S = 3.0

Sleep = Callable[[float], Awaitable[None]]

# One pooled AsyncClient per event loop. Under ASGI that's one per worker process; the
# sync test client spins up short-lived loops, so the clients can't be module globals.
_clients: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, httpx.AsyncClient]" = (
    weakref.WeakKeyDictionary()
)


def _shared_client(timeout_s: float) -> httpx.AsyncClient:
    loop = asyncio.get_running_loop()
    client = _clients.get(loop)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(timeout_s),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={"User-Agent": "weather-truck-routing/1.0"},
        )
        _clients[loop] = client
    return client


class HttpClient:
    def __init__(
        self,
        *,
        timeout_s: float = 8.0,
        backoff_s: tuple[float, ...] = (0.3, 0.9),
        sleep: Sleep = asyncio.sleep,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.timeout_s = timeout_s
        self.backoff_s = backoff_s
        self.sleep = sleep
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        return self._client or _shared_client(self.timeout_s)

    async def get_json(
        self, url: str, params: Mapping[str, str | int | float], *, provider: str
    ) -> tuple[int, Any]:
        """GET with up to len(backoff_s) retries on timeouts, transport errors, 429 and 5xx.
        Returns (status, parsed JSON) for any other response; the caller interprets 4xx."""
        attempt = 0
        while True:
            started = time.perf_counter()
            try:
                response = await self.client.get(url, params=params)
            except httpx.TransportError as exc:  # includes timeouts
                outcome, retry_after = type(exc).__name__, None
            else:
                outcome, retry_after = str(response.status_code), _retry_after(response)
                if response.status_code not in RETRY_STATUSES:
                    self._log(provider, outcome, started, attempt)
                    return response.status_code, _json_or_none(response)
            self._log(provider, outcome, started, attempt)
            if attempt >= len(self.backoff_s):
                raise ProviderUnavailableError(f"{provider} is unavailable right now.")
            delay = self.backoff_s[attempt] * (1 + random.uniform(0, 0.25))
            await self.sleep(max(delay, retry_after or 0.0))
            attempt += 1

    @staticmethod
    def _log(provider: str, outcome: str, started: float, attempt: int) -> None:
        # Never log the URL or params: they carry the access token.
        log.info(
            "provider call",
            extra={
                "provider": provider,
                "outcome": outcome,
                "attempt": attempt,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return min(float(raw), MAX_RETRY_AFTER_S)
    except ValueError:
        return None


def _json_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
