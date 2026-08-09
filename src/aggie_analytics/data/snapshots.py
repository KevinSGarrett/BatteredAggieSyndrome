from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlsplit

from .contracts import RawSnapshot


_SENSITIVE_IDENTITY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "signature",
    "token",
)

_DEFAULT_SOURCE_POLICY_METADATA = {
    "private_research_use_allowed": True,
    "raw_publication_allowed": False,
    "rights_metadata_nonblocking": True,
    "storage_boundary": "EXTERNAL_DATA_ROOT",
}

_QUARANTINE_REASON_CODES = frozenset(
    {
        "CORRUPTED_RECORD",
        "FABRICATED_RECORD",
        "SCHEMA_INCOMPATIBLE",
        "MALWARE_SUSPECTED",
        "CREDENTIAL_EXPOSURE",
        "PRIVATE_PERSONAL_INFORMATION",
        "PIT_LEAKAGE",
        "TARGET_LEAKAGE",
        "RECONCILIATION_FAILURE",
        "MISSING_REQUIRED_PROVENANCE",
    }
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _contains_sensitive_name(value: str) -> bool:
    normalized = value.lower().replace("-", "_")
    return normalized in _SENSITIVE_IDENTITY_PARTS or any(
        normalized.endswith(f"_{part}") for part in _SENSITIVE_IDENTITY_PARTS
    )


def _safe_path_segment(value: str, field_name: str) -> str:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise ValueError(f"{field_name} must be one safe path segment")
    return value


def _validate_request_identity(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("request identity must be a lowercase SHA-256 digest")


def _validate_public_source_uri(source_uri: str) -> None:
    if not source_uri or not isinstance(source_uri, str):
        raise ValueError("source_uri must be a non-empty string")
    parsed = urlsplit(source_uri)
    if parsed.username or parsed.password:
        raise ValueError("source_uri must not contain credentials")
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if _contains_sensitive_name(key) and value.lower() not in {"", "redacted", "<redacted>"}:
            raise ValueError(f"source_uri contains sensitive query material: {key}")


def _validate_metadata_has_no_sensitive_keys(value: Any, path: str = "metadata") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if _contains_sensitive_name(key_text):
                raise ValueError(f"{path} contains sensitive key: {key_text}")
            _validate_metadata_has_no_sensitive_keys(item, f"{path}.{key_text}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_metadata_has_no_sensitive_keys(item, f"{path}[{index}]")


def _source_policy_metadata(value: Mapping[str, Any] | None) -> dict[str, Any]:
    policy = dict(_DEFAULT_SOURCE_POLICY_METADATA)
    policy.update(dict(value or {}))
    _validate_metadata_has_no_sensitive_keys(policy, "source_policy_metadata")
    if policy.get("private_research_use_allowed") is not True:
        raise ValueError("private research use must remain allowed for public factual data")
    if policy.get("raw_publication_allowed") is not False:
        raise ValueError("raw third-party publication must remain disabled")
    if policy.get("rights_metadata_nonblocking") is not True:
        raise ValueError("rights metadata must remain nonblocking for private research")
    if policy.get("storage_boundary") != "EXTERNAL_DATA_ROOT":
        raise ValueError("raw storage must remain under the configured external data root")
    return policy


def request_identity_sha256(
    source_id: str,
    dataset: str,
    method: str,
    source_uri: str,
    identity_components: Mapping[str, Any] | None = None,
) -> str:
    """Return a credential-free, deterministic source/request identity."""

    _validate_public_source_uri(source_uri)
    components = dict(identity_components or {})
    sensitive = sorted(str(key) for key in components if _contains_sensitive_name(str(key)))
    if sensitive:
        raise ValueError(f"request identity contains sensitive keys: {','.join(sensitive)}")
    payload = {
        "dataset": dataset,
        "identity_components": components,
        "method": method.upper(),
        "source_id": source_id,
        "source_uri": source_uri,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class RawSnapshotStore:
    """Content-addressed immutable raw store with immutable request bindings."""

    def __init__(self, root: Path):
        self.root = root

    def _install_immutable(self, destination: Path, payload: bytes, digest: str) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if _sha(destination) != digest:
                raise RuntimeError("immutable snapshot collision")
            return
        handle, temporary_name = tempfile.mkstemp(prefix=".incoming-", dir=destination.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError:
                if _sha(destination) != digest:
                    raise RuntimeError("immutable snapshot collision")
        finally:
            temporary.unlink(missing_ok=True)

    def _write_immutable_json(self, path: Path, record: Mapping[str, Any], collision: str) -> None:
        encoded = (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != encoded:
                raise RuntimeError(collision)
            return
        self._install_immutable(path, encoded, digest)

    def ingest_bytes(
        self,
        source_id: str,
        dataset: str,
        payload: bytes,
        *,
        retrieved_at: datetime,
        source_uri: str,
        extension: str = ".bin",
        publication_time: datetime | None = None,
        row_count: int = 0,
        schema_fields=(),
        metadata: Mapping[str, Any] | None = None,
        source_policy_metadata: Mapping[str, Any] | None = None,
    ) -> RawSnapshot:
        _validate_public_source_uri(source_uri)
        _validate_metadata_has_no_sensitive_keys(metadata or {})
        policy_metadata = _source_policy_metadata(source_policy_metadata)
        source_id = _safe_path_segment(source_id, "source_id")
        dataset = _safe_path_segment(dataset, "dataset")
        digest = hashlib.sha256(payload).hexdigest()
        suffix = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        if not suffix[1:] or not suffix[1:].replace("_", "").isalnum():
            raise ValueError("extension must contain only letters, numbers, or underscore")
        capture_identity = {
            "dataset": dataset,
            "publication_time": _iso(publication_time) if publication_time else None,
            "raw_sha256": digest,
            "retrieved_at": _iso(retrieved_at),
            "source_id": source_id,
            "source_uri": source_uri,
        }
        capture_digest = hashlib.sha256(
            json.dumps(capture_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        snapshot_id = f"snap_{capture_digest[:24]}"
        # Capture identity and content identity are deliberately distinct. A
        # later retrieval of identical bytes receives its own capture manifest
        # but reuses the exact content-addressed payload path.
        relative_path = Path("raw") / source_id / dataset / f"{digest}{suffix}"
        destination = self.root / relative_path
        self._install_immutable(destination, payload, digest)
        record = {
            "dataset": dataset,
            "metadata": dict(metadata or {}),
            "publication_time": _iso(publication_time) if publication_time else None,
            "raw_sha256": digest,
            "relative_path": relative_path.as_posix(),
            "retrieved_at": _iso(retrieved_at),
            "row_count": int(row_count),
            "schema_fields": list(schema_fields),
            "snapshot_id": snapshot_id,
            "source_id": source_id,
            "source_policy_metadata": policy_metadata,
            "source_uri": source_uri,
        }
        self._write_immutable_json(
            self.root / "manifests" / f"{snapshot_id}.json",
            record,
            "immutable manifest collision",
        )
        return self._snapshot_from_record(record)

    def ingest_file(
        self,
        source_id: str,
        dataset: str,
        input_path: Path,
        *,
        retrieved_at: datetime,
        source_uri: str,
        publication_time: datetime | None = None,
        row_count: int = 0,
        schema_fields=(),
        metadata=None,
        source_policy_metadata: Mapping[str, Any] | None = None,
    ) -> RawSnapshot:
        return self.ingest_bytes(
            source_id,
            dataset,
            input_path.read_bytes(),
            retrieved_at=retrieved_at,
            source_uri=source_uri,
            extension=input_path.suffix or ".bin",
            publication_time=publication_time,
            row_count=row_count,
            schema_fields=schema_fields,
            metadata=metadata,
            source_policy_metadata=source_policy_metadata,
        )

    def manifest_record(self, snapshot_id: str) -> dict[str, Any]:
        snapshot_id = _safe_path_segment(snapshot_id, "snapshot_id")
        manifest_path = self.root / "manifests" / f"{snapshot_id}.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"snapshot manifest not found: {snapshot_id}")
        record = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload_path = self.root / record["relative_path"]
        if not payload_path.is_file() or _sha(payload_path) != record["raw_sha256"]:
            raise RuntimeError("snapshot payload integrity failure")
        return record

    def ingest_correction(
        self,
        prior_snapshot_id: str,
        payload: bytes,
        *,
        retrieved_at: datetime,
        corrected_at: datetime,
        source_uri: str,
        correction_reason: str,
        extension: str = ".bin",
        publication_time: datetime | None = None,
        row_count: int = 0,
        schema_fields=(),
        metadata: Mapping[str, Any] | None = None,
        source_policy_metadata: Mapping[str, Any] | None = None,
    ) -> tuple[RawSnapshot, dict[str, Any]]:
        prior = self.manifest_record(prior_snapshot_id)
        reason = correction_reason.strip()
        if not reason:
            raise ValueError("correction_reason must be non-empty")
        if hashlib.sha256(payload).hexdigest() == prior["raw_sha256"]:
            raise ValueError("correction bytes must differ from the prior immutable content identity")
        corrected = self.ingest_bytes(
            prior["source_id"],
            prior["dataset"],
            payload,
            retrieved_at=retrieved_at,
            source_uri=source_uri,
            extension=extension,
            publication_time=publication_time,
            row_count=row_count,
            schema_fields=schema_fields,
            metadata=metadata,
            source_policy_metadata=source_policy_metadata or prior.get("source_policy_metadata"),
        )
        corrected_manifest_path = self.root / "manifests" / f"{corrected.snapshot_id}.json"
        prior_manifest_path = self.root / "manifests" / f"{prior_snapshot_id}.json"
        identity = {
            "corrected_at": _iso(corrected_at),
            "corrected_raw_sha256": corrected.raw_sha256,
            "corrected_snapshot_id": corrected.snapshot_id,
            "correction_reason": reason,
            "prior_raw_sha256": prior["raw_sha256"],
            "prior_snapshot_id": prior_snapshot_id,
        }
        correction_digest = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        correction_id = f"corr_{correction_digest[:24]}"
        record = {
            **identity,
            "correction_id": correction_id,
            "corrected_manifest_sha256": _sha(corrected_manifest_path),
            "prior_manifest_sha256": _sha(prior_manifest_path),
            "prior_snapshot_preserved": True,
            "relative_path": (Path("corrections") / prior["source_id"] / prior["dataset"] / f"{correction_id}.json").as_posix(),
            "schema_version": "1.0.0",
            "source_id": prior["source_id"],
            "dataset": prior["dataset"],
        }
        self._write_immutable_json(self.root / record["relative_path"], record, "immutable correction lineage collision")
        return corrected, record

    def quarantine_snapshot(
        self,
        snapshot_id: str,
        *,
        reason_code: str,
        quarantined_at: datetime,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        snapshot = self.manifest_record(snapshot_id)
        normalized_reason = reason_code.strip().upper()
        if normalized_reason not in _QUARANTINE_REASON_CODES:
            raise ValueError(f"unsupported quarantine reason: {normalized_reason}")
        safe_details = dict(details or {})
        _validate_metadata_has_no_sensitive_keys(safe_details, "quarantine.details")
        identity = {
            "details": safe_details,
            "quarantined_at": _iso(quarantined_at),
            "raw_sha256": snapshot["raw_sha256"],
            "reason_code": normalized_reason,
            "snapshot_id": snapshot_id,
        }
        quarantine_digest = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        quarantine_id = f"quar_{quarantine_digest[:24]}"
        record = {
            **identity,
            "dataset": snapshot["dataset"],
            "quarantine_id": quarantine_id,
            "raw_snapshot_preserved": True,
            "relative_path": (Path("quarantine") / snapshot["source_id"] / snapshot["dataset"] / f"{quarantine_id}.json").as_posix(),
            "schema_version": "1.0.0",
            "source_id": snapshot["source_id"],
            "unrelated_domains_globally_blocked": False,
        }
        self._write_immutable_json(self.root / record["relative_path"], record, "immutable quarantine record collision")
        return record

    def bind_request(self, request_identity: str, snapshot: RawSnapshot) -> None:
        _validate_request_identity(request_identity)
        record = {
            "dataset": snapshot.dataset,
            "raw_sha256": snapshot.raw_sha256,
            "request_identity_sha256": request_identity,
            "snapshot_id": snapshot.snapshot_id,
            "source_id": snapshot.source_id,
        }
        self._write_immutable_json(
            self.root / "request_cache" / request_identity[:2] / f"{request_identity}.json",
            record,
            "immutable request cache collision",
        )

    def lookup_request(self, request_identity: str) -> RawSnapshot | None:
        _validate_request_identity(request_identity)
        binding_path = self.root / "request_cache" / request_identity[:2] / f"{request_identity}.json"
        if not binding_path.exists():
            return None
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        if binding.get("request_identity_sha256") != request_identity:
            raise RuntimeError("request cache identity mismatch")
        manifest_path = self.root / "manifests" / f"{binding['snapshot_id']}.json"
        if not manifest_path.exists():
            raise RuntimeError("request cache snapshot manifest missing")
        record = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload_path = self.root / record["relative_path"]
        if not payload_path.exists() or _sha(payload_path) != record["raw_sha256"]:
            raise RuntimeError("request cache payload integrity failure")
        if binding.get("raw_sha256") != record["raw_sha256"]:
            raise RuntimeError("request cache binding integrity failure")
        return self._snapshot_from_record(record)

    @staticmethod
    def _snapshot_from_record(record: Mapping[str, Any]) -> RawSnapshot:
        metadata = dict(record.get("metadata", {}))
        if "source_policy_metadata" in record:
            metadata["source_policy"] = dict(record["source_policy_metadata"])
        return RawSnapshot(
            str(record["snapshot_id"]),
            str(record["source_id"]),
            str(record["dataset"]),
            _parse_iso(str(record["retrieved_at"])),
            str(record["raw_sha256"]),
            str(record["relative_path"]),
            int(record["row_count"]),
            tuple(record["schema_fields"]),
            str(record["source_uri"]),
            _parse_iso(record.get("publication_time")),
            metadata,
        )
