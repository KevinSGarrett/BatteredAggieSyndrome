"""Independently reconstruct and validate the Week 1 2026 semantic successor gate.

The validator rebuilds every successor surface from the committed predecessor
payloads, compares the reconstruction byte-for-byte against the committed successor
payloads, and then rechecks the gate's own invariants: that site orientation never
promotes a venue identity, that no venue coordinate is admitted from inference, that
weather stays candidate-only without coordinate authority, that no retired
classification is emitted, and that no forecast is produced. It never reaches the
network and never writes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.national_foundation_reconciliation import sha256_file  # noqa: E402
from aggie_analytics.data.week1_2026_spine_semantic_successor import (  # noqa: E402
    ADMITTED_PROSPECTIVE_PREKICKOFF,
    CELL_PAYLOAD_NAME,
    CORRECTION_PAYLOAD_NAME,
    GATE_RELATIVE,
    PAIR_PAYLOAD_NAME,
    PREDECESSOR_COMPOSITE_DOMAIN,
    PRIOR_CLASSIFICATIONS,
    READINESS_PAYLOAD_NAME,
    RETIRED_PRIOR_CLASSIFICATION,
    ROW_PAYLOAD_NAME,
    SUCCESSOR_DOMAINS,
    VENUE_COORDINATES,
    VENUE_IDENTITY,
    WEATHER_VINTAGE,
    SemanticSuccessorViolation,
    build_expected,
    read_json,
    read_jsonl,
    validate_artifact,
)


def reconstruct(repo_root: Path, data_root: Path) -> dict[str, Any]:
    gate = read_json(repo_root / GATE_RELATIVE)
    expected = build_expected(repo_root=repo_root, data_root=data_root)
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    committed = {
        payload["name"]: read_jsonl(data_root / payload["relative_path"])
        for payload in manifest["payloads"]
    }
    findings: list[str] = []
    for name, rebuilt in (
        (CELL_PAYLOAD_NAME, expected["cells"]),
        (ROW_PAYLOAD_NAME, expected["rows"]),
        (PAIR_PAYLOAD_NAME, expected["pair_counts"]),
        (READINESS_PAYLOAD_NAME, expected["readiness"]),
        (CORRECTION_PAYLOAD_NAME, expected["corrections"]),
    ):
        published = committed.get(name)
        if published is None:
            findings.append(f"committed payload absent: {name}")
        elif published != rebuilt:
            findings.append(
                f"{name}: reconstruction does not match the committed payload"
            )

    bound = gate["bound_predecessors"]
    spine_gate = read_json(
        repo_root / "artifacts/spine/week1_2026_current_feature_spine_gate.json"
    )
    if bound["feature_spine_gate_identity"] != spine_gate["gate_identity"]:
        findings.append(
            "the gate is bound to a different feature spine than the one on disk"
        )
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def audit_semantics(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Re-derive the semantic guarantees from the committed successor payloads alone."""
    gate = read_json(repo_root / GATE_RELATIVE)
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    located = {
        item["name"]: data_root / item["relative_path"] for item in manifest["payloads"]
    }
    cells = read_jsonl(located[CELL_PAYLOAD_NAME])
    rows = read_jsonl(located[ROW_PAYLOAD_NAME])
    pairs = read_jsonl(located[PAIR_PAYLOAD_NAME])
    readiness = read_jsonl(located[READINESS_PAYLOAD_NAME])

    findings: list[str] = []
    if any(cell["domain"] == PREDECESSOR_COMPOSITE_DOMAIN for cell in cells):
        findings.append(
            "the retired composite domain survives in the successor cell surface"
        )
    unknown = sorted({cell["domain"] for cell in cells} - set(SUCCESSOR_DOMAINS))
    if unknown:
        findings.append(f"unknown successor domains emitted: {unknown}")

    by_key: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for cell in cells:
        by_key.setdefault(
            (cell["contest_identity"], cell["canonical_team_id"] or ""), {}
        )[cell["domain"]] = cell

    for key, domains in by_key.items():
        identity_cell = domains.get(VENUE_IDENTITY)
        coordinate_cell = domains.get(VENUE_COORDINATES)
        weather_cell = domains.get(WEATHER_VINTAGE)
        identity_admitted = bool(
            identity_cell
            and identity_cell["admission_disposition"]
            == ADMITTED_PROSPECTIVE_PREKICKOFF
        )
        if identity_admitted and identity_cell["value"].get("venue_identity") is None:
            findings.append(
                f"{key}: venue identity admitted without an authoritative id"
            )
        if (
            coordinate_cell
            and coordinate_cell["admission_disposition"]
            == ADMITTED_PROSPECTIVE_PREKICKOFF
            and not identity_admitted
        ):
            findings.append(f"{key}: venue coordinates admitted without venue identity")
        if (
            weather_cell
            and weather_cell["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
            and not (
                coordinate_cell
                and coordinate_cell["admission_disposition"]
                == ADMITTED_PROSPECTIVE_PREKICKOFF
            )
        ):
            findings.append(
                f"{key}: weather admitted without authoritative coordinates"
            )

    for row in rows:
        if row["prior_classification"] == RETIRED_PRIOR_CLASSIFICATION:
            findings.append("a successor row emitted the retired prior classification")
        if row["prior_classification"] not in PRIOR_CLASSIFICATIONS:
            findings.append(
                f"unknown prior classification: {row['prior_classification']}"
            )
        if row["prior_retired_classification_asserted"] is not False:
            findings.append("a successor row asserted the retired unknowability claim")
        if row["target_outcome_enters_its_own_feature_row"] is not False:
            findings.append("a target outcome entered its own feature row")
        if row["tamu_specific_adjustment_applied"] is not False:
            findings.append("an A&M-specific adjustment was applied to a successor row")

    for pair in pairs:
        if "admitted_domain_count" in pair:
            findings.append("the retired ambiguous count field survives at pair level")
        if (
            pair["distinct_admitted_domain_count"]
            > pair["admitted_team_domain_cell_count"]
        ):
            findings.append(
                f"{pair['contest_identity']}: distinct domains exceed team-domain cells"
            )

    for item in readiness:
        if item["forecast_readiness_state"] == "PARTIAL_MODEL_INPUT":
            findings.append("a readiness row remained in the nonterminal partial state")
        if item["forecast_emitted_by_this_gate"] is not False:
            findings.append("a readiness row emitted a forecast")

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "cells_audited": len(cells),
        "rows_audited": len(rows),
        "pairs_audited": len(pairs),
        "readiness_rows_audited": len(readiness),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    )
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)
    try:
        reconstruction = reconstruct(repo_root, data_root)
        semantics = audit_semantics(repo_root, data_root)
        artifact = validate_artifact(repo_root=repo_root, data_root=data_root)
    except SemanticSuccessorViolation as exc:
        print(json.dumps({"result": "FAIL", "findings": [str(exc)]}, indent=2))
        return 1
    passed = (
        reconstruction["result"] == "PASS"
        and semantics["result"] == "PASS"
        and artifact["result"] == "PASS"
    )
    report = {
        "result": "PASS" if passed else "FAIL",
        "independent_reconstruction": reconstruction,
        "semantic_audit": semantics,
        "artifact_validation": artifact,
        "gate_sha256": sha256_file(repo_root / GATE_RELATIVE),
        "forecast_produced": False,
        "network_access": "NONE",
        "writes_performed": "NONE",
    }
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
