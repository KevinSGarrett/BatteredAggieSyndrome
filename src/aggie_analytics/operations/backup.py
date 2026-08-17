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


def _normalize_relpath(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("path must be a string")
    raw = name.strip()
    if not raw:
        raise ValueError("path cannot be empty")
    if "\\" in raw:
        raise ValueError(f"unsafe path separator alias: {name!r}")
    if raw.startswith("/"):
        raise ValueError(f"absolute path is not allowed: {name!r}")
    if len(raw) > 1 and raw[1] == ":":
        raise ValueError(f"drive-qualified path is not allowed: {name!r}")
    if raw.endswith("/"):
        raise ValueError(f"directory member is not allowed: {name!r}")
    if "//" in raw:
        raise ValueError(f"path separator alias is not allowed: {name!r}")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"unsafe path component in {name!r}")
    normalized = PurePosixPath(*parts).as_posix()
    if normalized in {"", "."}:
        raise ValueError(f"invalid normalized path: {name!r}")
    return normalized


def _is_safe_relpath(name: str) -> bool:
    try:
        _normalize_relpath(name)
    except ValueError:
        return False
    return True


def _validate_manifest_shape(manifest: dict) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError("backup manifest schema mismatch")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError("backup manifest entries missing")
    seen: set[str] = set()
    seen_casefold: set[str] = set()
    for entry in entries:
        rel = entry.get("path")
        if not isinstance(rel, str):
            raise ValueError(f"unsafe manifest entry path: {rel!r}")
        normalized = _normalize_relpath(rel)
        folded = normalized.casefold()
        if normalized in seen:
            raise ValueError(f"duplicate manifest entry path: {normalized}")
        if folded in seen_casefold:
            raise ValueError(f"case-colliding manifest entry path: {normalized}")
        seen.add(normalized)
        seen_casefold.add(folded)
        entry["path"] = normalized
        if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64:
            raise ValueError(f"invalid manifest hash for {normalized}")
        if int(entry.get("bytes", -1)) < 0:
            raise ValueError(f"invalid manifest byte count for {normalized}")


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
        normalized_members: dict[str, str] = {}
        casefold_members: dict[str, str] = {}
        names: list[str] = []
        for info in infos:
            import stat

            mode = (info.external_attr >> 16) & 0o170000
            if info.is_dir():
                raise ValueError(f"directory backup member is not allowed: {info.filename}")
            if mode == stat.S_IFLNK:
                raise ValueError(f"symlink backup member is not allowed: {info.filename}")
            if mode not in {0, stat.S_IFREG}:
                raise ValueError(f"nonregular backup member is not allowed: {info.filename}")
            normalized = _normalize_relpath(info.filename)
            folded = normalized.casefold()
            if normalized in normalized_members:
                raise ValueError(f"duplicate ZIP member names are not allowed: {normalized}")
            if folded in casefold_members:
                raise ValueError(
                    f"case-colliding ZIP member names are not allowed: {normalized}"
                )
            normalized_members[normalized] = info.filename
            casefold_members[folded] = info.filename
            names.append(normalized)
        if len(names) != len(set(names)):
            raise ValueError("duplicate ZIP member names are not allowed")
        if MANIFEST_FILE not in names:
            raise ValueError("backup manifest missing")
        manifest = json.loads(archive.read(normalized_members[MANIFEST_FILE]))
        _validate_manifest_shape(manifest)
        expected_payload = {f"payload/{row['path']}": row for row in manifest["entries"]}
        actual_payload = {name for name in names if name.startswith("payload/")}
        if actual_payload != set(expected_payload):
            raise ValueError("backup payload/manifest coverage mismatch")
        allowed_members = set(expected_payload) | {MANIFEST_FILE}
        unexpected = set(names) - allowed_members
        if unexpected:
            raise ValueError(f"unexpected backup members present: {sorted(unexpected)!r}")
        for name, row in expected_payload.items():
            data = archive.read(normalized_members[name])
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


def promote_last_known_good_atomic(
    candidate_backup: Path,
    last_known_good: Path,
    *,
    verifier=verify_backup,
    failure_injector=None,
) -> dict:
    import shutil

    candidate_backup = Path(candidate_backup)
    last_known_good = Path(last_known_good)
    last_known_good.parent.mkdir(parents=True, exist_ok=True)
    candidate_hash = _sha(candidate_backup.read_bytes())
    temp_promote = last_known_good.parent / f".{last_known_good.name}.promote.tmp"
    rollback_copy = last_known_good.parent / f".{last_known_good.name}.rollback.tmp"
    had_prior = last_known_good.exists()
    prior_hash = _sha(last_known_good.read_bytes()) if had_prior else None
    promotion_performed = False
    try:
        if had_prior:
            shutil.copy2(last_known_good, rollback_copy)
        if failure_injector:
            failure_injector("before_copy")
        shutil.copy2(candidate_backup, temp_promote)
        if failure_injector:
            failure_injector("after_copy")
        with temp_promote.open("rb+") as fh:
            fh.flush()
            if hasattr(os, "fsync"):
                os.fsync(fh.fileno())
        if failure_injector:
            failure_injector("after_flush")
        verifier(temp_promote)
        if failure_injector:
            failure_injector("after_verify")
        os.replace(temp_promote, last_known_good)
        promotion_performed = True
        if failure_injector:
            failure_injector("after_replace")
        promoted_hash = _sha(last_known_good.read_bytes())
        if promoted_hash != candidate_hash:
            raise ValueError("promoted last-known-good bytes mismatch candidate")
        verifier(last_known_good)
        return {
            "verified_before_promotion": True,
            "candidate_sha256": candidate_hash,
            "previous_last_known_good_sha256": prior_hash,
            "promoted_last_known_good_sha256": promoted_hash,
            "rollback_available": had_prior,
        }
    except Exception:
        if promotion_performed and rollback_copy.exists():
            os.replace(rollback_copy, last_known_good)
        raise
    finally:
        temp_promote.unlink(missing_ok=True)
        rollback_copy.unlink(missing_ok=True)
