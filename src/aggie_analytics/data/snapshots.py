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
    ) -> RawSnapshot:
        _validate_public_source_uri(source_uri)
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
        relative_path = Path("raw") / source_id / dataset / f"{snapshot_id}{suffix}"
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
        )

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
            dict(record.get("metadata", {})),
        )
