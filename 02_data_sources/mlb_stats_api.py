# ============================================================
# AISP2 BASEBALL INTELLIGENCE PLATFORM
# PHASE 11 PART 5.0
# FILE: 02_data_sources/mlb_stats_api.py
# PURPOSE:
# Authoritative MLB Stats API client for team, player, roster,
# schedule, game, lineup, probable-pitcher, venue, standings,
# league-leader, statistics, ingestion, and prediction features.
# ============================================================

from __future__ import annotations

# ============================================================
# SECTION 01 - STANDARD LIBRARY IMPORTS
# ============================================================

from collections import OrderedDict
from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import date
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
import logging
import math
import random
import threading
import time
from typing import Any
from typing import Final
from urllib.parse import urlencode


# ============================================================
# SECTION 02 - THIRD-PARTY IMPORTS
# ============================================================

import requests
from requests import Response
from requests import Session
from requests.adapters import HTTPAdapter


# ============================================================
# SECTION 03 - MODULE METADATA
# ============================================================

CLIENT_NAME: Final[str] = "AISP2 Enterprise MLB Stats API Client"
CLIENT_VERSION: Final[str] = "6.0.0"
CLIENT_PHASE: Final[str] = "Phase 11 Part 5.0"
CLIENT_PATH: Final[str] = "02_data_sources/mlb_stats_api.py"
CLIENT_STATUS: Final[str] = "enterprise_ready"

MLB_API_BASE_URL: Final[str] = "https://statsapi.mlb.com/api/v1"
MLB_LIVE_BASE_URL: Final[str] = "https://statsapi.mlb.com/api/v1.1"
DEFAULT_TIMEOUT: Final[float] = 30.0
DEFAULT_CONNECT_TIMEOUT: Final[float] = 10.0
DEFAULT_READ_TIMEOUT: Final[float] = 30.0
DEFAULT_SPORT_ID: Final[int] = 1
DEFAULT_SEASON: Final[int] = datetime.now(UTC).year

DEFAULT_MAX_RETRIES: Final[int] = 4
DEFAULT_BACKOFF_FACTOR: Final[float] = 0.75
DEFAULT_BACKOFF_JITTER: Final[float] = 0.25
DEFAULT_CACHE_TTL_SECONDS: Final[int] = 300
DEFAULT_CACHE_MAX_ENTRIES: Final[int] = 512
DEFAULT_PAGE_SIZE: Final[int] = 100
DEFAULT_MAX_PAGES: Final[int] = 100

DEFAULT_USER_AGENT: Final[str] = (
    "AISP2-Baseball/6.0 "
    "(https://github.com/CodeDressing/AISP2_Baseball)"
)

RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({
    408,
    425,
    429,
    500,
    502,
    503,
    504,
})

SAFE_CACHEABLE_PATH_PREFIXES: Final[tuple[str, ...]] = (
    "teams",
    "people",
    "sports",
    "schedule",
    "game",
    "venues",
    "league",
    "divisions",
    "standings",
    "stats",
)

LOGGER = logging.getLogger("aisp2.mlb_stats_api")


# ============================================================
# SECTION 04 - ENUMERATIONS
# ============================================================

class SourceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class RequestOutcome(str, Enum):
    SUCCESS = "success"
    RETRIED_SUCCESS = "retried_success"
    CLIENT_ERROR = "client_error"
    SERVER_ERROR = "server_error"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    INVALID_JSON = "invalid_json"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"


class CacheOutcome(str, Enum):
    HIT = "hit"
    MISS = "miss"
    BYPASS = "bypass"
    EXPIRED = "expired"
    STORED = "stored"


# ============================================================
# SECTION 05 - STRUCTURED ERRORS
# ============================================================

class MLBStatsAPIError(RuntimeError):
    """Base error for MLB Stats API client failures."""

    def __init__(
        self,
        message: str,
        *,
        url: str | None = None,
        status_code: int | None = None,
        response_text: str | None = None,
        request_id: str | None = None,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)

        self.message = message
        self.url = url
        self.status_code = status_code
        self.response_text = response_text
        self.request_id = request_id
        self.retryable = retryable
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "url": self.url,
            "status_code": self.status_code,
            "response_text": self.response_text,
            "request_id": self.request_id,
            "retryable": self.retryable,
            "details": self.details,
        }


class MLBStatsAPITimeoutError(MLBStatsAPIError):
    """Request timed out."""


class MLBStatsAPIConnectionError(MLBStatsAPIError):
    """Connection could not be established."""


class MLBStatsAPIHTTPError(MLBStatsAPIError):
    """Remote service returned an HTTP error."""


class MLBStatsAPIRateLimitError(MLBStatsAPIHTTPError):
    """Remote service returned a rate-limit response."""


class MLBStatsAPIJSONError(MLBStatsAPIError):
    """Response was not valid JSON."""


class MLBStatsAPIValidationError(MLBStatsAPIError):
    """Response JSON did not match the expected contract."""


class MLBStatsAPIPaginationError(MLBStatsAPIError):
    """Pagination could not complete safely."""


# ============================================================
# SECTION 06 - CONFIGURATION CONTRACT
# ============================================================

@dataclass(frozen=True, slots=True)
class MLBStatsAPISettings:
    base_url: str = MLB_API_BASE_URL
    live_base_url: str = MLB_LIVE_BASE_URL

    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    read_timeout: float = DEFAULT_READ_TIMEOUT

    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
    backoff_jitter: float = DEFAULT_BACKOFF_JITTER

    cache_enabled: bool = True
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    cache_max_entries: int = DEFAULT_CACHE_MAX_ENTRIES

    rate_limit_floor_seconds: float = 0.0
    respect_retry_after: bool = True

    user_agent: str = DEFAULT_USER_AGENT
    verify_ssl: bool = True

    page_size: int = DEFAULT_PAGE_SIZE
    max_pages: int = DEFAULT_MAX_PAGES

    def validate(self) -> None:
        if not self.base_url:
            raise ValueError("base_url cannot be empty")

        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout must be positive")

        if self.read_timeout <= 0:
            raise ValueError("read_timeout must be positive")

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        if self.backoff_factor < 0:
            raise ValueError("backoff_factor cannot be negative")

        if self.cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds cannot be negative")

        if self.cache_max_entries < 1:
            raise ValueError("cache_max_entries must be at least one")

        if self.page_size < 1:
            raise ValueError("page_size must be at least one")

        if self.max_pages < 1:
            raise ValueError("max_pages must be at least one")


