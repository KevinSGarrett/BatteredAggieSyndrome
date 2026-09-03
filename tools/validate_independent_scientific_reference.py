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
}
REFERENCE_ROOT = Path("src") / "aggie_analytics" / "scientific_reference"
PRODUCER_PATHS = (
    Path("src") / "aggie_analytics" / "data" / "week1_2026_game_grain_distribution_successor.py",
    Path("src") / "aggie_analytics" / "data" / "week1_2026_market_integrity_successor.py",
    Path("src") / "aggie_analytics" / "data" / "week1_2026_current_contest_binding_successor.py",
    Path("src") / "aggie_analytics" / "data" / "producer_distribution_math.py",
    Path("src") / "aggie_analytics" / "data" / "producer_market_math.py",
)


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def validate(repo_root: Path) -> list[str]:
    findings: list[str] = []
    root = repo_root / REFERENCE_ROOT
    if not root.is_dir():
        return ["INDEPENDENT_REFERENCE_MISSING"]
    for path in sorted(root.glob("*.py")):
        imports = _module_imports(path)
        overlap = sorted(imports & FORBIDDEN_PRODUCER_IMPORTS)
        if overlap:
            findings.append(
                f"INDEPENDENT_REFERENCE_IMPORTS_PRODUCER:{path.name}:{','.join(overlap)}"
            )
        producer = sorted(
            item
            for item in imports
            if item == "aggie_analytics.data"
            or item.startswith("aggie_analytics.data.")
        )
        if producer:
            findings.append(
                f"INDEPENDENT_REFERENCE_IMPORTS_PRODUCER:{path.name}:{','.join(producer)}"
            )
    for producer_path in PRODUCER_PATHS:
        path = repo_root / producer_path
        if not path.is_file():
            findings.append(f"PRODUCER_MODULE_MISSING:{producer_path.as_posix()}")
            continue
        imports = _module_imports(path)
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
