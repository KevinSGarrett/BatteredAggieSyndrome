from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from .contracts import RawSnapshot, SourceRecord
from .snapshots import RawSnapshotStore, request_identity_sha256


class CsvSourceAdapter:
    def __init__(self, source_id: str, dataset: str):
        self.source_id = source_id
        self.dataset = dataset

    def read(self, path: Path) -> tuple[SourceRecord, ...]:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return tuple(
                SourceRecord(self.source_id, self.dataset, index, dict(row))
                for index, row in enumerate(csv.DictReader(handle), start=1)
            )


class JsonSourceAdapter:
    def __init__(self, source_id: str, dataset: str):
        self.source_id = source_id
        self.dataset = dataset

    def read(self, path: Path) -> tuple[SourceRecord, ...]:
        value = json.loads(path.read_text(encoding="utf-8"))
        rows = value if isinstance(value, list) else [value]
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError("JSON source must contain object rows")
        return tuple(
            SourceRecord(self.source_id, self.dataset, index, dict(row))
            for index, row in enumerate(rows, start=1)
        )


@dataclass(frozen=True)
class AcquisitionRequest:
    source_id: str
    dataset: str
    source_uri: str
    method: str = "GET"
    identity_components: Mapping[str, Any] = field(default_factory=dict)
    extension: str = ".bin"

    @property
    def identity_sha256(self) -> str:
        return request_identity_sha256(
            self.source_id,
            self.dataset,
            self.method,
            self.source_uri,
            self.identity_components,
        )


@dataclass(frozen=True)
class FetchResponse:
    body: bytes
    status_code: int = 200
    headers: Mapping[str, str] = field(default_factory=dict)
    row_count: int = 0
    schema_fields: tuple[str, ...] = ()


class AcquisitionFailure(RuntimeError):
    def __init__(
        self,
        condition: str,
        message: str = "",
        *,
        retry_after_seconds: float | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message or condition)
        self.condition = condition
        self.retry_after_seconds = retry_after_seconds
        self.status_code = status_code


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    maximum_delay_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.base_delay_seconds < 0 or self.maximum_delay_seconds < 0:
            raise ValueError("retry delays must be non-negative")
        if self.base_delay_seconds > self.maximum_delay_seconds:
            raise ValueError("base retry delay exceeds maximum delay")

    def delay_seconds(self, failed_attempt: int, retry_after_seconds: float | None) -> float:
        exponential = self.base_delay_seconds * (2 ** max(0, failed_attempt - 1))
        provider_delay = max(0.0, float(retry_after_seconds or 0.0))
        return min(self.maximum_delay_seconds, max(exponential, provider_delay))


Transport = Callable[[AcquisitionRequest], FetchResponse]


@dataclass(frozen=True)
class AcquisitionRoute:
    route_id: str
    request: AcquisitionRequest
    transport: Transport
    retry_conditions: frozenset[str] = frozenset(
        {"CONNECTION_ERROR", "RATE_LIMITED", "SERVER_ERROR", "TIMEOUT"}
    )
    fallback_conditions: frozenset[str] = frozenset()


@dataclass(frozen=True)
class AcquisitionResult:
    snapshot: RawSnapshot
    request_identity_sha256: str
    selected_route_id: str
    from_cache: bool
    attempt_evidence: tuple[Mapping[str, Any], ...]


