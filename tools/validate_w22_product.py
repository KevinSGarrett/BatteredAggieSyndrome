from __future__ import annotations

import argparse
import ast
import csv
from pathlib import Path

DONE = [f"TASK-{i:03d}" for i in range(152, 158)]
REQUIRED = [
    "src/aggie_analytics/product/contracts.py",
    "src/aggie_analytics/product/repository.py",
    "src/aggie_analytics/product/freshness.py",
    "src/aggie_analytics/product/explainability.py",
    "src/aggie_analytics/product/service.py",
    "src/aggie_analytics/product/dashboard.py",
    "src/aggie_analytics/api/fastapi_app.py",
    "src/aggie_analytics/product/static/index.html",
    "src/aggie_analytics/product/static/app.js",
    "schemas/forecast_snapshot_v2.schema.json",
    "schemas/product_forecast_response_v1.schema.json",
    "docs/107_W22_SNAPSHOT_SERVING_PRODUCT.md",
    "docs/108_W22_IMPLEMENTATION_INVENTORY.md",
    "docs/product/API_CONTRACT.md",
    "docs/product/FRAMEWORK_DECISION.md",
    "tests/test_w22_product_serving.py",
    "governance/W22_ADAPTIVE_REVIEW.md",
    "governance/W22_VALIDATION_REPORT.md",
]
FORBIDDEN_PREFIXES = (
    "aggie_analytics.data",
    "aggie_analytics.features",
    "aggie_analytics.modeling",
    "aggie_analytics.experimentation",
    "aggie_analytics.team_state",
)


def validate(root: Path) -> list[str]:
    findings: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            findings.append("missing:" + rel)
    rows = {r["task_id"]: r for r in csv.DictReader((root / "governance/IMPLEMENTATION_WBS.csv").open(encoding="utf-8"))}
    for tid in DONE:
        if rows.get(tid, {}).get("status") != "DONE":
            findings.append(f"{tid}:not_done")
    state = (root / "governance/CURRENT_STATE.yaml").read_text(encoding="utf-8")
    current = None
    for line in state.splitlines():
        if line.startswith("current_wave:"):
            current = line.split(":", 1)[1].strip(); break
    try:
        current_number = int(current[1:]) if current else None
        if current_number is None or current_number < 22:
            findings.append("current_state:pre_w22")
        elif current_number == 22 and rows.get("TASK-158", {}).get("status") != "READY":
            findings.append("TASK-158:not_ready_for_w23")
        elif current_number > 22 and rows.get("TASK-158", {}).get("status") != "DONE":
            findings.append("TASK-158:not_done_after_w22")
    except (TypeError, ValueError):
        findings.append("current_state:invalid_wave")
    for needle in (
        "w22_product_gate: CLEARED_W22_FUNCTIONAL_STARTER",
        "serving_mode: IMMUTABLE_PUBLISHED_SNAPSHOT_ONLY",
        "trained_model_metrics_claimed_w22: false",
    ):
        if needle not in state:
            findings.append("current_state_missing:" + needle)
    adr = {r["adr_id"] for r in csv.DictReader((root / "governance/ADR_INDEX.csv").open(encoding="utf-8"))}
    for item in ("ADR-331", "ADR-332", "ADR-333", "ADR-334", "ADR-335"):
        if item not in adr:
            findings.append("missing:" + item)
    for base in (root / "src/aggie_analytics/product", root / "src/aggie_analytics/api"):
        if not base.exists():
            continue
        for path in base.glob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                findings.append(f"syntax:{path.relative_to(root)}:{exc}")
                continue
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    if name.startswith(FORBIDDEN_PREFIXES):
                        findings.append(f"serving_boundary:{path.relative_to(root)}:{name}")
    return findings


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = ap.parse_args()
    result = validate(args.repo_root.resolve())
    if result:
        raise SystemExit("FAIL: " + "; ".join(result))
    print("PASS: W22 immutable snapshot-serving/product functional-starter gate")
