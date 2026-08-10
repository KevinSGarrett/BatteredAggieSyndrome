from __future__ import annotations

"""Fail-closed helpers for recursive cleanup outside the Git repository."""

import os
import shutil
from pathlib import Path


class UnsafeRecursiveDelete(ValueError):
    """Raised when a recursive-delete target is not provably safe."""


def _absolute_resolved(path: str | os.PathLike[str], *, label: str) -> Path:
    raw = os.fspath(path)
    if not raw.strip():
        raise UnsafeRecursiveDelete(f"{label} must not be empty")
    candidate = Path(raw)
    if not candidate.is_absolute():
        raise UnsafeRecursiveDelete(f"{label} must be an absolute path")
    lexical = Path(os.path.abspath(candidate))
    resolved = lexical.resolve(strict=False)
    if lexical.is_symlink() or os.path.normcase(str(lexical)) != os.path.normcase(str(resolved)):
        raise UnsafeRecursiveDelete(f"{label} must not be or traverse a symlink/junction")
    return resolved


def validate_recursive_delete_target(
    target: str | os.PathLike[str] | None,
    *,
    allowed_root: str | os.PathLike[str],
    repo_root: str | os.PathLike[str],
) -> Path:
    """Return a verified target that is strictly below an external allowed root.

    A missing/relative target, the allowed root itself, any repository path, a
    filesystem root, the current directory, the user's home, or a symlink is
    rejected.  Callers must preserve ``None`` as ``None`` instead of replacing
    it with ``Path()``, whose value is the current directory.
    """

    if target is None:
        raise UnsafeRecursiveDelete("recursive-delete target is unset")
    raw_target = os.fspath(target)
    if not raw_target.strip() or Path(raw_target) == Path():
        raise UnsafeRecursiveDelete("recursive-delete target must not be the current directory")

    resolved_target = _absolute_resolved(raw_target, label="recursive-delete target")
    resolved_allowed = _absolute_resolved(allowed_root, label="allowed cleanup root")
    resolved_repo = _absolute_resolved(repo_root, label="repository root")
    resolved_cwd = Path.cwd().resolve()
    resolved_home = Path.home().resolve()

    drive_root = Path(resolved_target.anchor).resolve()
    allowed_drive_root = Path(resolved_allowed.anchor).resolve()
    if resolved_allowed in {allowed_drive_root, resolved_cwd, resolved_home, resolved_repo}:
        raise UnsafeRecursiveDelete(f"protected allowed cleanup root: {resolved_allowed}")
    forbidden_exact = {
        drive_root,
        resolved_allowed,
        resolved_repo,
        resolved_cwd,
        resolved_home,
    }
    if resolved_target in forbidden_exact:
        raise UnsafeRecursiveDelete(f"protected recursive-delete target: {resolved_target}")
    if resolved_repo in resolved_allowed.parents:
        raise UnsafeRecursiveDelete("allowed cleanup root must be outside the repository")
    if (
        resolved_target == resolved_repo
        or resolved_repo in resolved_target.parents
        or resolved_target in resolved_repo.parents
    ):
        raise UnsafeRecursiveDelete("recursive-delete target must not contain or be inside the repository")
    if resolved_target in resolved_cwd.parents:
        raise UnsafeRecursiveDelete("recursive-delete target must not contain the current directory")
    if resolved_target in resolved_home.parents:
        raise UnsafeRecursiveDelete("recursive-delete target must not contain the user's home")
    if resolved_allowed not in resolved_target.parents:
        raise UnsafeRecursiveDelete("recursive-delete target is not below the allowed cleanup root")
    return resolved_target


def safe_remove_tree(
    target: str | os.PathLike[str] | None,
    *,
    allowed_root: str | os.PathLike[str],
    repo_root: str | os.PathLike[str],
) -> bool:
    """Remove one verified external subtree; return False when it is absent."""

    resolved = validate_recursive_delete_target(
        target,
        allowed_root=allowed_root,
        repo_root=repo_root,
    )
    if not resolved.exists():
        return False
    if not resolved.is_dir():
        raise UnsafeRecursiveDelete("recursive-delete target must be a directory")
    shutil.rmtree(resolved)
    return True
