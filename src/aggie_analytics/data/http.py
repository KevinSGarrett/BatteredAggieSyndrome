from __future__ import annotations

"""Credential-free public HTTP transport for immutable source assets."""

import urllib.error
import urllib.request
from dataclasses import dataclass

from .adapters import AcquisitionFailure, AcquisitionRequest, FetchResponse


@dataclass(frozen=True)
class PublicHTTPTransport:
    timeout_seconds: float = 180.0
    user_agent: str = "AggieAnalyticsEngine-private-research/1.0"

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout must be positive")

    def __call__(self, request: AcquisitionRequest) -> FetchResponse:
        wire_request = urllib.request.Request(
            request.source_uri,
            headers={"Accept": "application/octet-stream", "User-Agent": self.user_agent},
            method=request.method,
        )
        try:
            with urllib.request.urlopen(wire_request, timeout=self.timeout_seconds) as response:
                return FetchResponse(
                    body=response.read(),
                    status_code=int(response.status),
                    headers={
                        key: value
                        for key, value in response.headers.items()
                        if key.lower() in {"content-length", "content-type", "etag", "last-modified", "retry-after"}
                    },
                )
        except urllib.error.HTTPError as error:
            return FetchResponse(
                body=error.read(),
                status_code=int(error.code),
                headers={
                    key: value
                    for key, value in error.headers.items()
                    if key.lower() in {"content-length", "content-type", "etag", "last-modified", "retry-after"}
                },
            )
        except TimeoutError as error:
            raise AcquisitionFailure("TIMEOUT", "public asset request timed out") from error
        except urllib.error.URLError as error:
            raise AcquisitionFailure("CONNECTION_ERROR", "public asset connection failed") from error
