from __future__ import annotations

"""Credential-safe CollegeFootballData REST acquisition helpers."""

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .adapters import AcquisitionFailure, AcquisitionRequest, FetchResponse


CFBD_BASE_URL = "https://api.collegefootballdata.com"


def load_dotenv_value(path: Path, name: str) -> str:
    """Load one nonempty dotenv value without returning any unrelated secret."""

    if not path.is_file():
        raise FileNotFoundError(f"authoritative dotenv file is absent: {path}")
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        resolved = value.strip()
        if len(resolved) >= 2 and resolved[0] == resolved[-1] and resolved[0] in {"'", '"'}:
            resolved = resolved[1:-1]
        if not resolved:
            raise RuntimeError(f"{name} is configured but empty")
        return resolved
    raise RuntimeError(f"{name} is not configured in the authoritative dotenv file")


def public_uri(path: str, parameters: Mapping[str, Any]) -> str:
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("CFBD endpoint path must be one absolute API path")
    query = urllib.parse.urlencode(
        [(str(key), str(value).lower() if isinstance(value, bool) else str(value))
         for key, value in sorted(parameters.items()) if value is not None]
    )
    return f"{CFBD_BASE_URL}{path}" + (f"?{query}" if query else "")


def inspect_json_rows(body: bytes) -> tuple[int, tuple[str, ...]]:
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "CFBD response is not valid JSON") from error
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise AcquisitionFailure("SCHEMA_INCOMPATIBLE", "CFBD response must be a JSON object array")
    fields = tuple(sorted({str(key) for row in value for key in row}))
    return len(value), fields


def acquisition_request(
    *, endpoint_id: str, path: str, parameters: Mapping[str, Any], run_id: str
) -> AcquisitionRequest:
    uri = public_uri(path, parameters)
    return AcquisitionRequest(
        source_id="SRC-002",
        dataset=endpoint_id,
        source_uri=uri,
        identity_components={
            "endpoint_id": endpoint_id,
            "parameters": dict(sorted(parameters.items())),
            "run_id": run_id,
        },
        extension=".json",
    )


@dataclass(frozen=True)
class CFBDTransport:
    access_token: str = field(repr=False)
    timeout_seconds: float = 90.0
    user_agent: str = "AggieAnalyticsEngine-private-research/1.0"

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError("CFBD access token must be nonempty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout must be positive")

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        wire_request = urllib.request.Request(
            request.source_uri,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent,
            },
            method=request.method,
        )
        try:
            with urllib.request.urlopen(wire_request, timeout=self.timeout_seconds) as response:
                body = response.read()
                status = int(response.status)
                headers = {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower() in {"content-type", "retry-after", "x-ratelimit-limit", "x-ratelimit-remaining"}
                }
        except urllib.error.HTTPError as error:
            body = error.read()
            return FetchResponse(
                body=body,
                status_code=int(error.code),
                headers={
                    key: value
                    for key, value in error.headers.items()
                    if key.lower() in {"content-type", "retry-after", "x-ratelimit-limit", "x-ratelimit-remaining"}
                },
            )
        except TimeoutError as error:
            raise AcquisitionFailure("TIMEOUT", "CFBD request timed out") from error
        except urllib.error.URLError as error:
            raise AcquisitionFailure("CONNECTION_ERROR", "CFBD connection failed") from error
        if not 200 <= status < 300:
            return FetchResponse(body=body, status_code=status, headers=headers)
        row_count, fields = inspect_json_rows(body)
        return FetchResponse(
            body=body,
            status_code=status,
            headers=headers,
            row_count=row_count,
            schema_fields=fields,
        )