def _header_value(headers: Mapping[str, str], name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return str(value)
    return None


def _response_failure(response: FetchResponse) -> AcquisitionFailure | None:
    status = int(response.status_code)
    if 200 <= status < 300:
        return None
    retry_after: float | None = None
    raw_retry_after = _header_value(response.headers, "Retry-After")
    if raw_retry_after is not None:
        try:
            retry_after = float(raw_retry_after)
        except ValueError:
            retry_after = None
    if status == 429:
        condition = "RATE_LIMITED"
    elif status in {408, 425}:
        condition = "TIMEOUT"
    elif 500 <= status < 600:
        condition = "SERVER_ERROR"
    else:
        condition = f"HTTP_{status}"
    return AcquisitionFailure(
        condition,
        f"acquisition response status {status}",
        retry_after_seconds=retry_after,
        status_code=status,
    )


class ResilientAcquirer:
    """Execute bounded retries, immutable caching, and explicit fallbacks.

    Transports receive credentials out of band. Only the credential-free public
    URI and declared identity components are retained in evidence.
    """

    def __init__(
        self,
        store: RawSnapshotStore,
        *,
        retry_policy: RetryPolicy | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.store = store
        self.retry_policy = retry_policy or RetryPolicy()
        self.sleeper = sleeper or __import__("time").sleep

    def acquire(self, routes: tuple[AcquisitionRoute, ...], *, retrieved_at: datetime) -> AcquisitionResult:
        if not routes:
            raise ValueError("at least one acquisition route is required")
        evidence: list[Mapping[str, Any]] = []
        failed_routes: list[str] = []
        terminal: AcquisitionFailure | None = None

        for route_index, route in enumerate(routes):
            request_identity = route.request.identity_sha256
            cached = self.store.lookup_request(request_identity)
            if cached is not None:
                evidence.append(
                    {
                        "attempt": 0,
                        "condition": "CACHE_HIT",
                        "request_identity_sha256": request_identity,
                        "route_id": route.route_id,
                    }
                )
                return AcquisitionResult(cached, request_identity, route.route_id, True, tuple(evidence))

            terminal = None
            for attempt in range(1, self.retry_policy.max_attempts + 1):
                try:
                    response = route.transport(route.request)
                    failure = _response_failure(response)
                    if failure is not None:
                        raise failure
                except AcquisitionFailure as failure:
                    terminal = failure
                except (ConnectionError, TimeoutError) as failure:
                    condition = "TIMEOUT" if isinstance(failure, TimeoutError) else "CONNECTION_ERROR"
                    terminal = AcquisitionFailure(condition, str(failure))
                except Exception as failure:
                    raise AcquisitionFailure("TRANSPORT_DEFECT", type(failure).__name__) from failure
                else:
                    metadata = {
                        "acquisition_attempts": tuple(evidence)
                        + (
                            {
                                "attempt": attempt,
                                "condition": "SUCCESS",
                                "request_identity_sha256": request_identity,
                                "route_id": route.route_id,
                            },
                        ),
                        "fallback_from_route_ids": tuple(failed_routes),
                        "request_identity_sha256": request_identity,
                        "selected_route_id": route.route_id,
                    }
                    snapshot = self.store.ingest_bytes(
                        route.request.source_id,
                        route.request.dataset,
                        response.body,
                        retrieved_at=retrieved_at,
                        source_uri=route.request.source_uri,
                        extension=route.request.extension,
                        row_count=response.row_count,
                        schema_fields=response.schema_fields,
                        metadata=metadata,
                    )
                    self.store.bind_request(request_identity, snapshot)
                    success = dict(metadata["acquisition_attempts"][-1])
                    evidence.append(success)
                    return AcquisitionResult(snapshot, request_identity, route.route_id, False, tuple(evidence))

                assert terminal is not None
                can_retry = terminal.condition in route.retry_conditions and attempt < self.retry_policy.max_attempts
                delay = (
                    self.retry_policy.delay_seconds(attempt, terminal.retry_after_seconds)
                    if can_retry
                    else 0.0
                )
                evidence.append(
                    {
                        "attempt": attempt,
                        "condition": terminal.condition,
                        "delay_seconds": delay,
                        "request_identity_sha256": request_identity,
                        "route_id": route.route_id,
                        "status_code": terminal.status_code,
                    }
                )
                if can_retry:
                    self.sleeper(delay)
                    continue
                break

            assert terminal is not None
            has_next_route = route_index + 1 < len(routes)
            if has_next_route and terminal.condition in route.fallback_conditions:
                failed_routes.append(route.route_id)
                continue
            raise terminal

        assert terminal is not None
        raise terminal
