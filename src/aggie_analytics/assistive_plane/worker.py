from __future__ import annotations

from pathlib import Path, PurePosixPath


FORBIDDEN_PARTS = {".env", ".git"}


def validate_patch_paths(paths: list[str], allowed_roots: list[str]) -> None:
    normalized_roots = tuple(PurePosixPath(root) for root in allowed_roots)
    for raw in paths:
        path = PurePosixPath(raw.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or any(part in FORBIDDEN_PARTS for part in path.parts):
            raise ValueError(f"unsafe patch path: {raw}")
        if not any(path == root or root in path.parents for root in normalized_roots):
            raise ValueError(f"out-of-scope patch path: {raw}")


def ensure_isolated_worktree(path: Path, repository_root: Path) -> None:
    resolved = path.resolve()
    if resolved == repository_root.resolve() or repository_root.resolve() in resolved.parents:
        raise ValueError("assistive worker must use an isolated external worktree")
    if ".env" in {entry.name for entry in resolved.glob(".env")}:
        raise ValueError("assistive worker worktree contains .env")
