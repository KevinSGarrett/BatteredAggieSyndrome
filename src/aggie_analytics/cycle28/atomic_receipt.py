"""Atomic source-acquisition versus derivative-observation receipts.

A caller-supplied execution time, filesystem mtime, or later observation of a
pre-existing local file never proves source acquisition.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

SOURCE_ACQUISITION_RECEIPT = "SOURCE_ACQUISITION_RECEIPT"
DERIVATIVE_OBSERVATION_RECEIPT = "DERIVATIVE_OBSERVATION_RECEIPT"
RECEIPT_SCHEMA_VERSION = "aggie.cycle28.source_acquisition_receipt.v1"


class AtomicReceiptError(ValueError):
    """Raised when a receipt cannot be admitted as source acquisition."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def trusted_clock_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def request_identity_sha256(
    *,
    method: str,
    uri: str,
    parameters: Mapping[str, Any] | None = None,
) -> str:
    payload = {
        "method": str(method).upper(),
        "parameters": dict(parameters or {}),
        "uri": str(uri),
    }
    return sha256_bytes(canonical_json_bytes(payload))


def classify_cycle27_receipt(payload: Mapping[str, Any]) -> str:
    """Predecessor Cycle #27 receipts are derivative observations."""

    if payload.get("pin_field_retrieved_at_is_not_authority") is True:
        return DERIVATIVE_OBSERVATION_RECEIPT
    if payload.get("artifact_type") == "WEEK1_OFFICIAL_FINAL_ACQUISITION_RECEIPT":
        if not payload.get("request_identity_sha256"):
            return DERIVATIVE_OBSERVATION_RECEIPT
        if not payload.get("network_response_status"):
            return DERIVATIVE_OBSERVATION_RECEIPT
    kind = str(payload.get("receipt_kind") or "")
    if kind == SOURCE_ACQUISITION_RECEIPT:
        return SOURCE_ACQUISITION_RECEIPT
    if kind == DERIVATIVE_OBSERVATION_RECEIPT:
        return DERIVATIVE_OBSERVATION_RECEIPT
    return DERIVATIVE_OBSERVATION_RECEIPT


def reject_caller_supplied_retrieval_time(
    *,
    trusted_retrieval_utc: str,
    caller_execution_time_utc: str | None,
) -> None:
    if caller_execution_time_utc and caller_execution_time_utc != trusted_retrieval_utc:
        raise AtomicReceiptError(
            "caller-supplied execution time cannot be used as source retrieval time"
        )


def reject_filesystem_mtime_authority(mtime_utc: str | None, retrieval_utc: str) -> None:
    if mtime_utc and mtime_utc == retrieval_utc:
        raise AtomicReceiptError("filesystem mtime cannot be used as source authority")


def _fsync_directory(path: Path) -> None:
    try:
        handle = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(handle)
    except OSError:
        return
    finally:
        os.close(handle)


