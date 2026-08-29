"""Offline reconstruction guards shared by the deterministic season-index suites.

A mounted data root means the immutable lake is available for reconstruction. It has
never meant that a test may open a socket, and treating the two as the same thing is
what made three suites fail whenever an official host rotated or expired a certificate.
The predicates here keep the two facts apart, and the fixture helper fails closed with
a specific reason instead of falling back to a live fetch.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from aggie_analytics.data.tamu_official_historical_archive import AuthorityViolation

NETWORK_FORBIDDEN_ENV = "AGGIE_ANALYTICS_NETWORK_FORBIDDEN"
LAKE_ONLY_ENV = "AGGIE_ANALYTICS_RECONSTRUCT_FROM_LAKE_ONLY"
DATA_ROOT_ENV = "AGGIE_ANALYTICS_DATA_ROOT"

FIXTURE_MISSING = "OFFLINE_FIXTURE_MISSING"
FIXTURE_HASH_DRIFT = "OFFLINE_FIXTURE_HASH_DRIFT"
NETWORK_NOT_PERMITTED = "NETWORK_ACCESS_NOT_PERMITTED_IN_THIS_CONTEXT"


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def network_forbidden() -> bool:
    return env_truthy(NETWORK_FORBIDDEN_ENV)


def reconstruct_from_lake_only() -> bool:
    return env_truthy(LAKE_ONLY_ENV)


def data_root_is_mounted() -> bool:
    """A mounted lake authorizes reconstruction, never acquisition."""

    configured = os.environ.get(DATA_ROOT_ENV, "").strip()
    return bool(configured) and Path(configured).is_dir()


def assert_network_permitted(context: str) -> None:
    """Refuse a live fetch from any context that must stay deterministic."""

    if network_forbidden():
        raise AuthorityViolation(f"{NETWORK_NOT_PERMITTED}: {context} (network forbidden)")
    if reconstruct_from_lake_only():
        raise AuthorityViolation(f"{NETWORK_NOT_PERMITTED}: {context} (lake-only reconstruction)")


def require_fixture(path: Path, *, expected_sha256: str | None, description: str) -> bytes:
    """Read an immutable capture, failing closed on absence or hash drift."""

    resolved = Path(path)
    if not resolved.is_file():
        raise AuthorityViolation(f"{FIXTURE_MISSING}: {description} at {resolved}")
    body = resolved.read_bytes()
    if expected_sha256:
        observed = hashlib.sha256(body).hexdigest()
        if observed != expected_sha256:
            raise AuthorityViolation(
                f"{FIXTURE_HASH_DRIFT}: {description} expected {expected_sha256} observed {observed}"
            )
    return body
