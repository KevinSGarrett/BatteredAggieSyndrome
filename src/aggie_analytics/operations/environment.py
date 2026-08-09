from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
import hashlib, json, os, platform, subprocess, sys
from typing import Iterable

SAFE_ENV_KEYS = ("AGGIE_ENV", "AGGIE_LOG_LEVEL", "PYTHONHASHSEED")


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