# ============================================================
# SECTION 07 - REQUEST METRICS
# ============================================================

@dataclass(slots=True)
class RequestMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    retried_requests: int = 0
    rate_limited_requests: int = 0
    timeout_requests: int = 0
    connection_errors: int = 0
    invalid_json_responses: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_stores: int = 0

    total_latency_ms: float = 0.0
    last_request_at: str | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None

    status_code_counts: dict[str, int] = field(
        default_factory=dict
    )

    endpoint_counts: dict[str, int] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        average_latency = (
            self.total_latency_ms / self.total_requests
            if self.total_requests
            else 0.0
        )

        return {
            **asdict(self),
            "average_latency_ms": round(
                average_latency,
                6,
            ),
        }


# ============================================================
# SECTION 08 - RESPONSE ENVELOPE
# ============================================================

@dataclass(slots=True)
class SourceResponse:
    data: dict[str, Any]
    source: str
    source_url: str
    source_timestamp: str
    request_id: str
    status_code: int
    elapsed_ms: float
    from_cache: bool
    attempts: int
    headers: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "source": self.source,
            "source_url": self.source_url,
            "source_timestamp": self.source_timestamp,
            "request_id": self.request_id,
            "status_code": self.status_code,
            "elapsed_ms": round(self.elapsed_ms, 6),
            "from_cache": self.from_cache,
            "attempts": self.attempts,
            "headers": self.headers,
        }


# ============================================================
# SECTION 09 - CACHE CONTRACTS
# ============================================================

@dataclass(slots=True)
class CacheEntry:
    value: dict[str, Any]
    stored_at: float
    expires_at: float
    source_timestamp: str

    def expired(self, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        return now >= self.expires_at


class ResponseCache:
    """
    Thread-safe in-memory LRU cache for safe GET responses.
    """

    def __init__(
        self,
        *,
        max_entries: int,
        ttl_seconds: int,
    ) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._entries: OrderedDict[
            str,
            CacheEntry,
        ] = OrderedDict()
        self._lock = threading.RLock()

    def get(
        self,
        key: str,
    ) -> CacheEntry | None:
        with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                return None

            if entry.expired():
                self._entries.pop(key, None)
                return None

            self._entries.move_to_end(key)
            return entry

    def set(
        self,
        key: str,
        value: dict[str, Any],
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        ttl = (
            self.ttl_seconds
            if ttl_seconds is None
            else max(0, int(ttl_seconds))
        )

        now = time.time()

        entry = CacheEntry(
            value=value,
            stored_at=now,
            expires_at=now + ttl,
            source_timestamp=datetime.now(UTC).isoformat(),
        )

        with self._lock:
            self._entries[key] = entry
            self._entries.move_to_end(key)

            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._entries)


# ============================================================
# SECTION 10 - LOW-LEVEL UTILITIES
# ============================================================

def utc_now() -> datetime:
    return datetime.now(UTC)


def safe_integer(
    value: Any,
) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)

    except (TypeError, ValueError):
        return None


def safe_float(
    value: Any,
) -> float | None:
    if value in (None, ""):
        return None

    try:
        numeric = float(value)

        if math.isnan(numeric):
            return None

        return numeric

    except (TypeError, ValueError):
        return None


def safe_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def coerce_mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)

    return {}


