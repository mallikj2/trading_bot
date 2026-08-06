"""Small, injectable HTTPS transports with retry and rate-limit controls."""

from __future__ import annotations

from dataclasses import dataclass
import json
import random
import time
from typing import Any, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


class ProviderRequestError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class JsonTransport(Protocol):
    def get_json(self, url: str, *, headers: Mapping[str, str], timeout: float) -> Mapping[str, Any]: ...


class TextTransport(Protocol):
    def get_text(self, url: str, *, headers: Mapping[str, str], timeout: float) -> str: ...


class UrllibJsonTransport:
    def get_json(self, url: str, *, headers: Mapping[str, str], timeout: float) -> Mapping[str, Any]:
        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:  # nosec B310: caller pins allowed host
                payload = json.load(response)
        except HTTPError as exc:
            body = exc.read(1024).decode("utf-8", errors="replace")
            raise ProviderRequestError(
                f"provider returned HTTP {exc.code}: {body}", status_code=exc.code
            ) from exc
        except URLError as exc:
            raise ProviderRequestError(f"provider request failed: {exc.reason}") from exc
        if not isinstance(payload, Mapping):
            raise ProviderRequestError("provider response must be a JSON object")
        return payload


class UrllibTextTransport:
    def get_text(self, url: str, *, headers: Mapping[str, str], timeout: float) -> str:
        request = Request(url, headers=dict(headers), method="GET")
        try:
            with urlopen(request, timeout=timeout) as response:  # nosec B310: caller pins allowed host
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
        except HTTPError as exc:
            body = exc.read(1024).decode("utf-8", errors="replace")
            raise ProviderRequestError(
                f"provider returned HTTP {exc.code}: {body}", status_code=exc.code
            ) from exc
        except URLError as exc:
            raise ProviderRequestError(f"provider request failed: {exc.reason}") from exc
        return raw.decode(charset, errors="replace")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 4
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 8.0
    retryable_statuses: tuple[int, ...] = (429, 500, 502, 503, 504)

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError("attempts must be at least one")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("invalid retry delays")


class RateLimiter:
    def __init__(self, requests_per_second: float, *, clock=time.monotonic, sleeper=time.sleep) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self._minimum_interval = 1.0 / requests_per_second
        self._clock = clock
        self._sleeper = sleeper
        self._last_request_at: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last_request_at is not None:
            remaining = self._minimum_interval - (now - self._last_request_at)
            if remaining > 0:
                self._sleeper(remaining)
                now = self._clock()
        self._last_request_at = now


class _SafeClientBase:
    def __init__(
        self,
        *,
        base_url: str,
        default_headers: Mapping[str, str],
        requests_per_second: float,
        retry_policy: RetryPolicy | None,
        timeout_seconds: float,
        sleeper,
    ) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTPS URL")
        self.base_url = base_url.rstrip("/")
        self._allowed_host = parsed.netloc
        self.default_headers = dict(default_headers)
        self.rate_limiter = RateLimiter(requests_per_second, sleeper=sleeper)
        self.retry_policy = retry_policy or RetryPolicy()
        self.timeout_seconds = timeout_seconds
        self._sleeper = sleeper

    def _url(self, path_or_url: str, params: Mapping[str, Any] | None = None) -> str:
        if path_or_url.startswith("https://"):
            candidate = path_or_url
        elif path_or_url.startswith("/"):
            candidate = f"{self.base_url}{path_or_url}"
        else:
            raise ValueError("path must start with '/' or be an absolute HTTPS URL")

        parsed = urlparse(candidate)
        if parsed.scheme != "https" or parsed.netloc != self._allowed_host:
            raise ProviderRequestError("provider request attempted to leave the allowed HTTPS host")

        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if params:
            for key, value in params.items():
                if value is None:
                    continue
                if isinstance(value, bool):
                    query[key] = "true" if value else "false"
                else:
                    query[key] = str(value)
        return urlunparse(parsed._replace(query=urlencode(query)))

    def _retry(self, call):
        last_error: ProviderRequestError | None = None
        for attempt in range(self.retry_policy.attempts):
            self.rate_limiter.wait()
            try:
                return call()
            except ProviderRequestError as exc:
                last_error = exc
                retryable = exc.status_code in self.retry_policy.retryable_statuses
                if not retryable or attempt + 1 >= self.retry_policy.attempts:
                    raise
                exponential = min(
                    self.retry_policy.max_delay_seconds,
                    self.retry_policy.base_delay_seconds * (2**attempt),
                )
                self._sleeper(exponential + random.random() * min(0.25, exponential))
        assert last_error is not None
        raise last_error


class SafeJsonClient(_SafeClientBase):
    """GET-only JSON client that rejects requests to an unexpected host."""

    def __init__(
        self,
        *,
        base_url: str,
        default_headers: Mapping[str, str],
        transport: JsonTransport | None = None,
        requests_per_second: float = 5.0,
        retry_policy: RetryPolicy | None = None,
        timeout_seconds: float = 60.0,
        sleeper=time.sleep,
    ) -> None:
        super().__init__(
            base_url=base_url,
            default_headers=default_headers,
            requests_per_second=requests_per_second,
            retry_policy=retry_policy,
            timeout_seconds=timeout_seconds,
            sleeper=sleeper,
        )
        self.transport = transport or UrllibJsonTransport()

    def get_json(self, path_or_url: str, *, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        url = self._url(path_or_url, params)
        return self._retry(
            lambda: self.transport.get_json(
                url,
                headers=self.default_headers,
                timeout=self.timeout_seconds,
            )
        )


class SafeTextClient(_SafeClientBase):
    """GET-only text client that rejects requests to an unexpected host."""

    def __init__(
        self,
        *,
        base_url: str,
        default_headers: Mapping[str, str],
        transport: TextTransport | None = None,
        requests_per_second: float = 5.0,
        retry_policy: RetryPolicy | None = None,
        timeout_seconds: float = 60.0,
        sleeper=time.sleep,
    ) -> None:
        super().__init__(
            base_url=base_url,
            default_headers=default_headers,
            requests_per_second=requests_per_second,
            retry_policy=retry_policy,
            timeout_seconds=timeout_seconds,
            sleeper=sleeper,
        )
        self.transport = transport or UrllibTextTransport()

    def get_text(self, path_or_url: str, *, params: Mapping[str, Any] | None = None) -> str:
        url = self._url(path_or_url, params)
        return self._retry(
            lambda: self.transport.get_text(
                url,
                headers=self.default_headers,
                timeout=self.timeout_seconds,
            )
        )


def redact_url(url: str, *, secret_keys: set[str] | None = None) -> str:
    keys = {key.lower() for key in (secret_keys or {"apikey", "api_key", "token", "access_token"})}
    parsed = urlparse(url)
    redacted = [
        (key, "REDACTED" if key.lower() in keys else value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunparse(parsed._replace(query=urlencode(redacted)))
