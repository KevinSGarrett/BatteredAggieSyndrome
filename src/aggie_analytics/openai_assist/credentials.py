from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


class CredentialError(RuntimeError):
    pass


def authoritative_env_path(repo_root: Path) -> Path:
    """Resolve the main checkout .env without copying it into a worktree."""
    explicit = os.environ.get("AGGIE_AUTHORITATIVE_ENV_PATH", "").strip()
    if explicit:
        candidate = Path(explicit).resolve()
    else:
        run = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=repo_root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        if run.returncode != 0:
            raise CredentialError("cannot resolve authoritative Git common directory")
        common = Path(run.stdout.strip()).resolve()
        candidate = common.parent / ".env"
    if not candidate.is_absolute() or not candidate.is_file():
        raise CredentialError("authoritative project .env is unavailable")
    return candidate


def load_openai_api_key(repo_root: Path) -> str:
    try:
        path = authoritative_env_path(repo_root)
    except CredentialError:
        path = None
    if path is not None:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if raw.startswith("OPENAI_API_KEY="):
                value = raw.split("=", 1)[1].strip().strip('"').strip("'")
                if value:
                    return value
                break
    injected = os.environ.get("OPENAI_API_KEY", "").strip()
    if injected:
        return injected
    raise CredentialError(
        "OPENAI_API_KEY is missing or blank in both the authoritative project .env "
        "and the inherited process environment"
    )


def configured_secret_values(repo_root: Path) -> tuple[str, ...]:
    """Load secret values for exact request-material rejection without exposing names or values."""
    secret_name = re.compile(r"(?:KEY|TOKEN|SECRET|PASSWORD|COOKIE|AUTH)", re.IGNORECASE)
    values: set[str] = set()
    try:
        path = authoritative_env_path(repo_root)
    except CredentialError:
        path = None
    if path is not None:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, value = stripped.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if secret_name.search(name) and len(value) >= 8:
                values.add(value)
    injected = os.environ.get("OPENAI_API_KEY", "").strip()
    if len(injected) >= 8:
        values.add(injected)
    return tuple(sorted(values))


def credential_source(repo_root: Path) -> str:
    """Report only the credential channel; never the value or a secret-bearing path."""
    try:
        path = authoritative_env_path(repo_root)
    except CredentialError:
        path = None
    if path is not None:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if raw.startswith("OPENAI_API_KEY=") and raw.split("=", 1)[1].strip().strip('"').strip("'"):
                return "AUTHORITATIVE_ENV_FILE"
    if os.environ.get("OPENAI_API_KEY", "").strip():
        return "INHERITED_PROCESS_ENVIRONMENT"
    return "UNAVAILABLE"


def key_is_nonempty(repo_root: Path) -> bool:
    try:
        return bool(load_openai_api_key(repo_root))
    except CredentialError:
        return False