def coerce_list(
    value: Any,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    return [
        coerce_mapping(item)
        for item in value
    ]


def canonical_query_string(
    params: Mapping[str, Any] | None,
) -> str:
    normalized: list[tuple[str, str]] = []

    for key, value in sorted(
        dict(params or {}).items()
    ):
        if value is None:
            continue

        if isinstance(value, (list, tuple, set)):
            normalized.append(
                (
                    str(key),
                    ",".join(
                        str(item)
                        for item in value
                    ),
                )
            )

        else:
            normalized.append(
                (str(key), str(value))
            )

    return urlencode(normalized)


def build_request_id(
    method: str,
    url: str,
    params: Mapping[str, Any] | None,
) -> str:
    payload = (
        f"{method.upper()}|{url}|"
        f"{canonical_query_string(params)}|"
        f"{time.time_ns()}"
    )

    return sha256(
        payload.encode("utf-8")
    ).hexdigest()[:24]


def build_cache_key(
    url: str,
    params: Mapping[str, Any] | None,
) -> str:
    payload = (
        f"{url}|{canonical_query_string(params)}"
    )

    return sha256(
        payload.encode("utf-8")
    ).hexdigest()


# ============================================================
# SECTION 11 - CLIENT IMPLEMENTATION
# ============================================================

class MLBStatsAPIClient:
    """
    Authoritative MLB Stats API client.

    This client performs source retrieval only. It does not write
    database records and does not calculate predictions.
    """

    def __init__(
        self,
        base_url: str = MLB_API_BASE_URL,
        timeout: int | float | tuple[float, float] = DEFAULT_TIMEOUT,
        *,
        settings: MLBStatsAPISettings | None = None,
        session: Session | None = None,
    ) -> None:
        if settings is None:
            if isinstance(timeout, tuple):
                connect_timeout = float(timeout[0])
                read_timeout = float(timeout[1])

            else:
                connect_timeout = min(
                    DEFAULT_CONNECT_TIMEOUT,
                    float(timeout),
                )
                read_timeout = float(timeout)

            settings = MLBStatsAPISettings(
                base_url=base_url.rstrip("/"),
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
            )

        settings.validate()

        self.settings = settings
        self.base_url = settings.base_url.rstrip("/")
        self.live_base_url = settings.live_base_url.rstrip("/")
        self.timeout = (
            settings.connect_timeout,
            settings.read_timeout,
        )

        self.session = session or requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": settings.user_agent,
        })

        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=0,
        )

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.cache = ResponseCache(
            max_entries=settings.cache_max_entries,
            ttl_seconds=settings.cache_ttl_seconds,
        )

        self._metrics = RequestMetrics()
        self._metrics_lock = threading.RLock()
        self._rate_limit_lock = threading.RLock()
        self._last_request_monotonic = 0.0

    # ========================================================
    # SECTION 11.01 - METRICS
    # ========================================================

    def _increment_metric(
        self,
        field_name: str,
        amount: int | float = 1,
    ) -> None:
        with self._metrics_lock:
            current = getattr(
                self._metrics,
                field_name,
            )

            setattr(
                self._metrics,
                field_name,
                current + amount,
            )

    def _record_status_code(
        self,
        status_code: int,
    ) -> None:
        with self._metrics_lock:
            key = str(status_code)

            self._metrics.status_code_counts[key] = (
                self._metrics.status_code_counts.get(
                    key,
                    0,
                )
                + 1
            )

    def _record_endpoint(
        self,
        path: str,
    ) -> None:
        endpoint = path.strip("/").split("/")[0] or "root"

        with self._metrics_lock:
            self._metrics.endpoint_counts[endpoint] = (
                self._metrics.endpoint_counts.get(
                    endpoint,
                    0,
                )
                + 1
            )

    def request_metrics(
        self,
    ) -> dict[str, Any]:
        with self._metrics_lock:
            return self._metrics.to_dict()

    def reset_request_metrics(
        self,
    ) -> None:
        with self._metrics_lock:
            self._metrics = RequestMetrics()

    # ========================================================
    # SECTION 11.02 - RATE LIMIT AWARENESS
    # ========================================================

    def _respect_rate_limit_floor(
        self,
    ) -> None:
        floor = self.settings.rate_limit_floor_seconds

        if floor <= 0:
            return

        with self._rate_limit_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_monotonic
            remaining = floor - elapsed

            if remaining > 0:
                time.sleep(remaining)

            self._last_request_monotonic = time.monotonic()

    def _retry_after_seconds(
        self,
        response: Response,
    ) -> float | None:
        raw = response.headers.get("Retry-After")

        if not raw:
            return None

        numeric = safe_float(raw)

        if numeric is not None:
            return max(0.0, numeric)

        try:
            retry_at = datetime.fromisoformat(
                raw.replace("Z", "+00:00")
            )

            return max(
                0.0,
                (
                    retry_at.astimezone(UTC)
                    - utc_now()
                ).total_seconds(),
            )

        except ValueError:
            return None

    def _backoff_seconds(
        self,
        attempt: int,
        response: Response | None = None,
    ) -> float:
        if (
            response is not None
            and self.settings.respect_retry_after
        ):
            retry_after = self._retry_after_seconds(
                response
            )

            if retry_after is not None:
                return retry_after

        base = (
            self.settings.backoff_factor
            * (2 ** max(0, attempt - 1))
        )

        jitter = random.uniform(
            0.0,
            self.settings.backoff_jitter,
        )

        return base + jitter

    # ========================================================
    # SECTION 11.03 - URL AND CACHE
    # ========================================================

    def _build_url(
        self,
        path: str,
        *,
        live: bool = False,
    ) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path

        base = self.live_base_url if live else self.base_url

        return f"{base}/{path.lstrip('/')}"

    def _is_cacheable(
        self,
        path: str,
        *,
        use_cache: bool,
    ) -> bool:
        if not self.settings.cache_enabled:
            return False

        if not use_cache:
            return False

        normalized = path.lstrip("/")

        return normalized.startswith(
            SAFE_CACHEABLE_PATH_PREFIXES
        )

    # ========================================================
    # SECTION 11.04 - JSON VALIDATION
    # ========================================================

    def _decode_json(
        self,
        response: Response,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        content_type = (
            response.headers.get("Content-Type", "")
            .lower()
        )

        if (
            "json" not in content_type
            and response.text.strip()
        ):
            LOGGER.debug(
                "Unexpected content type %s for %s",
                content_type,
                response.url,
            )

        try:
            payload = response.json()

        except ValueError as error:
            self._increment_metric(
                "invalid_json_responses"
            )

            raise MLBStatsAPIJSONError(
                "MLB Stats API returned invalid JSON",
                url=response.url,
                status_code=response.status_code,
                response_text=response.text[:1000],
                request_id=request_id,
                retryable=False,
                details={
                    "content_type": content_type,
                    "error": str(error),
                },
            ) from error

        if not isinstance(payload, dict):
            raise MLBStatsAPIValidationError(
                "MLB Stats API returned a non-object JSON payload",
                url=response.url,
                status_code=response.status_code,
                request_id=request_id,
                retryable=False,
                details={
                    "payload_type": type(payload).__name__,
                },
            )

        return payload

    @staticmethod
    def _validate_required_keys(
        payload: Mapping[str, Any],
        required_keys: Iterable[str] | None,
        *,
        url: str,
        request_id: str,
        status_code: int,
    ) -> None:
        if not required_keys:
            return

        missing = [
            key
            for key in required_keys
            if key not in payload
        ]

        if missing:
            raise MLBStatsAPIValidationError(
                "MLB Stats API response is missing required keys",
                url=url,
                status_code=status_code,
                request_id=request_id,
                retryable=False,
                details={
                    "missing_keys": missing,
                    "available_keys": sorted(payload.keys()),
                },
            )

    # ========================================================
    # SECTION 11.05 - CORE REQUEST HANDLER
    # ========================================================

    def request_json(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        live: bool = False,
        use_cache: bool = True,
        cache_ttl_seconds: int | None = None,
        required_keys: Iterable[str] | None = None,
    ) -> SourceResponse:
        url = self._build_url(
            path,
            live=live,
        )

        params_dict = {
            key: value
            for key, value in dict(params or {}).items()
            if value is not None
        }

        request_id = build_request_id(
            "GET",
            url,
            params_dict,
        )

        cacheable = self._is_cacheable(
            path,
            use_cache=use_cache,
        )

        cache_key = build_cache_key(
            url,
            params_dict,
        )

        if cacheable:
            cached = self.cache.get(cache_key)

            if cached is not None:
                self._increment_metric("cache_hits")

                return SourceResponse(
                    data=dict(cached.value),
                    source="MLB Stats API",
                    source_url=url,
                    source_timestamp=cached.source_timestamp,
                    request_id=request_id,
                    status_code=200,
                    elapsed_ms=0.0,
                    from_cache=True,
                    attempts=0,
                    headers={},
                )

            self._increment_metric("cache_misses")

        started_at = time.perf_counter()
        self._increment_metric("total_requests")
        self._record_endpoint(path)

        with self._metrics_lock:
            self._metrics.last_request_at = utc_now().isoformat()

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.settings.max_retries + 2,
        ):
            self._respect_rate_limit_floor()

            try:
                response = self.session.get(
                    url,
                    params=params_dict,
                    timeout=self.timeout,
                    verify=self.settings.verify_ssl,
                )

                self._record_status_code(
                    response.status_code
                )

                if response.status_code == 429:
                    self._increment_metric(
                        "rate_limited_requests"
                    )

                    error = MLBStatsAPIRateLimitError(
                        "MLB Stats API rate limit encountered",
                        url=response.url,
                        status_code=response.status_code,
                        response_text=response.text[:1000],
                        request_id=request_id,
                        retryable=True,
                        details={
                            "retry_after": response.headers.get(
                                "Retry-After"
                            ),
                        },
                    )

                    last_error = error

                    if attempt <= self.settings.max_retries:
                        self._increment_metric(
                            "retried_requests"
                        )

                        time.sleep(
                            self._backoff_seconds(
                                attempt,
                                response,
                            )
                        )
                        continue

                    raise error

                if response.status_code in RETRYABLE_STATUS_CODES:
                    error = MLBStatsAPIHTTPError(
                        "MLB Stats API returned a retryable HTTP error",
                        url=response.url,
                        status_code=response.status_code,
                        response_text=response.text[:1000],
                        request_id=request_id,
                        retryable=True,
                    )

                    last_error = error

                    if attempt <= self.settings.max_retries:
                        self._increment_metric(
                            "retried_requests"
                        )

                        time.sleep(
                            self._backoff_seconds(
                                attempt,
                                response,
                            )
                        )
                        continue

                    raise error

                if response.status_code >= 400:
                    raise MLBStatsAPIHTTPError(
                        "MLB Stats API returned an HTTP error",
                        url=response.url,
                        status_code=response.status_code,
                        response_text=response.text[:1000],
                        request_id=request_id,
                        retryable=False,
                    )

                payload = self._decode_json(
                    response,
                    request_id=request_id,
                )

                self._validate_required_keys(
                    payload,
                    required_keys,
                    url=response.url,
                    request_id=request_id,
                    status_code=response.status_code,
                )

                elapsed_ms = (
                    time.perf_counter()
                    - started_at
                ) * 1000.0

                self._increment_metric(
                    "successful_requests"
                )

                self._increment_metric(
                    "total_latency_ms",
                    elapsed_ms,
                )

                with self._metrics_lock:
                    self._metrics.last_success_at = utc_now().isoformat()

                if cacheable:
                    self.cache.set(
                        cache_key,
                        payload,
                        ttl_seconds=cache_ttl_seconds,
                    )

                    self._increment_metric(
                        "cache_stores"
                    )

                return SourceResponse(
                    data=payload,
                    source="MLB Stats API",
                    source_url=response.url,
                    source_timestamp=utc_now().isoformat(),
                    request_id=request_id,
                    status_code=response.status_code,
                    elapsed_ms=elapsed_ms,
                    from_cache=False,
                    attempts=attempt,
                    headers={
                        key: value
                        for key, value in response.headers.items()
                        if key.lower() in {
                            "content-type",
                            "retry-after",
                            "x-ratelimit-limit",
                            "x-ratelimit-remaining",
                            "date",
                            "etag",
                            "last-modified",
                        }
                    },
                )

            except requests.Timeout as error:
                self._increment_metric(
                    "timeout_requests"
                )

                last_error = MLBStatsAPITimeoutError(
                    "MLB Stats API request timed out",
                    url=url,
                    request_id=request_id,
                    retryable=True,
                    details={
                        "attempt": attempt,
                        "timeout": self.timeout,
                    },
                )

                if attempt <= self.settings.max_retries:
                    self._increment_metric(
                        "retried_requests"
                    )

                    time.sleep(
                        self._backoff_seconds(attempt)
                    )
                    continue

                raise last_error from error

            except requests.ConnectionError as error:
                self._increment_metric(
                    "connection_errors"
                )

                last_error = MLBStatsAPIConnectionError(
                    "MLB Stats API connection failed",
                    url=url,
                    request_id=request_id,
                    retryable=True,
                    details={
                        "attempt": attempt,
                        "error": str(error),
                    },
                )

                if attempt <= self.settings.max_retries:
                    self._increment_metric(
                        "retried_requests"
                    )

                    time.sleep(
                        self._backoff_seconds(attempt)
                    )
                    continue

                raise last_error from error

            except MLBStatsAPIError:
                raise

            except Exception as error:
                last_error = MLBStatsAPIError(
                    "Unexpected MLB Stats API client failure",
                    url=url,
                    request_id=request_id,
                    retryable=False,
                    details={
                        "attempt": attempt,
                        "error_type": type(error).__name__,
                        "error": str(error),
                    },
                )

                raise last_error from error

        self._increment_metric("failed_requests")

        with self._metrics_lock:
            self._metrics.last_failure_at = utc_now().isoformat()

        if isinstance(last_error, MLBStatsAPIError):
            raise last_error

        raise MLBStatsAPIError(
            "MLB Stats API request failed",
            url=url,
            request_id=request_id,
            retryable=False,
        )

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.request_json(
            path,
            params=params,
        ).data

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._get(path, params=params)

    # ========================================================
    # SECTION 11.06 - PAGINATION
    # ========================================================

    def paginate(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        collection_key: str,
        page_size: int | None = None,
        max_pages: int | None = None,
        offset_parameter: str = "offset",
        limit_parameter: str = "limit",
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        page_size = page_size or self.settings.page_size
        max_pages = max_pages or self.settings.max_pages

        base_params = dict(params or {})
        results: list[dict[str, Any]] = []

        offset = 0

        for page_number in range(1, max_pages + 1):
            page_params = {
                **base_params,
                offset_parameter: offset,
                limit_parameter: page_size,
            }

            response = self.request_json(
                path,
                params=page_params,
                use_cache=use_cache,
            )

            items = coerce_list(
                response.data.get(collection_key)
            )

            results.extend(items)

            if len(items) < page_size:
                return results

            offset += page_size

        raise MLBStatsAPIPaginationError(
            "Pagination reached max_pages before completion",
            url=self._build_url(path),
            retryable=False,
            details={
                "collection_key": collection_key,
                "page_size": page_size,
                "max_pages": max_pages,
                "records_collected": len(results),
            },
        )

    # ========================================================
    # SECTION 11.07 - HEALTH
    # ========================================================

    def health_check(
        self,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()

        try:
            teams = self.get_teams(
                season=DEFAULT_SEASON,
            )

            return {
                "source": "MLB Stats API",
                "status": SourceHealth.HEALTHY.value,
                "base_url": self.base_url,
                "teams_returned": len(teams),
                "latency_ms": round(
                    (
                        time.perf_counter()
                        - started_at
                    )
                    * 1000.0,
                    6,
                ),
                "metrics": self.request_metrics(),
                "checked_at": utc_now().isoformat(),
            }

        except Exception as error:
            return {
                "source": "MLB Stats API",
                "status": SourceHealth.UNHEALTHY.value,
                "base_url": self.base_url,
                "error_type": type(error).__name__,
                "error": str(error),
                "latency_ms": round(
                    (
                        time.perf_counter()
                        - started_at
                    )
                    * 1000.0,
                    6,
                ),
                "metrics": self.request_metrics(),
                "checked_at": utc_now().isoformat(),
            }

    # ========================================================
    # SECTION 12 - TEAM ENDPOINTS
    # ========================================================

    def get_teams(
        self,
        season: int = DEFAULT_SEASON,
        sport_id: int = DEFAULT_SPORT_ID,
        *,
        active_only: bool = True,
        hydrate: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "sportId": sport_id,
            "season": season,
        }

        if active_only:
            params["activeStatus"] = "Y"

        if hydrate:
            params["hydrate"] = hydrate

        payload = self.request_json(
            "teams",
            params=params,
            required_keys=("teams",),
            cache_ttl_seconds=900,
        ).data

        return coerce_list(
            payload.get("teams")
        )

    def get_team(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
        *,
        hydrate: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "season": season,
        }

        if hydrate:
            params["hydrate"] = hydrate

        payload = self.request_json(
            f"teams/{team_id}",
            params=params,
            required_keys=("teams",),
            cache_ttl_seconds=900,
        ).data

        teams = coerce_list(
            payload.get("teams")
        )

        return teams[0] if teams else {}

    def get_team_full_profile(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        return self.get_team(
            team_id,
            season,
            hydrate=(
                "venue,division,league,sport,"
                "leagueRecord,records,stats"
            ),
        )

    def get_team_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
        roster_type: str = "active",
        *,
        hydrate: str | None = "person",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "season": season,
            "rosterType": roster_type,
        }

        if hydrate:
            params["hydrate"] = hydrate

        payload = self.request_json(
            f"teams/{team_id}/roster",
            params=params,
            required_keys=("roster",),
            cache_ttl_seconds=300,
        ).data

        return coerce_list(
            payload.get("roster")
        )

    def get_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
        roster_type: str = "active",
    ) -> list[dict[str, Any]]:
        return self.get_team_roster(
            team_id,
            season,
            roster_type,
        )

    def get_active_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        return self.get_team_roster(
            team_id,
            season,
            "active",
        )

    def get_forty_man_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        return self.get_team_roster(
            team_id,
            season,
            "40Man",
        )

    # ========================================================
    # SECTION 13 - PLAYER ENDPOINTS
    # ========================================================

    def search_players(
        self,
        query: str,
        season: int = DEFAULT_SEASON,
        *,
        active_only: bool = True,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        normalized = str(query or "").strip().lower()

        if not normalized:
            return []

        players = self.get_all_active_players(
            season=season,
        )

        matches = [
            player
            for player in players
            if normalized
            in str(
                player.get("fullName", "")
            ).lower()
        ]

        matches.sort(
            key=lambda player: (
                str(
                    player.get("fullName", "")
                ).lower()
                != normalized,
                len(
                    str(
                        player.get("fullName", "")
                    )
                ),
            )
        )

        return matches[:max(1, int(limit))]

    def search_player_by_name(
        self,
        name: str,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        return self.search_players(
            name,
            season,
        )

    def get_player(
        self,
        player_id: int,
        *,
        hydrate: str | None = None,
    ) -> dict[str, Any]:
        params = {}

        if hydrate:
            params["hydrate"] = hydrate

        payload = self.request_json(
            f"people/{player_id}",
            params=params,
            required_keys=("people",),
            cache_ttl_seconds=900,
        ).data

        people = coerce_list(
            payload.get("people")
        )

        return people[0] if people else {}

    def get_person(
        self,
        person_id: int,
    ) -> dict[str, Any]:
        return self.get_player(person_id)

    def get_player_current_team(
        self,
        player_id: int,
    ) -> dict[str, Any]:
        player = self.get_player(
            player_id,
            hydrate="currentTeam",
        )

        return coerce_mapping(
            player.get("currentTeam")
        )

    def get_players_by_ids(
        self,
        player_ids: Sequence[int],
    ) -> list[dict[str, Any]]:
        players: list[dict[str, Any]] = []

        for player_id in player_ids:
            try:
                player = self.get_player(
                    int(player_id)
                )

                if player:
                    players.append(player)

            except MLBStatsAPIError:
                continue

        return players

    def get_all_active_players(
        self,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        payload = self.request_json(
            f"sports/{DEFAULT_SPORT_ID}/players",
            params={
                "season": season,
            },
            required_keys=("people",),
            cache_ttl_seconds=900,
        ).data

        return coerce_list(
            payload.get("people")
        )

    # ========================================================
    # SECTION 14 - PLAYER STAT ENDPOINTS
    # ========================================================

    def get_player_season_stats(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
    ) -> dict[str, Any]:
        return self.request_json(
            f"people/{player_id}/stats",
            params={
                "stats": "season",
                "season": season,
                "group": group,
            },
            required_keys=("stats",),
            cache_ttl_seconds=300,
        ).data

    def get_player_season_hitting_stats(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        return self.get_player_season_stats(
            player_id,
            season,
            "hitting",
        )

    def get_player_season_pitching_stats(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        return self.get_player_season_stats(
            player_id,
            season,
            "pitching",
        )

    def get_player_career_stats(
        self,
        player_id: int,
        group: str = "hitting",
    ) -> dict[str, Any]:
        return self.request_json(
            f"people/{player_id}/stats",
            params={
                "stats": "career",
                "group": group,
            },
            required_keys=("stats",),
            cache_ttl_seconds=1800,
        ).data

    def get_player_game_logs(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
    ) -> dict[str, Any]:
        return self.request_json(
            f"people/{player_id}/stats",
            params={
                "stats": "gameLog",
                "season": season,
                "group": group,
                "hydrate": "team,opponent",
            },
            required_keys=("stats",),
            cache_ttl_seconds=300,
        ).data

    def get_player_game_log(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
    ) -> dict[str, Any]:
        return self.get_player_game_logs(
            player_id,
            season,
            group,
        )

    def get_player_splits(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
        split: str = "statSplits",
        *,
        sit_codes: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "stats": split,
            "season": season,
            "group": group,
        }

        if sit_codes:
            params["sitCodes"] = ",".join(
                str(code)
                for code in sit_codes
            )

        return self.request_json(
            f"people/{player_id}/stats",
            params=params,
            required_keys=("stats",),
            cache_ttl_seconds=300,
        ).data

    def get_complete_player_profile(
        self,
        player_id: int,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        return {
            "source": "MLB Stats API",
            "source_timestamp": utc_now().isoformat(),
            "player": self.get_player(
                player_id,
                hydrate="currentTeam",
            ),
            "current_team": self.get_player_current_team(
                player_id
            ),
            "season_hitting": (
                self.get_player_season_hitting_stats(
                    player_id,
                    season,
                )
            ),
            "season_pitching": (
                self.get_player_season_pitching_stats(
                    player_id,
                    season,
                )
            ),
            "game_logs_hitting": (
                self.get_player_game_logs(
                    player_id,
                    season,
                    "hitting",
                )
            ),
            "game_logs_pitching": (
                self.get_player_game_logs(
                    player_id,
                    season,
                    "pitching",
                )
            ),
            "splits_hitting": (
                self.get_player_splits(
                    player_id,
                    season,
                    "hitting",
                )
            ),
            "splits_pitching": (
                self.get_player_splits(
                    player_id,
                    season,
                    "pitching",
                )
            ),
        }

    # ========================================================
    # SECTION 15 - TEAM STAT ENDPOINTS
    # ========================================================

    def get_team_season_stats(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
    ) -> dict[str, Any]:
        return self.request_json(
            f"teams/{team_id}/stats",
            params={
                "stats": "season",
                "season": season,
                "group": group,
            },
            required_keys=("stats",),
            cache_ttl_seconds=300,
        ).data

    # ========================================================
    # SECTION 16 - SCHEDULE ENDPOINTS
    # ========================================================

    def get_schedule(
        self,
        season: int = DEFAULT_SEASON,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        team_id: int | None = None,
        *,
        game_type: str | None = None,
        hydrate: str | None = (
            "team,venue,probablePitcher,"
            "linescore,flags"
        ),
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "sportId": DEFAULT_SPORT_ID,
            "season": season,
        }

        if start_date is not None:
            params["startDate"] = (
                start_date.isoformat()
                if isinstance(start_date, date)
                else str(start_date)
            )

        if end_date is not None:
            params["endDate"] = (
                end_date.isoformat()
                if isinstance(end_date, date)
                else str(end_date)
            )

        if team_id is not None:
            params["teamId"] = team_id

        if game_type:
            params["gameType"] = game_type

        if hydrate:
            params["hydrate"] = hydrate

        return self.request_json(
            "schedule",
            params=params,
            required_keys=("dates",),
            cache_ttl_seconds=120,
        ).data

    def get_schedule_games(
        self,
        season: int = DEFAULT_SEASON,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        team_id: int | None = None,
    ) -> list[dict[str, Any]]:
        payload = self.get_schedule(
            season,
            start_date,
            end_date,
            team_id,
        )

        games: list[dict[str, Any]] = []

        for date_block in coerce_list(
            payload.get("dates")
        ):
            games.extend(
                coerce_list(
                    date_block.get("games")
                )
            )

        return games

    # ========================================================
    # SECTION 17 - GAME ENDPOINTS
    # ========================================================

    def get_game(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        return self.get_game_feed(game_pk)

    def get_game_feed(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        return self.request_json(
            f"game/{game_pk}/feed/live",
            live=True,
            use_cache=False,
        ).data

    def get_game_boxscore(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        return self.request_json(
            f"game/{game_pk}/boxscore",
            use_cache=False,
        ).data

    def get_game_linescore(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        return self.request_json(
            f"game/{game_pk}/linescore",
            use_cache=False,
        ).data

    def get_game_content(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        return self.request_json(
            f"game/{game_pk}/content",
            cache_ttl_seconds=300,
        ).data

    def get_game_status(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        feed = self.get_game_feed(game_pk)

        game_data = coerce_mapping(
            feed.get("gameData")
        )

        return coerce_mapping(
            game_data.get("status")
        )

    def get_probable_pitchers(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        feed = self.get_game_feed(game_pk)

        game_data = coerce_mapping(
            feed.get("gameData")
        )

        probable = coerce_mapping(
            game_data.get("probablePitchers")
        )

        return {
            "game_pk": game_pk,
            "away": coerce_mapping(
                probable.get("away")
            ),
            "home": coerce_mapping(
                probable.get("home")
            ),
            "source": "MLB Stats API",
            "source_timestamp": utc_now().isoformat(),
        }

    def get_starting_lineups(
        self,
        game_pk: int,
    ) -> dict[str, Any]:
        boxscore = self.get_game_boxscore(
            game_pk
        )

        teams = coerce_mapping(
            boxscore.get("teams")
        )

        away = coerce_mapping(
            teams.get("away")
        )

        home = coerce_mapping(
            teams.get("home")
        )

        return {
            "game_pk": game_pk,
            "away": {
                "team": coerce_mapping(
                    away.get("team")
                ),
                "batters": list(
                    away.get("batters", [])
                ),
                "batting_order": list(
                    away.get("battingOrder", [])
                ),
                "players": coerce_mapping(
                    away.get("players")
                ),
            },
            "home": {
                "team": coerce_mapping(
                    home.get("team")
                ),
                "batters": list(
                    home.get("batters", [])
                ),
                "batting_order": list(
                    home.get("battingOrder", [])
                ),
                "players": coerce_mapping(
                    home.get("players")
                ),
            },
            "source": "MLB Stats API",
            "source_timestamp": utc_now().isoformat(),
        }

    # ========================================================
    # SECTION 18 - VENUE ENDPOINTS
    # ========================================================

    def get_venue(
        self,
        venue_id: int,
        *,
        hydrate: str | None = None,
    ) -> dict[str, Any]:
        params = {}

        if hydrate:
            params["hydrate"] = hydrate

        payload = self.request_json(
            f"venues/{venue_id}",
            params=params,
            required_keys=("venues",),
            cache_ttl_seconds=3600,
        ).data

        venues = coerce_list(
            payload.get("venues")
        )

        return venues[0] if venues else {}

    def get_venues(
        self,
    ) -> list[dict[str, Any]]:
        payload = self.request_json(
            "venues",
            required_keys=("venues",),
            cache_ttl_seconds=3600,
        ).data

        return coerce_list(
            payload.get("venues")
        )

    # ========================================================
    # SECTION 19 - LEAGUE LEADERS
    # ========================================================

    def get_league_leaders(
        self,
        *,
        leader_categories: Sequence[str] | str,
        season: int = DEFAULT_SEASON,
        group: str = "hitting",
        league_ids: Sequence[int] = (103, 104),
        limit: int = 50,
        player_pool: str = "qualified",
    ) -> dict[str, Any]:
        categories = (
            leader_categories
            if isinstance(
                leader_categories,
                str,
            )
            else ",".join(
                str(category)
                for category in leader_categories
            )
        )

        return self.request_json(
            "stats/leaders",
            params={
                "leaderCategories": categories,
                "season": season,
                "statGroup": group,
                "leagueIds": ",".join(
                    str(league_id)
                    for league_id in league_ids
                ),
                "limit": limit,
                "playerPool": player_pool,
            },
            required_keys=("leagueLeaders",),
            cache_ttl_seconds=300,
        ).data

    # ========================================================
    # SECTION 20 - REFERENCE ENDPOINTS
    # ========================================================

    def get_standings(
        self,
        season: int = DEFAULT_SEASON,
    ) -> dict[str, Any]:
        return self.request_json(
            "standings",
            params={
                "leagueId": "103,104",
                "season": season,
                "standingsTypes": (
                    "regularSeason"
                ),
            },
            cache_ttl_seconds=300,
        ).data

    def get_divisions(
        self,
    ) -> list[dict[str, Any]]:
        payload = self.request_json(
            "divisions",
            params={
                "sportId": DEFAULT_SPORT_ID,
            },
            required_keys=("divisions",),
            cache_ttl_seconds=3600,
        ).data

        return coerce_list(
            payload.get("divisions")
        )

    def get_leagues(
        self,
    ) -> list[dict[str, Any]]:
        payload = self.request_json(
            "league",
            params={
                "sportId": DEFAULT_SPORT_ID,
            },
            required_keys=("leagues",),
            cache_ttl_seconds=3600,
        ).data

        return coerce_list(
            payload.get("leagues")
        )

    def get_transactions(
        self,
        start_date: str,
        end_date: str,
        team_id: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "sportId": DEFAULT_SPORT_ID,
            "startDate": start_date,
            "endDate": end_date,
        }

        if team_id is not None:
            params["teamId"] = team_id

        return self.request_json(
            "transactions",
            params=params,
            cache_ttl_seconds=120,
        ).data

    # ========================================================
    # SECTION 21 - HUMAN-FRIENDLY HELPERS
    # ========================================================

    def summarize_teams(
        self,
        season: int = DEFAULT_SEASON,
    ) -> list[dict[str, Any]]:
        return [
            {
                "team_id": team.get("id"),
                "name": team.get("name"),
                "abbreviation": team.get(
                    "abbreviation"
                ),
                "league": coerce_mapping(
                    team.get("league")
                ).get("name"),
                "division": coerce_mapping(
                    team.get("division")
                ).get("name"),
                "venue": coerce_mapping(
                    team.get("venue")
                ).get("name"),
            }
            for team in self.get_teams(
                season
            )
        ]

    def summarize_roster(
        self,
        team_id: int,
        season: int = DEFAULT_SEASON,
        roster_type: str = "active",
    ) -> list[dict[str, Any]]:
        return [
            {
                "player_id": coerce_mapping(
                    item.get("person")
                ).get("id"),
                "name": coerce_mapping(
                    item.get("person")
                ).get("fullName"),
                "position": coerce_mapping(
                    item.get("position")
                ).get("name"),
                "position_code": coerce_mapping(
                    item.get("position")
                ).get("code"),
                "jersey_number": item.get(
                    "jerseyNumber"
                ),
                "status": coerce_mapping(
                    item.get("status")
                ).get("description"),
            }
            for item in self.get_team_roster(
                team_id,
                season,
                roster_type,
            )
        ]

    # ========================================================
    # SECTION 22 - CAPABILITY REPORT
    # ========================================================

    def capability_report(
        self,
    ) -> dict[str, Any]:
        return {
            "source": "MLB Stats API",
            "client_name": CLIENT_NAME,
            "client_version": CLIENT_VERSION,
            "phase": CLIENT_PHASE,
            "status": CLIENT_STATUS,
            "base_url": self.base_url,
            "live_base_url": self.live_base_url,
            "features": {
                "timeouts": True,
                "retry_policy": True,
                "exponential_backoff": True,
                "status_code_validation": True,
                "json_validation": True,
                "pagination_support": True,
                "request_metrics": True,
                "source_timestamps": True,
                "structured_errors": True,
                "rate_limit_awareness": True,
                "response_caching": True,
            },
            "required_endpoints": {
                "get_teams": callable(
                    getattr(self, "get_teams", None)
                ),
                "get_team": callable(
                    getattr(self, "get_team", None)
                ),
                "get_team_roster": callable(
                    getattr(self, "get_team_roster", None)
                ),
                "search_players": callable(
                    getattr(self, "search_players", None)
                ),
                "get_player": callable(
                    getattr(self, "get_player", None)
                ),
                "get_player_current_team": callable(
                    getattr(
                        self,
                        "get_player_current_team",
                        None,
                    )
                ),
                "get_player_season_hitting_stats": callable(
                    getattr(
                        self,
                        "get_player_season_hitting_stats",
                        None,
                    )
                ),
                "get_player_season_pitching_stats": callable(
                    getattr(
                        self,
                        "get_player_season_pitching_stats",
                        None,
                    )
                ),
                "get_player_game_logs": callable(
                    getattr(
                        self,
                        "get_player_game_logs",
                        None,
                    )
                ),
                "get_player_splits": callable(
                    getattr(
                        self,
                        "get_player_splits",
                        None,
                    )
                ),
                "get_schedule": callable(
                    getattr(self, "get_schedule", None)
                ),
                "get_game": callable(
                    getattr(self, "get_game", None)
                ),
                "get_probable_pitchers": callable(
                    getattr(
                        self,
                        "get_probable_pitchers",
                        None,
                    )
                ),
                "get_starting_lineups": callable(
                    getattr(
                        self,
                        "get_starting_lineups",
                        None,
                    )
                ),
                "get_game_status": callable(
                    getattr(
                        self,
                        "get_game_status",
                        None,
                    )
                ),
                "get_venue": callable(
                    getattr(self, "get_venue", None)
                ),
                "get_league_leaders": callable(
                    getattr(
                        self,
                        "get_league_leaders",
                        None,
                    )
                ),
            },
            "request_metrics": self.request_metrics(),
            "cache": {
                "enabled": self.settings.cache_enabled,
                "ttl_seconds": (
                    self.settings.cache_ttl_seconds
                ),
                "max_entries": (
                    self.settings.cache_max_entries
                ),
                "current_entries": self.cache.size(),
            },
        }


# ============================================================
# SECTION 23 - VALIDATION
# ============================================================

def validate_mlb_stats_api_client(
) -> dict[str, Any]:
    client = MLBStatsAPIClient()

    required_methods = (
        "get_teams",
        "get_team",
        "get_team_roster",
        "search_players",
        "get_player",
        "get_player_current_team",
        "get_player_season_hitting_stats",
        "get_player_season_pitching_stats",
        "get_player_game_logs",
        "get_player_splits",
        "get_schedule",
        "get_game",
        "get_probable_pitchers",
        "get_starting_lineups",
        "get_game_status",
        "get_venue",
        "get_league_leaders",
    )

    checks = {
        method_name: callable(
            getattr(client, method_name, None)
        )
        for method_name in required_methods
    }

    checks.update({
        "settings_valid": True,
        "timeouts_configured": (
            client.timeout[0] > 0
            and client.timeout[1] > 0
        ),
        "retry_policy_configured": (
            client.settings.max_retries >= 0
        ),
        "backoff_configured": (
            client.settings.backoff_factor >= 0
        ),
        "cache_available": (
            client.cache is not None
        ),
        "metrics_available": callable(
            client.request_metrics
        ),
        "structured_error_contract": (
            isinstance(
                MLBStatsAPIError(
                    "test"
                ).to_dict(),
                dict,
            )
        ),
        "pagination_available": callable(
            client.paginate
        ),
        "source_timestamp_contract": (
            SourceResponse(
                data={},
                source="MLB Stats API",
                source_url="https://example.com",
                source_timestamp=utc_now().isoformat(),
                request_id="test",
                status_code=200,
                elapsed_ms=1.0,
                from_cache=False,
                attempts=1,
                headers={},
            ).source_timestamp
            is not None
        ),
    })

    passed = sum(
        1
        for value in checks.values()
        if value
    )

    return {
        "status": (
            "ok"
            if passed == len(checks)
            else "failed"
        ),
        "client": CLIENT_NAME,
        "version": CLIENT_VERSION,
        "phase": CLIENT_PHASE,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "failed_checks": [
            name
            for name, value in checks.items()
            if not value
        ],
        "capability_report": (
            client.capability_report()
        ),
    }


# ============================================================
# SECTION 24 - PUBLIC EXPORTS
# ============================================================

__all__ = [
    "CLIENT_NAME",
    "CLIENT_VERSION",
    "CLIENT_PHASE",
    "CLIENT_PATH",
    "CLIENT_STATUS",

    "MLB_API_BASE_URL",
    "MLB_LIVE_BASE_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_CONNECT_TIMEOUT",
    "DEFAULT_READ_TIMEOUT",
    "DEFAULT_SPORT_ID",
    "DEFAULT_SEASON",

    "SourceHealth",
    "RequestOutcome",
    "CacheOutcome",

    "MLBStatsAPIError",
    "MLBStatsAPITimeoutError",
    "MLBStatsAPIConnectionError",
    "MLBStatsAPIHTTPError",
    "MLBStatsAPIRateLimitError",
    "MLBStatsAPIJSONError",
    "MLBStatsAPIValidationError",
    "MLBStatsAPIPaginationError",

    "MLBStatsAPISettings",
    "RequestMetrics",
    "SourceResponse",
    "CacheEntry",
    "ResponseCache",

    "MLBStatsAPIClient",
    "validate_mlb_stats_api_client",
]


# ============================================================
# SECTION 25 - LOCAL VALIDATION ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    print(
        json.dumps(
            validate_mlb_stats_api_client(),
            indent=2,
            default=str,
        )
    )
