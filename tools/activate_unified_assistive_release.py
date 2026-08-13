from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
LAUNCHER_PATH = HERE / "launch_unified_assistive_service.py"


def _launcher_module():
    spec = importlib.util.spec_from_file_location("unified_assistive_stable_launcher", LAUNCHER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("STABLE_LAUNCHER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}-{uuid.uuid4().hex}.tmp"
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def activate(runtime_root: Path, release_root: Path) -> dict[str, object]:
    runtime = runtime_root.resolve(strict=True)
    release = release_root.resolve(strict=True)
    commit = release.name
    expected_release = (runtime / "releases" / commit).resolve(strict=True)
    if release != expected_release:
        raise RuntimeError("ACTIVATION_RELEASE_PATH_INVALID")
    manifest_path = release / "RELEASE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("build_commit") != commit:
        raise RuntimeError("ACTIVATION_RELEASE_IDENTITY_INVALID")
    pointer = {
        "schema_version": 1,
        "artifact_type": "UNIFIED_ASSISTIVE_RELEASE_POINTER",
        "build_commit": commit,
        "release_root": str(release),
        "release_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "source_tree_sha256": manifest.get("source_tree_sha256"),
        "activated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    payload = canonical(pointer)
    digest = hashlib.sha256(payload).hexdigest()
    immutable = runtime / "deployment" / "release-pointers" / "sha256" / digest / "pointer.json"
    if immutable.exists() and immutable.read_bytes() != payload:
        raise RuntimeError("IMMUTABLE_RELEASE_POINTER_COLLISION")
    if not immutable.exists():
        atomic_write(immutable, payload)
    candidate = runtime / "deployment" / f"candidate-{digest}.json"
    atomic_write(candidate, payload)
    launcher = _launcher_module()
    launcher.validate_release(runtime, candidate)
    atomic_write(runtime / "deployment" / "current-release.json", payload)
    candidate.unlink(missing_ok=True)
    return {
        "result": "PASS",
        "build_commit": commit,
        "pointer_sha256": digest,
        "pointer_path": str(runtime / "deployment" / "current-release.json"),
        "immutable_pointer_path": str(immutable),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--release-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = activate(args.runtime_root, args.release_root)
    except Exception as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
