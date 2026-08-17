from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import tempfile
import zipfile

FIXED = (1980, 1, 1, 0, 0, 0)
MANIFEST_SCHEMA = "aggie.backup.v2"
MANIFEST_FILE = "BACKUP_MANIFEST.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_safe_relpath(name: str) -> bool:
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        return False
    if "\\" in name:
        return False
    if len(name) > 1 and name[1] == ":":
        return False
    return True


def _validate_manifest_shape(manifest: dict) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError("backup manifest schema mismatch")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError("backup manifest entries missing")
    seen: set[str] = set()
    for entry in entries:
        rel = entry.get("path")
        if not isinstance(rel, str) or not _is_safe_relpath(rel):
            raise ValueError(f"unsafe manifest entry path: {rel!r}")
        if rel in seen:
            raise ValueError(f"duplicate manifest entry path: {rel}")
        seen.add(rel)
        if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
            raise ValueError(f"invalid manifest hash for {rel}")
        if int(entry.get("bytes", -1)) < 0:
            raise ValueError(f"invalid manifest byte count for {rel}")


def _load_policy(policy_path: Path | None) -> dict:
    path = policy_path or (Path(__file__).resolve().parents[3] / "configs/backup_retention_policy.json")
    return json.loads(path.read_text(encoding="utf-8"))


def enforce_backup_destination_policy(
    destination: Path,
    *,
    source_class: str,
    policy_path: Path | None = None,
    repo_root: Path | None = None,
) -> None:
    policy = _load_policy(policy_path)
    classes = {
        row["class"]: row
        for row in policy.get("classification_policy", {}).get("classes", [])
        if isinstance(row, dict) and "class" in row
    }
    row = classes.get(source_class)
    if row is None:
        raise ValueError(f"unknown backup source class: {source_class}")
    dest = destination.resolve()
    repo = (
        repo_root.resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[3]
    )
    if "repository_tracked_payloads" in row.get("prohibited_destinations", []):
        if dest == repo or repo in dest.parents:
            raise ValueError("restricted destination rejected: repository path forbidden")


def create_backup(source: Path, output_zip: Path) -> dict:
    source = Path(source).resolve()
    output_zip = Path(output_zip)
    if not source.is_dir():
        raise ValueError("backup source must be a directory")
    files = sorted(
        (p for p in source.rglob("*") if p.is_file()),
        key=lambda p: p.relative_to(source).as_posix(),
    )
    entries: list[dict] = []
    seen_relpaths: set[str] = set()
    for path in files:
        if path.is_symlink():
            raise ValueError("symlink backup members are not supported")
        rel = path.relative_to(source).as_posix()
        if not _is_safe_relpath(rel):
            raise ValueError(f"unsafe payload path: {rel}")
        if rel in seen_relpaths:
            raise ValueError(f"duplicate source member path: {rel}")
        seen_relpaths.add(rel)
        payload = path.read_bytes()
        entries.append(
            {
                "path": rel,
                "bytes": len(payload),
                "sha256": _sha(payload),
                "mode": oct(path.stat().st_mode & 0o777),
            }
        )
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_name": source.name,
        "entries": entries,
    }
    _validate_manifest_shape(manifest)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, entry in zip(files, entries):
            info = zipfile.ZipInfo(f"payload/{entry['path']}", FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
        manifest_info = zipfile.ZipInfo(MANIFEST_FILE, FIXED)
        manifest_info.compress_type = zipfile.ZIP_DEFLATED
        manifest_info.external_attr = 0o644 << 16
        archive.writestr(
            manifest_info,
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
    return manifest


def verify_backup(backup_zip: Path) -> dict:
    backup_zip = Path(backup_zip)
    archive_sha256 = _sha(backup_zip.read_bytes())
    with zipfile.ZipFile(backup_zip) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP member names are not allowed")
        for info in infos:
            if not _is_safe_relpath(info.filename):
                raise ValueError(f"unsafe backup member: {info.filename}")
        if MANIFEST_FILE not in names:
            raise ValueError("backup manifest missing")
        manifest = json.loads(archive.read(MANIFEST_FILE))
        _validate_manifest_shape(manifest)
        expected_payload = {f"payload/{row['path']}": row for row in manifest["entries"]}
        actual_payload = {
            info.filename for info in infos if info.filename.startswith("payload/") and not info.is_dir()
        }
        if actual_payload != set(expected_payload):
            raise ValueError("backup payload/manifest coverage mismatch")
        allowed_members = set(expected_payload) | {MANIFEST_FILE}
        unexpected = set(names) - allowed_members
        if unexpected:
            raise ValueError(f"unexpected backup members present: {sorted(unexpected)!r}")
        for name, row in expected_payload.items():
            data = archive.read(name)
            if len(data) != int(row["bytes"]) or _sha(data) != row["sha256"]:
                raise ValueError(f"backup integrity mismatch: {name}")
    manifest = dict(manifest)
    manifest["archive_sha256"] = archive_sha256
    manifest["content_identity"] = _sha(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    return manifest


def restore_backup(backup_zip: Path, destination: Path, *, require_empty: bool = True) -> dict:
    manifest = verify_backup(backup_zip)
    destination = Path(destination)
    if destination.exists() and require_empty and any(destination.iterdir()):
        raise ValueError("restore destination must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(backup_zip) as archive:
        for entry in manifest["entries"]:
            rel = PurePosixPath(entry["path"])
            target = (destination / Path(*rel.parts)).resolve()
            if root != target and root not in target.parents:
                raise ValueError("unsafe restore target")
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".restore.")
            os.close(fd)
            Path(tmp).write_bytes(archive.read(f"payload/{entry['path']}"))
            os.replace(tmp, target)
    return manifest