def write_atomic_source_acquisition(
    *,
    data_root: Path,
    raw_relative_dir: str,
    receipt_relative_dir: str,
    raw_bytes: bytes,
    receipt_fields: Mapping[str, Any],
) -> dict[str, Any]:
    """Write raw bytes and receipt in one directory transaction.

    Both files are written to a temporary directory and renamed into the
    content-addressed destinations only after both exist. Partial writes never
    become admitted receipts.
    """

    if not raw_bytes:
        raise AtomicReceiptError("empty raw response cannot be a source acquisition")
    required = (
        "request_identity_sha256",
        "source_uri",
        "route_id",
        "network_response_status",
        "acquisition_started_at_utc",
        "acquisition_ended_at_utc",
        "trusted_clock_retrieval_utc",
        "process_identity",
    )
    missing = [key for key in required if not receipt_fields.get(key)]
    if missing:
        raise AtomicReceiptError(f"missing source-acquisition fields: {missing}")
    if receipt_fields.get("receipt_kind") != SOURCE_ACQUISITION_RECEIPT:
        raise AtomicReceiptError("receipt_kind must be SOURCE_ACQUISITION_RECEIPT")
    start = parse_utc(str(receipt_fields["acquisition_started_at_utc"]))
    end = parse_utc(str(receipt_fields["acquisition_ended_at_utc"]))
    retrieved = parse_utc(str(receipt_fields["trusted_clock_retrieval_utc"]))
    if start is None or end is None or retrieved is None:
        raise AtomicReceiptError("acquisition timestamps must be timezone-aware UTC")
    if end < start:
        raise AtomicReceiptError("acquisition ended before it started")
    raw_digest = sha256_bytes(raw_bytes)
    payload = {
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "raw_bytes": len(raw_bytes),
        "raw_sha256": raw_digest,
        **dict(receipt_fields),
    }
    payload["pin_field_retrieved_at_is_not_authority"] = False
    payload["filesystem_mtime_is_not_authority"] = True
    payload["caller_execution_time_is_not_authority"] = True
    body = canonical_json_bytes(payload)
    receipt_digest = sha256_bytes(body)
    raw_dir = data_root / raw_relative_dir.replace("\\", "/")
    receipt_dir = data_root / receipt_relative_dir.replace("\\", "/") / "sha256" / receipt_digest
    raw_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    raw_name = f"{raw_digest}.html"
    receipt_name = "source_acquisition_receipt.json"
    staging_parent = data_root / ".cycle28_atomic_staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f"atomic-{uuid4().hex}-", dir=str(staging_parent))
    )
    try:
        staged_raw = staging / raw_name
        staged_receipt = staging / receipt_name
        with staged_raw.open("wb") as handle:
            handle.write(raw_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        with staged_receipt.open("wb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(staging)
        final_raw = raw_dir / raw_name
        final_receipt = receipt_dir / receipt_name
        os.replace(staged_raw, final_raw)
        os.replace(staged_receipt, final_receipt)
        _fsync_directory(raw_dir)
        _fsync_directory(receipt_dir)
    finally:
        for leftover in staging.glob("*"):
            leftover.unlink(missing_ok=True)
        staging.rmdir()
    raw_relative = str(final_raw.relative_to(data_root)).replace("\\", "/")
    receipt_relative = str(final_receipt.relative_to(data_root)).replace("\\", "/")
    return {
        "raw_relative_path": raw_relative,
        "raw_sha256": raw_digest,
        "raw_bytes": len(raw_bytes),
        "receipt_relative_path": receipt_relative,
        "receipt_sha256": receipt_digest,
        "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
        "request_identity_sha256": receipt_fields["request_identity_sha256"],
        "route_id": receipt_fields["route_id"],
        "trusted_clock_retrieval_utc": receipt_fields["trusted_clock_retrieval_utc"],
        "transport_is_not_result_authority": bool(
            receipt_fields.get("transport_is_not_result_authority", False)
        ),
    }


def write_acquisition_failure(
    *,
    data_root: Path,
    receipt_relative_dir: str,
    receipt_fields: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
        "acquisition_failed": True,
        "does_not_admit_local_file_as_newly_acquired": True,
        **dict(receipt_fields),
    }
    body = canonical_json_bytes(payload)
    digest = sha256_bytes(body)
    posix_dir = receipt_relative_dir.replace("\\", "/")
    relative = f"{posix_dir}/sha256/{digest}/source_acquisition_failure.json"
    path = data_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {
        "receipt_kind": SOURCE_ACQUISITION_RECEIPT,
        "receipt_relative_path": relative,
        "receipt_sha256": digest,
        "acquisition_failed": True,
    }


def write_derivative_observation_receipt(
    *,
    data_root: Path,
    receipt_relative_dir: str,
    fields: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "receipt_kind": DERIVATIVE_OBSERVATION_RECEIPT,
        "pin_field_retrieved_at_is_not_authority": True,
        "filesystem_mtime_is_not_authority": True,
        "does_not_prove_source_acquisition": True,
        **dict(fields),
    }
    body = canonical_json_bytes(payload)
    digest = sha256_bytes(body)
    posix_dir = receipt_relative_dir.replace("\\", "/")
    relative = f"{posix_dir}/sha256/{digest}/derivative_observation_receipt.json"
    path = data_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return {
        "receipt_kind": DERIVATIVE_OBSERVATION_RECEIPT,
        "receipt_relative_path": relative,
        "receipt_sha256": digest,
    }
