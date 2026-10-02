"""Static and runtime producer/reference dependency separation."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterable

PRODUCER_ROOT = "aggie_analytics.cycle30"
REFERENCE_ROOT = "aggie_analytics.scientific_reference.cycle30"
FORBIDDEN_SHARED = (
    "aggie_analytics.scientific_reference.metrics",
    "aggie_analytics.scientific_reference.coherence",
    "aggie_analytics.scientific_reference.binding",
    "aggie_analytics.data",
    "aggie_analytics.modeling",
    "aggie_analytics.features",
    "aggie_analytics.cycle29",
    "aggie_analytics.scientific_reference.cycle29",
    "aggie_analytics.cycle28.scoring",
    "aggie_analytics.scientific_reference.cycle28_scoring",
)


class DependencyError(ValueError):
    """Raised when producer/reference independence is violated."""


def _iter_py(root: Path) -> Iterable[Path]:
    if not root.exists():
        raise DependencyError(f"dependency directory missing: {root}")
    paths = sorted(path for path in root.rglob("*.py") if path.name != "__pycache__")
    if not paths:
        raise DependencyError(f"empty producer/reference directory: {root}")
    return paths


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
            if node.level and node.module is None:
                names.add(f".relative.{node.level}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in {"__import__", "eval", "exec"}:
                raise DependencyError(
                    f"{path}: dynamic {func.id} is a dependency bypass"
                )
            if isinstance(func, ast.Attribute) and func.attr in {"import_module"}:
                raise DependencyError(
                    f"{path}: importlib.import_module is a dependency bypass"
                )
    return names


def _violates(name: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(
        name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes
    )


def static_import_graph(src_root: Path) -> dict[str, Any]:
    producer_dir = src_root / "aggie_analytics" / "cycle30"
    reference_dir = src_root / "aggie_analytics" / "scientific_reference" / "cycle30"
    producer_imports: set[str] = set()
    reference_imports: set[str] = set()
    for path in _iter_py(producer_dir):
        producer_imports.update(_imported_modules(path))
    for path in _iter_py(reference_dir):
        reference_imports.update(_imported_modules(path))
    producer_hits = sorted(
        name
        for name in producer_imports
        if _violates(name, (REFERENCE_ROOT,) + FORBIDDEN_SHARED)
    )
    reference_hits = sorted(
        name
        for name in reference_imports
        if _violates(name, (PRODUCER_ROOT,) + FORBIDDEN_SHARED)
    )
    if producer_hits:
        raise DependencyError(f"producer imports forbidden modules: {producer_hits}")
    if reference_hits:
        raise DependencyError(f"reference imports forbidden modules: {reference_hits}")
    overlap = producer_imports.intersection(reference_imports)
    local_overlap = sorted(
        name
        for name in overlap
        if name.startswith("aggie_analytics.") and name not in {"aggie_analytics"}
    )
    if local_overlap:
        raise DependencyError(
            f"producer and reference share project-local imports: {local_overlap}"
        )
    return {
        "producer_imports": sorted(producer_imports),
        "reference_imports": sorted(reference_imports),
        "disjoint": True,
        "producer_module_count": len(list(_iter_py(producer_dir))),
        "reference_module_count": len(list(_iter_py(reference_dir))),
    }
