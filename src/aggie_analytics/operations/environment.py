from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
import hashlib, json, os, platform, subprocess, sys, tempfile
from typing import Iterable

SAFE_ENV_KEYS = ("AGGIE_ENV", "AGGIE_LOG_LEVEL", "PYTHONHASHSEED")
DATA_ROOT_ENV = "AGGIE_ANALYTICS_DATA_ROOT"
LOCAL_RUNTIME_RELATIVE_PATHS = {
    "raw": "raw",
    "curated": "canonical",
    "model": "model_artifacts",
    "forecast": "forecast_snapshots",
    "log": "runtime/logs",
    "backup": "runtime/backups",
    "quarantine": "quarantine",
}


class UnsafeLocalRuntimePath(ValueError):
    """Raised when a bulk-data root could overlap the source repository."""


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_external_data_root(
    *, repo_root: Path, value: str | os.PathLike[str] | None = None
) -> Path:
    raw = str(value if value is not None else os.environ.get(DATA_ROOT_ENV, "")).strip()
    if not raw or "<" in raw or ">" in raw:
        raise UnsafeLocalRuntimePath(f"{DATA_ROOT_ENV} must be a concrete absolute path")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise UnsafeLocalRuntimePath(f"{DATA_ROOT_ENV} must be absolute")
    data_root = candidate.resolve(strict=False)
    repository = Path(repo_root).expanduser().resolve(strict=False)
    if data_root == repository or _is_within(data_root, repository) or _is_within(repository, data_root):
        raise UnsafeLocalRuntimePath("bulk-data root must be disjoint from the Git repository")
    return data_root


def resolve_local_runtime_paths(
    *, repo_root: Path, value: str | os.PathLike[str] | None = None
) -> dict[str, Path]:
    data_root = resolve_external_data_root(repo_root=repo_root, value=value)
    roots = {name: (data_root / relative).resolve(strict=False) for name, relative in LOCAL_RUNTIME_RELATIVE_PATHS.items()}
    if len(set(roots.values())) != len(roots):
        raise UnsafeLocalRuntimePath("local runtime roots must be distinct")
    return roots


def provision_local_runtime_paths(
    *, repo_root: Path, value: str | os.PathLike[str] | None = None
) -> dict:
    data_root = resolve_external_data_root(repo_root=repo_root, value=value)
    roots = resolve_local_runtime_paths(repo_root=repo_root, value=data_root)
    data_root.mkdir(parents=True, exist_ok=True)
    writable: dict[str, bool] = {}
    for name, path in roots.items():
        path.mkdir(parents=True, exist_ok=True)
        probe: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".aggie-write-probe-", dir=path, delete=False) as handle:
                handle.write(b"AGGIE_PATH_PROBE\n")
                probe = Path(handle.name)
            writable[name] = True
        finally:
            if probe is not None:
                probe.unlink(missing_ok=True)
    return {
        "data_root": data_root,
        "roots": roots,
        "all_absolute": all(path.is_absolute() for path in roots.values()),
        "all_outside_repository": True,
        "all_distinct": len(set(roots.values())) == len(roots),
        "writable": writable,
    }


def validate_local_path_contract(
    payload: dict, *, expected_data_root_activation_sha256: str | None = None
) -> None:
    errors: list[str] = []
    if payload.get("schema_version") != "1.0.0" or payload.get("artifact_type") != "aggie.local_runtime_path_contract":
        errors.append("schema")
    content_hash = payload.get("content_hash", {})
    canonical_payload = dict(payload)
    canonical_payload.pop("content_hash", None)
    actual_hash = hashlib.sha256(
        json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    if content_hash.get("algorithm") != "sha256" or content_hash.get("value") != actual_hash:
        errors.append("content_hash")
    prerequisites = payload.get("prerequisite_identities", {})
    if expected_data_root_activation_sha256 and prerequisites.get("data_root_activation_sha256") != expected_data_root_activation_sha256:
        errors.append("prerequisite_identity")
    roots = payload.get("roots", [])
    expected_aliases = set(LOCAL_RUNTIME_RELATIVE_PATHS)
    aliases = [root.get("alias") for root in roots if isinstance(root, dict)]
    path_hashes = [root.get("resolved_path_sha256") for root in roots if isinstance(root, dict)]
    if len(roots) != len(expected_aliases) or set(aliases) != expected_aliases or len(set(aliases)) != len(aliases):
        errors.append("root_aliases")
    if len(set(path_hashes)) != len(expected_aliases):
        errors.append("root_separation")
    if any(not root.get("absolute") or not root.get("outside_repository") or not root.get("writable") for root in roots if isinstance(root, dict)):
        errors.append("root_state")
    validation = payload.get("validation", {})
    if validation.get("restart_probe", {}).get("resolved_path_hashes_match") is not True:
        errors.append("restart_probe")
    if validation.get("repository_internal_negative_test", {}).get("rejected") is not True:
        errors.append("path_safety")
    if not payload.get("acceptance_matrix") or any(row.get("disposition") != "PASS" for row in payload.get("acceptance_matrix", [])):
        errors.append("acceptance")
    rights = payload.get("security_and_rights", {})
    if rights.get("source_rights_approval_claimed") is not False or rights.get("restricted_payloads_included") is not False:
        errors.append("rights_state")
    eligibility = payload.get("eligibility", {})
    if eligibility.get("production_release_authority") is not False or eligibility.get("source_rights_authority") is not False:
        errors.append("authority")
    handoff = payload.get("consumer_handoff", {})
    if handoff.get("consumer") != "POST-SUBTASK-005" or handoff.get("silent_unlock_allowed") is not False:
        errors.append("consumer_handoff")
    if errors:
        raise ValueError("invalid local path contract: " + ",".join(sorted(set(errors))))


def _git_commit(repo_root: Path | None) -> str | None:
    if not repo_root or not (repo_root / ".git").exists():
        return None
    try:
        return subprocess.check_output(["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True, timeout=3).strip()
    except Exception:
        return None


def collect_runtime_manifest(*, repo_root: Path | None = None, packages: Iterable[str] | None = None) -> dict:
    if packages is None:
        distributions = sorted((d.metadata.get("Name", ""), d.version) for d in metadata.distributions())
        package_map = {name: version for name, version in distributions if name}
    else:
        package_map = {}
        for name in sorted(set(packages)):
            try: package_map[name] = metadata.version(name)
            except metadata.PackageNotFoundError: package_map[name] = "NOT_INSTALLED"
    manifest = {
        "schema_version": "aggie.runtime.environment.v1",
        "captured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "python": {"version": platform.python_version(), "implementation": platform.python_implementation(), "executable_name": Path(sys.executable).name},
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "cpu_count": os.cpu_count(),
        "git_commit": _git_commit(Path(repo_root) if repo_root else None),
        "safe_environment": {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ},
        "packages": package_map,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest["manifest_sha256"] = hashlib.sha256(canonical).hexdigest()
    return manifest


def write_runtime_manifest(path: Path, **kwargs) -> dict:
    payload = collect_runtime_manifest(**kwargs)
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return payload
