"""Independent scientific-reference validators. Do not import producer helpers."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

FORBIDDEN_PRODUCER_IMPORTS = {
    "aggie_analytics.data.week1_2026_market_benchmark_and_adequacy",
    "aggie_analytics.data.week1_2026_forecast_input_binding_successor",
    "aggie_analytics.data.week1_2026_ridge_distribution_coherence",
    "aggie_analytics.data.national_foundation_reconciliation",
    "aggie_analytics.data.week1_2026_game_grain_distribution_successor",
    "aggie_analytics.data.week1_2026_market_integrity_successor",
    "aggie_analytics.data.week1_2026_current_contest_binding_successor",
    "aggie_analytics.data.producer_distribution_math",
    "aggie_analytics.data.producer_market_math",
    "aggie_analytics.data.producer_metric_math",
    "aggie_analytics.data.week1_2026_game_grain_national_forecast_successor",
    "aggie_analytics.data.historical_saved_pair_game_grain_successor",
    "aggie_analytics.data.week1_2026_cycle27_official_final_scoring",
    "aggie_analytics.data.week1_2026_official_final_scoring_successor",
}
REFERENCE_ROOT = Path("src") / "aggie_analytics" / "scientific_reference"
INDEPENDENT_TOOLS = (
    Path("tools") / "validate_historical_saved_pair_game_grain_successor.py",
    Path("tools") / "validate_week1_2026_cycle27_official_final_scoring.py",
    Path("tools") / "validate_cross_output_coherence.py",
    Path("tools") / "validate_raw_to_forecast_trace.py",
)
PRODUCER_PATHS = (
    Path("src")
    / "aggie_analytics"
    / "data"
    / "week1_2026_game_grain_distribution_successor.py",
    Path("src")
    / "aggie_analytics"
    / "data"
    / "week1_2026_market_integrity_successor.py",
    Path("src")
    / "aggie_analytics"
    / "data"
    / "week1_2026_current_contest_binding_successor.py",
    Path("src")
    / "aggie_analytics"
    / "data"
    / "week1_2026_game_grain_national_forecast_successor.py",
    Path("src")
    / "aggie_analytics"
    / "data"
    / "historical_saved_pair_game_grain_successor.py",
    Path("src") / "aggie_analytics" / "data" / "producer_distribution_math.py",
    Path("src") / "aggie_analytics" / "data" / "producer_market_math.py",
    Path("src") / "aggie_analytics" / "data" / "producer_metric_math.py",
    Path("src")
    / "aggie_analytics"
    / "data"
    / "week1_2026_cycle27_official_final_scoring.py",
)
DYNAMIC_IMPORT_FINDING = "INDEPENDENT_REFERENCE_DYNAMIC_IMPORT"


def _module_name_for(path: Path, repo_root: Path) -> str:
    relative = path.resolve().relative_to((repo_root / "src").resolve())
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_from_module(node: ast.ImportFrom, importer: str) -> list[str]:
    if node.level == 0:
        return [node.module] if node.module else []
    parts = importer.split(".")
    if node.level > len(parts):
        return ["INVALID_RELATIVE_IMPORT"]
    parent = parts[: len(parts) - node.level]
    if node.module:
        return [".".join([*parent, *node.module.split(".")])]
    return [".".join([*parent, alias.name]) for alias in node.names]


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _dynamic_import_names(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name in {"__import__", "import_module", "importlib.import_module"}:
            found.append(name)
    return found


def _module_imports(
    path: Path, *, importer: str
) -> tuple[set[str], list[str], list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    unresolved_relative: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_from_module(node, importer)
            if "INVALID_RELATIVE_IMPORT" in resolved:
                unresolved_relative.append(path.name)
            found.update(item for item in resolved if item != "INVALID_RELATIVE_IMPORT")
    return found, unresolved_relative, _dynamic_import_names(tree)


def _producer_overlap(imports: set[str]) -> list[str]:
    overlap = sorted(imports & FORBIDDEN_PRODUCER_IMPORTS)
    extra = sorted(
        item
        for item in imports
        if item == "aggie_analytics.data" or item.startswith("aggie_analytics.data.")
    )
    return sorted(set(overlap) | set(extra))


def _reference_closure(
    repo_root: Path, seed_imports: dict[str, set[str]]
) -> dict[str, set[str]]:
    changed = True
    closure = {name: set(values) for name, values in seed_imports.items()}
    while changed:
        changed = False
        for name, imported in list(closure.items()):
            extra: set[str] = set()
            for item in imported:
                if item in closure:
                    extra.update(closure[item])
            before = len(imported)
            imported.update(extra)
            if len(imported) != before:
                changed = True
            closure[name] = imported
    return closure


def validate(repo_root: Path) -> list[str]:
    findings: list[str] = []
    root = repo_root / REFERENCE_ROOT
    if not root.is_dir():
        return ["INDEPENDENT_REFERENCE_MISSING"]
    seed: dict[str, set[str]] = {}
    for path in sorted(root.rglob("*.py")):
        importer = _module_name_for(path, repo_root)
        imports, unresolved, dynamic = _module_imports(path, importer=importer)
        seed[importer] = imports
        if unresolved:
            findings.append(f"INDEPENDENT_REFERENCE_RELATIVE_UNRESOLVED:{path.name}")
        if dynamic:
            findings.append(f"{DYNAMIC_IMPORT_FINDING}:{path.name}:{','.join(dynamic)}")
        producer = _producer_overlap(imports)
        if producer:
            findings.append(
                f"INDEPENDENT_REFERENCE_IMPORTS_PRODUCER:{path.name}:{','.join(producer)}"
            )
    closure = _reference_closure(repo_root, seed)
    for name, imported in closure.items():
        producer = _producer_overlap(imported)
        if producer:
            findings.append(
                f"INDEPENDENT_REFERENCE_TRANSITIVE_PRODUCER:{name}:{','.join(producer)}"
            )
    for tool in INDEPENDENT_TOOLS:
        path = repo_root / tool
        if not path.is_file():
            findings.append(f"INDEPENDENT_TOOL_MISSING:{tool.as_posix()}")
            continue
        importer = f"tools.{path.stem}"
        imports, unresolved, dynamic = _module_imports(path, importer=importer)
        if unresolved:
            findings.append(f"INDEPENDENT_TOOL_RELATIVE_UNRESOLVED:{path.name}")
        if dynamic:
            findings.append(f"{DYNAMIC_IMPORT_FINDING}:{path.name}:{','.join(dynamic)}")
        producer = _producer_overlap(imports)
        if producer:
            findings.append(
                f"INDEPENDENT_TOOL_IMPORTS_PRODUCER:{path.name}:{','.join(producer)}"
            )
    for producer_path in PRODUCER_PATHS:
        path = repo_root / producer_path
        if not path.is_file():
            findings.append(f"PRODUCER_MODULE_MISSING:{producer_path.as_posix()}")
            continue
        importer = _module_name_for(path, repo_root)
        imports, _, _ = _module_imports(path, importer=importer)
        reverse = sorted(
            item
            for item in imports
            if item == "aggie_analytics.scientific_reference"
            or item.startswith("aggie_analytics.scientific_reference.")
        )
        if reverse:
            findings.append(
                f"PRODUCER_IMPORTS_INDEPENDENT_REFERENCE:{producer_path.name}:{','.join(reverse)}"
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    findings = validate(Path(args.repo_root).resolve())
    print(
        json.dumps(
            {
                "validator": "independent_scientific_reference",
                "result": "PASS" if not findings else "FAIL",
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
