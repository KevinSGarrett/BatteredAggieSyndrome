from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = Path(r"C:\BatteredAggieSyndrome.data\assistive\orchestrator-v3")
FILES = (
    "src/aggie_analytics/__init__.py",
    "src/aggie_analytics/assistive_plane/__init__.py",
    "src/aggie_analytics/assistive_plane/backend.py",
    "src/aggie_analytics/assistive_plane/budget.py",
    "src/aggie_analytics/assistive_plane/contracts.py",
    "src/aggie_analytics/assistive_plane/controller_state.py",
    "src/aggie_analytics/assistive_plane/cpu_worker_backend.py",
    "src/aggie_analytics/assistive_plane/cursor_backend.py",
    "src/aggie_analytics/assistive_plane/dispatcher.py",
    "src/aggie_analytics/assistive_plane/inventory_runtime.py",
    "src/aggie_analytics/assistive_plane/ollama_backend.py",
    "src/aggie_analytics/assistive_plane/openrouter_backend.py",
    "src/aggie_analytics/assistive_plane/orchestration.py",
    "src/aggie_analytics/assistive_plane/provider_adapters.py",
    "src/aggie_analytics/assistive_plane/redaction.py",
    "src/aggie_analytics/assistive_plane/review_runtime.py",
    "src/aggie_analytics/assistive_plane/scheduler_runtime.py",
    "src/aggie_analytics/assistive_plane/schemas.py",
    "src/aggie_analytics/assistive_plane/service_runtime.py",
    "src/aggie_analytics/assistive_plane/storage.py",
    "src/aggie_analytics/assistive_plane/watchdog.py",
    "src/aggie_analytics/openai_assist/__init__.py",
    "src/aggie_analytics/openai_assist/budget.py",
    "src/aggie_analytics/openai_assist/contracts.py",
    "src/aggie_analytics/openai_assist/controller.py",
    "src/aggie_analytics/openai_assist/credentials.py",
    "src/aggie_analytics/openai_assist/evals.py",
    "src/aggie_analytics/openai_assist/policy.py",
    "src/aggie_analytics/openai_assist/redaction.py",
    "src/aggie_analytics/openai_assist/schemas.py",
    "src/aggie_analytics/openai_assist/storage.py",
    "configs/openai_assist_policy.json",
    "configs/openai_task_registry.json",
    "configs/openrouter_assist_policy.json",
    "configs/openrouter_task_registry.json",
    "configs/unified_assistive_policy.json",
    "configs/assistive_route_readiness.json",
    "configs/assistive_downstream_adoptions.json",
    "schemas/assistive/candidate_patch.schema.json",
    "schemas/assistive/independent_review.schema.json",
    "schemas/assistive/reconciliation_ranking.schema.json",
    "schemas/assistive/schema_drift_review.schema.json",
    "schemas/assistive/visual_layout_triage.schema.json",
    "schemas/openai/assistive_candidate.schema.json",
    "schemas/openai/assistive_evaluation.schema.json",
    "schemas/openai/depth_chart_noncoverage_visual.schema.json",
    "tools/run_unified_assistive_controller.py",
    "tools/run_unified_assistive_watchdog.py",
    "tools/launch_unified_assistive_service.py",
    "tools/activate_unified_assistive_release.py",
    "tools/switch_unified_assistive_services.ps1",
    "tools/materialize_unified_assistive_inventory.py",
    "tools/reconcile_assistive_review_backlog.py",
)
GENERATED_RELEASE_FILES = {
    "src/aggie_analytics/assistive_plane/__init__.py": (
        b'"""Minimal governed controller release with admitted provider adapters."""\n'
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def git(*arguments: str) -> str:
    return subprocess.run(["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def build_release(output_root: Path, *, expected_commit: str | None = None) -> tuple[Path, dict[str, object]]:
    head = git("rev-parse", "HEAD")
    if expected_commit and head != expected_commit:
        raise RuntimeError("RELEASE_BUILD_COMMIT_MISMATCH")
    if git("status", "--porcelain"):
        raise RuntimeError("RELEASE_BUILD_REQUIRES_CLEAN_WORKTREE")
    temporary = output_root / ".staging" / f"{head}-{uuid.uuid4().hex}"
    release = output_root / head
    temporary.mkdir(parents=True, exist_ok=False)
    try:
        hashes: dict[str, dict[str, object]] = {}
        for relative in FILES:
            source = ROOT / relative
            if not source.is_file():
                raise RuntimeError(f"RELEASE_SOURCE_MISSING:{relative}")
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if relative in GENERATED_RELEASE_FILES:
                destination.write_bytes(GENERATED_RELEASE_FILES[relative])
                source_kind = "GENERATED_MINIMAL_PACKAGE_INITIALIZER"
            else:
                shutil.copy2(source, destination)
                source_kind = "EXACT_REPOSITORY_FILE"
            hashes[relative] = {
                "sha256": sha256_file(destination),
                "bytes": destination.stat().st_size,
                "source_kind": source_kind,
            }
        tree_identity = hashlib.sha256(canonical(hashes)).hexdigest()
        manifest: dict[str, object] = {
            "schema_version": 1,
            "artifact_type": "UNIFIED_ASSISTIVE_CONTROLLER_RELEASE",
            "build_commit": head,
            "source_tree_sha256": tree_identity,
            "built_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "python": sys.version,
            "files": hashes,
            "operational_completion": "INCOMPLETE_UNTIL_DEPLOYED_AND_QUALIFIED",
        }
        (temporary / "RELEASE_MANIFEST.json").write_bytes(canonical(manifest))
        manifest["release_manifest_sha256"] = sha256_file(temporary / "RELEASE_MANIFEST.json")
        if release.exists():
            existing = json.loads((release / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
            if existing.get("build_commit") != head or existing.get("source_tree_sha256") != tree_identity or existing.get("files") != hashes:
                raise RuntimeError("IMMUTABLE_RELEASE_COLLISION")
            expected_files = {*hashes, "RELEASE_MANIFEST.json"}
            actual_files = {
                path.relative_to(release).as_posix()
                for path in release.rglob("*")
                if path.is_file()
            }
            if actual_files != expected_files:
                raise RuntimeError("IMMUTABLE_RELEASE_UNEXPECTED_FILE_SET")
            for relative, identity in hashes.items():
                installed = release / relative
                if not installed.is_file() or sha256_file(installed) != identity["sha256"]:
                    raise RuntimeError(f"IMMUTABLE_RELEASE_FILE_INVALID:{relative}")
            shutil.rmtree(temporary)
            existing["release_manifest_sha256"] = sha256_file(release / "RELEASE_MANIFEST.json")
            return release, existing
        release.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary, release)
        return release, manifest
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_RUNTIME / "releases")
    parser.add_argument("--expected-commit")
    args = parser.parse_args()
    release, manifest = build_release(args.output_root, expected_commit=args.expected_commit)
    print(json.dumps({"result": "PASS", "release": str(release), **manifest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
