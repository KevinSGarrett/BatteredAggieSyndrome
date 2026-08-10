from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Mapping


class RegistryArtifactError(RuntimeError):
    """A canonical registry manifest or external payload failed validation."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class CoreRegistryArtifactManifest:
    schema_version: str
    dataset_version: str
    external_relative_path: str
    sha256: str
    bytes: int
    rows: int
    columns: int

    @classmethod
    def load(cls, path: Path) -> "CoreRegistryArtifactManifest":
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema_version") != "1.0.0":
            raise RegistryArtifactError("CORE_REGISTRY_MANIFEST_SCHEMA_UNSUPPORTED")
        if value.get("storage_boundary") != "EXTERNAL_CANONICAL_PAYLOAD":
            raise RegistryArtifactError("CORE_REGISTRY_STORAGE_BOUNDARY_UNSAFE")
        payload = value.get("payload")
        if not isinstance(payload, Mapping):
            raise RegistryArtifactError("CORE_REGISTRY_PAYLOAD_IDENTITY_MISSING")
        relative = payload.get("external_relative_path")
        digest = payload.get("sha256")
        integers = tuple(payload.get(key) for key in ("bytes", "rows", "columns"))
        if not isinstance(relative, str) or not relative:
            raise RegistryArtifactError("CORE_REGISTRY_RELATIVE_PATH_MISSING")
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise RegistryArtifactError("CORE_REGISTRY_SHA256_INVALID")
        if any(type(value) is not int or value <= 0 for value in integers):
            raise RegistryArtifactError("CORE_REGISTRY_DIMENSIONS_INVALID")
        relative_path = PurePosixPath(relative)
        if (
            "\\" in relative
            or ":" in relative
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.as_posix() != relative
        ):
            raise RegistryArtifactError("CORE_REGISTRY_RELATIVE_PATH_UNSAFE")
        if digest not in relative_path.parts:
            raise RegistryArtifactError("CORE_REGISTRY_PATH_NOT_CONTENT_ADDRESSED")
        return cls(
            schema_version=value["schema_version"],
            dataset_version=str(value.get("dataset_version", "")),
            external_relative_path=relative,
            sha256=digest,
            bytes=integers[0],
            rows=integers[1],
            columns=integers[2],
        )

    def resolve(self, data_root: Path) -> Path:
        root = data_root.resolve(strict=True)
        candidate = root.joinpath(*PurePosixPath(self.external_relative_path).parts)
        cursor = root
        for part in PurePosixPath(self.external_relative_path).parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise RegistryArtifactError("CORE_REGISTRY_PAYLOAD_PATH_UNSAFE")
        path = candidate.resolve(strict=True)
        if root not in path.parents or not path.is_file():
            raise RegistryArtifactError("CORE_REGISTRY_PAYLOAD_PATH_UNSAFE")
        return path

    def verify_payload(self, data_root: Path, *, verify_rows: bool = True) -> Path:
        path = self.resolve(data_root)
        if path.stat().st_size != self.bytes:
            raise RegistryArtifactError("CORE_REGISTRY_PAYLOAD_SIZE_MISMATCH")
        if _sha256(path) != self.sha256:
            raise RegistryArtifactError("CORE_REGISTRY_PAYLOAD_HASH_MISMATCH")
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise RegistryArtifactError("CORE_REGISTRY_PAYLOAD_EMPTY") from exc
            if len(header) != self.columns or len(header) != len(set(header)):
                raise RegistryArtifactError("CORE_REGISTRY_PAYLOAD_SCHEMA_MISMATCH")
            if verify_rows and sum(1 for _ in reader) != self.rows:
                raise RegistryArtifactError("CORE_REGISTRY_PAYLOAD_ROW_COUNT_MISMATCH")
        return path

    def verify_pointer(self, pointer_path: Path) -> None:
        with pointer_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 1:
            raise RegistryArtifactError("CORE_REGISTRY_POINTER_CARDINALITY_INVALID")
        row = rows[0]
        expected = {
            "schema_version": self.schema_version,
            "dataset_version": self.dataset_version,
            "record_type": "EXTERNAL_CANONICAL_PAYLOAD_MANIFEST",
            "data_root_env": "AGGIE_ANALYTICS_DATA_ROOT",
            "external_relative_path": self.external_relative_path,
            "sha256": self.sha256,
            "bytes": str(self.bytes),
            "rows": str(self.rows),
            "columns": str(self.columns),
            "eligibility": "CORE_REGISTRY",
        }
        if row != expected:
            raise RegistryArtifactError("CORE_REGISTRY_POINTER_IDENTITY_MISMATCH")

    def iter_rows(self, data_root: Path) -> Iterator[dict[str, Any]]:
        path = self.verify_payload(data_root)
        with path.open("r", encoding="utf-8", newline="") as handle:
            yield from csv.DictReader(handle)


@dataclass(frozen=True)
class PeopleRegistryArtifactManifest(CoreRegistryArtifactManifest):
    """Fail-closed manifest contract for the external canonical people registry."""

    @classmethod
    def load(cls, path: Path) -> "PeopleRegistryArtifactManifest":
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema_version") != "1.0.0":
            raise RegistryArtifactError("PEOPLE_REGISTRY_MANIFEST_SCHEMA_UNSUPPORTED")
        if value.get("storage_boundary") != "EXTERNAL_CANONICAL_PAYLOAD":
            raise RegistryArtifactError("PEOPLE_REGISTRY_STORAGE_BOUNDARY_UNSAFE")
        payload = value.get("payload")
        if not isinstance(payload, Mapping):
            raise RegistryArtifactError("PEOPLE_REGISTRY_PAYLOAD_IDENTITY_MISSING")
        relative = payload.get("external_relative_path")
        digest = payload.get("sha256")
        integers = tuple(payload.get(key) for key in ("bytes", "rows", "columns"))
        if not isinstance(relative, str) or not relative:
            raise RegistryArtifactError("PEOPLE_REGISTRY_RELATIVE_PATH_MISSING")
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise RegistryArtifactError("PEOPLE_REGISTRY_SHA256_INVALID")
        if any(type(item) is not int or item <= 0 for item in integers):
            raise RegistryArtifactError("PEOPLE_REGISTRY_DIMENSIONS_INVALID")
        relative_path = PurePosixPath(relative)
        if "\\" in relative or ":" in relative or relative_path.is_absolute() or ".." in relative_path.parts or relative_path.as_posix() != relative:
            raise RegistryArtifactError("PEOPLE_REGISTRY_RELATIVE_PATH_UNSAFE")
        if digest not in relative_path.parts:
            raise RegistryArtifactError("PEOPLE_REGISTRY_PATH_NOT_CONTENT_ADDRESSED")
        return cls(value["schema_version"], str(value.get("dataset_version", "")), relative, digest, *integers)

    def verify_pointer(self, pointer_path: Path) -> None:
        with pointer_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        expected = {
            "schema_version": self.schema_version,
            "dataset_version": self.dataset_version,
            "record_type": "EXTERNAL_CANONICAL_PAYLOAD_MANIFEST",
            "data_root_env": "AGGIE_ANALYTICS_DATA_ROOT",
            "external_relative_path": self.external_relative_path,
            "sha256": self.sha256,
            "bytes": str(self.bytes),
            "rows": str(self.rows),
            "columns": str(self.columns),
            "eligibility": "PEOPLE_REGISTRY",
        }
        if rows != [expected]:
            raise RegistryArtifactError("PEOPLE_REGISTRY_POINTER_IDENTITY_MISMATCH")
