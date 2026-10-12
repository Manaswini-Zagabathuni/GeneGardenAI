import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from genegarden_api.core.errors import ApplicationError
from genegarden_api.services.cache import TTLMemoryCache

SleepCallable = Callable[[float], Awaitable[None]]
_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class ExternalServiceError(ApplicationError):
    def __init__(self, service: str, message: str, *, unavailable: bool = False) -> None:
        super().__init__(
            code=f"{service}_unavailable" if unavailable else f"{service}_error",
            message=message,
            status_code=503 if unavailable else 502,
        )


class ExternalResponseError(ExternalServiceError):
    pass


class ResilientJsonClient:
    def __init__(
        self,
        *,
        service_name: str,
        base_url: str,
        timeout_seconds: float,
        max_attempts: int,
        backoff_seconds: float,
        user_agent: str,
        cache: TTLMemoryCache[dict[str, Any]],
        client: httpx.AsyncClient | None = None,
        sleep: SleepCallable = asyncio.sleep,
    ) -> None:
        self._service_name = service_name
        self._base_url = base_url.rstrip("/")
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds
        self._cache = cache
        self._sleep = sleep
        self._timeout = httpx.Timeout(timeout_seconds)
        self._headers = {"Accept": "application/json", "User-Agent": user_agent}
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=self._timeout,
            headers=self._headers,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        cache_key: str,
        params: Mapping[str, str | int] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached

        last_error: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                request_url = self._base_url if not path else f"{self._base_url}/{path.lstrip('/')}"
                response = await self._client.request(
                    method,
                    request_url,
                    params=params,
                    json=json_body,
                    timeout=self._timeout,
                    headers=self._headers,
                )
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if attempt + 1 < self._max_attempts:
                        await self._sleep(self._retry_delay(response, attempt))
                        continue
                    raise ExternalServiceError(
                        self._service_name,
                        f"{self._service_name} remained unavailable after bounded retries.",
                        unavailable=True,
                    )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ExternalResponseError(
                        self._service_name,
                        f"{self._service_name} returned a non-object JSON response.",
                    )
                await self._cache.set(cache_key, payload)
                return payload
            except ExternalServiceError:
                raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._backoff_seconds * (2**attempt))
                    continue
            except (httpx.HTTPStatusError, ValueError) as exc:
                raise ExternalServiceError(
                    self._service_name,
                    f"{self._service_name} returned an invalid response.",
                ) from exc

        raise ExternalServiceError(
            self._service_name,
            f"{self._service_name} could not be reached after bounded retries.",
            unavailable=True,
        ) from last_error

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 10.0)
            except ValueError:
                pass
        return min(self._backoff_seconds * (2**attempt), 10.0)
