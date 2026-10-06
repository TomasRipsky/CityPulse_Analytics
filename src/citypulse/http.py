"""HTTP with retries: JSON APIs (Open-Meteo) and large file downloads (Citi Bike ZIPs).

Server errors, rate limits and dropped connections are retried with exponential backoff
(honouring Retry-After); client errors (4xx) are not — retrying a bad request cannot fix it.
Downloads stream to disk and are checked against Content-Length, so a cut connection is
retried instead of producing a short file.
"""

from __future__ import annotations

import json
import logging
import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_DELAY = 60.0


class NotPublishedError(Exception):
    """The file does not exist at the source (yet) — e.g. a month Citi Bike has not published."""


class IncompleteDownloadError(OSError):
    """The body ended before Content-Length bytes arrived."""


@dataclass(frozen=True)
class DownloadInfo:
    """What the server said about a downloaded file: enough to prove later which version we read."""

    size: int
    etag: str | None
    last_modified: str | None


def backoff_delay(
    attempt: int, retry_after: str | None, rng: Callable[[], float] = random.random
) -> float:
    """Seconds to wait after failed `attempt` (1-based): numeric Retry-After, else 2^n + jitter."""
    if retry_after is not None:
        try:
            seconds = float(retry_after)
        except ValueError:
            pass  # HTTP-date form: fall back to our own backoff
        else:
            if math.isfinite(seconds) and seconds >= 0:
                return min(seconds, MAX_DELAY)
    return min(2.0**attempt + rng(), MAX_DELAY)


class Http:
    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_attempts: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client or httpx.Client(timeout=httpx.Timeout(30.0, read=120.0))
        self.max_attempts = max_attempts
        self._sleep = sleep

    def get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        return json.loads(self.get_bytes(url, params))

    def get_bytes(self, url: str, params: dict[str, Any]) -> bytes:
        """The response body, exactly as received (after transfer decoding)."""
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError as exc:
                if attempt == self.max_attempts:
                    raise
                self._wait(url, attempt, str(exc), None)
                continue
            if response.status_code in RETRYABLE_STATUS and attempt < self.max_attempts:
                self._wait(
                    url,
                    attempt,
                    f"HTTP {response.status_code}",
                    response.headers.get("Retry-After"),
                )
                continue
            response.raise_for_status()
            return response.content
        raise AssertionError("unreachable")

    def download(self, url: str, dest: Path) -> DownloadInfo:
        """Stream `url` into `dest`. Raises NotPublishedError on 403/404."""
        partial = dest.with_name(dest.name + ".part")
        try:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    info = self._download_once(url, partial)
                except (httpx.TransportError, IncompleteDownloadError) as exc:
                    if attempt == self.max_attempts:
                        raise
                    self._wait(url, attempt, str(exc), None)
                    continue
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    if status not in RETRYABLE_STATUS or attempt == self.max_attempts:
                        raise
                    self._wait(
                        url, attempt, f"HTTP {status}", exc.response.headers.get("Retry-After")
                    )
                    continue
                partial.replace(dest)
                return info
            raise AssertionError("unreachable")
        finally:
            partial.unlink(missing_ok=True)

    def _download_once(self, url: str, partial: Path) -> DownloadInfo:
        with self._client.stream("GET", url) as response:
            if response.status_code in (403, 404):  # S3 answers 403 for a missing public key
                raise NotPublishedError(f"{url}: HTTP {response.status_code}")
            response.raise_for_status()
            expected = response.headers.get("Content-Length")
            etag, modified = response.headers.get("ETag"), response.headers.get("Last-Modified")
            size = 0
            with partial.open("wb") as handle:
                for chunk in response.iter_bytes(chunk_size=1 << 20):
                    handle.write(chunk)
                    size += len(chunk)
        if expected is not None and size != int(expected):
            raise IncompleteDownloadError(f"{url}: got {size} of {expected} bytes")
        return DownloadInfo(size=size, etag=etag, last_modified=modified)

    def _wait(self, url: str, attempt: int, reason: str, retry_after: str | None) -> None:
        delay = backoff_delay(attempt, retry_after)
        log.warning("%s: %s; retry %d in %.1fs", url, reason, attempt, delay)
        self._sleep(delay)
