from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path


COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ROLE_SCRIPTS = {
    "controller": "tools/run_unified_assistive_controller.py",
    "watchdog": "tools/run_unified_assistive_watchdog.py",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_object(path: Path, error: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(error) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(error)
    return payload


def validate_release(runtime_root: Path, pointer_path: Path | None = None) -> tuple[Path, dict[str, object]]:
    runtime = runtime_root.resolve(strict=True)
    pointer = pointer_path or runtime / "deployment" / "current-release.json"
    payload = _load_object(pointer, "RELEASE_POINTER_INVALID")
    if payload.get("schema_version") != 1 or payload.get("artifact_type") != "UNIFIED_ASSISTIVE_RELEASE_POINTER":
        raise RuntimeError("RELEASE_POINTER_SCHEMA_INVALID")
    commit = payload.get("build_commit")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        raise RuntimeError("RELEASE_POINTER_COMMIT_INVALID")
    expected_release = (runtime / "releases" / commit).resolve(strict=True)
    configured_release = payload.get("release_root")
    if not isinstance(configured_release, str) or Path(configured_release).resolve(strict=True) != expected_release:
        raise RuntimeError("RELEASE_POINTER_PATH_INVALID")
    manifest_path = expected_release / "RELEASE_MANIFEST.json"
    manifest_sha = payload.get("release_manifest_sha256")
    if not isinstance(manifest_sha, str) or sha256_file(manifest_path) != manifest_sha:
        raise RuntimeError("RELEASE_POINTER_MANIFEST_HASH_MISMATCH")
    manifest = _load_object(manifest_path, "RELEASE_MANIFEST_INVALID")
    if manifest.get("schema_version") != 1 or manifest.get("build_commit") != commit:
        raise RuntimeError("RELEASE_MANIFEST_IDENTITY_MISMATCH")
    if manifest.get("source_tree_sha256") != payload.get("source_tree_sha256"):
        raise RuntimeError("RELEASE_SOURCE_TREE_IDENTITY_MISMATCH")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise RuntimeError("RELEASE_MANIFEST_FILES_INVALID")
    expected_files = {"RELEASE_MANIFEST.json", *files}
    actual_files = {
        path.relative_to(expected_release).as_posix()
        for path in expected_release.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise RuntimeError("RELEASE_FILE_SET_MISMATCH")
    for relative, identity in files.items():
        if not isinstance(relative, str) or not isinstance(identity, dict):
            raise RuntimeError("RELEASE_MANIFEST_FILE_IDENTITY_INVALID")
        candidate = (expected_release / relative).resolve(strict=True)
        try:
            candidate.relative_to(expected_release)
        except ValueError as exc:
            raise RuntimeError("RELEASE_FILE_PATH_ESCAPE") from exc
        if not candidate.is_file():
            raise RuntimeError(f"RELEASE_FILE_MISSING:{relative}")
        if candidate.stat().st_size != identity.get("bytes") or sha256_file(candidate) != identity.get("sha256"):
            raise RuntimeError(f"RELEASE_FILE_IDENTITY_MISMATCH:{relative}")
    return expected_release, manifest


def launch(role: str, runtime_root: Path, pointer_path: Path | None = None, *, validate_only: bool = False) -> dict[str, object]:
    if role not in ROLE_SCRIPTS:
        raise RuntimeError("SERVICE_ROLE_INVALID")
    release, manifest = validate_release(runtime_root, pointer_path)
    script = release / ROLE_SCRIPTS[role]
    result = {
        "result": "PASS",
        "role": role,
        "build_commit": manifest["build_commit"],
        "release_root": str(release),
        "script": str(script),
    }
    if validate_only:
        return result
    arguments = [
        sys.executable,
        "-B",
        str(script),
        "serve",
        "--runtime-root",
        str(runtime_root.resolve(strict=True)),
        "--build-commit",
        str(manifest["build_commit"]),
    ]
    os.execv(sys.executable, arguments)
    raise RuntimeError("SERVICE_EXEC_RETURNED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=sorted(ROLE_SCRIPTS), required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--pointer-path", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        result = launch(args.role, args.runtime_root, args.pointer_path, validate_only=args.validate_only)
    except Exception as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
