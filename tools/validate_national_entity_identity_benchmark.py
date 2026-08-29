"""Independently validate the national entity-identity benchmark.

Re-derives every resolution, control and metric from the contract, the raw
acquisition ledger and the canonical spine, then proves the committed artifact
reproduces byte for byte and honours every declared prohibition.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_entity_identity_benchmark import (  # noqa: E402
    ARTIFACT_ID,
    EntityBenchmarkViolation,
    build_artifact,
    load_inputs,
    payload_identity,
    read_jsonl,
    sha256_of,
)


def failures_for(gate: dict, rebuilt: dict, data_root: Path) -> list[str]:
    problems: list[str] = []

    if gate.get("payload_root_sha256") != rebuilt["gate"].get("payload_root_sha256"):
        problems.append(
            "payload identity did not reproduce:"
            f" committed={gate.get('payload_root_sha256')}"
            f" rebuilt={rebuilt['gate'].get('payload_root_sha256')}"
        )

    manifest = json.loads(
        (data_root / gate["manifest"]["relative_path"]).read_text(encoding="utf-8-sig")
    )
    located = {entry["name"]: data_root / entry["relative_path"] for entry in manifest["payloads"]}

    def payload_rows(name: str) -> list[dict]:
        return read_jsonl(located[name])

    for entry in gate.get("payloads", []):
        path = located.get(entry["name"])
        if path is None or not path.exists():
            problems.append(f"payload {entry['name']} is missing at {path}")
            continue
        rows = read_jsonl(path)
        if len(rows) != entry["rows"]:
            problems.append(
                f"payload {entry['name']} row count drifted:"
                f" committed={entry['rows']} observed={len(rows)}"
            )
        digest = payload_identity(rows)
        if digest != entry["sha256"]:
            problems.append(
                f"payload {entry['name']} hash drifted:"
                f" committed={entry['sha256']} observed={digest}"
            )

    resolutions = payload_rows("national_entity_identity_resolutions.jsonl")

    if gate.get("identity_surfaces", {}).get("fuzzy_auto_accept_enabled") is not False:
        problems.append("fuzzy auto-accept must remain disabled")

    for row in resolutions:
        if row["canonical_team_id"] is None:
            if not row.get("abstention_reason"):
                problems.append(
                    f"{row['official_source_label']} abstained without a declared reason"
                )
            continue
        if row.get("official_evidence_state") != "ACQUIRED":
            problems.append(
                f"{row['official_source_label']} was bound without acquired official evidence"
            )
        if not row.get("official_source_label_matches_directory"):
            problems.append(
                f"{row['official_source_label']} was bound without an exact official"
                " directory identifier"
            )
        leader = row.get("leading_candidate") or {}
        if leader.get("canonical_team_id") != row["canonical_team_id"]:
            problems.append(
                f"{row['official_source_label']} bound a team that was not the leading candidate"
            )

    controls = payload_rows("national_entity_identity_negative_controls.jsonl")
    failed = [row for row in controls if not row["passed"]]
    if failed:
        problems.append(
            "negative controls failed for: "
            + ", ".join(sorted(f"{row['control_id']}/{row['official_source_label']}" for row in failed))
        )
    if gate.get("negative_controls", {}).get("failed") != len(failed):
        problems.append("the gate misreports the negative control failure count")

    successors = payload_rows("prospective_2026_shadow_cohort_successor.jsonl")
    for row in successors:
        for checkpoint in row.get("checkpoints") or []:
            identifier = checkpoint.get("checkpoint_id")
            if identifier in {"T_MINUS_24H", "T_MINUS_90M"}:
                if checkpoint.get("state") != "OPEN":
                    continue
                if checkpoint.get("preservation_policy") != (
                    "PRESERVE_AS_OPEN_AND_NEVER_EXECUTE_EARLY"
                ):
                    problems.append(
                        f"contest {row.get('ncaa_contest_id')} lost the {identifier}"
                        " early-execution prohibition"
                    )

    if gate.get("protected_lane_opened") is not False:
        problems.append("the protected lane must remain closed")
    if gate.get("protected_lane") != "RETAIN_PROTECTED_LANE_BLOCKED":
        problems.append("the protected lane declaration drifted")
    identity = dict(gate)
    committed_identity = identity.pop("gate_identity", None)
    if committed_identity != sha256_of(identity):
        problems.append("the gate identity does not reproduce from the gate body")
    if gate.get("forbidden_seasons_compared") != 0:
        problems.append("a sealed season entered the comparison set")
    if sorted(gate.get("season_scope", {}).get("forbidden_seasons", [])) != [2024, 2025]:
        problems.append("the sealed-season declaration drifted")

    for block in ("authority", "scientific_nonclaims"):
        for name, asserted in sorted((gate.get(block) or {}).items()):
            if asserted:
                problems.append(f"the gate asserts the prohibited claim {block}.{name}")

    for required in (
        "bas_or_aggie_excess",
        "causal_effect",
        "champion_or_production_selection",
        "gap_002_closed_by_this_benchmark",
        "new_frozen_or_scorable_coverage_created",
        "retroactive_forecast_created",
    ):
        if required not in (gate.get("scientific_nonclaims") or {}):
            problems.append(f"the gate dropped the required non-claim {required}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    args = parser.parse_args()

    data_root = os.environ.get("AGGIE_ANALYTICS_DATA_ROOT")
    if not data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT must be mounted", file=sys.stderr)
        return 2

    gate = json.loads(args.gate.read_text(encoding="utf-8-sig"))
    try:
        rebuilt = build_artifact(
            **load_inputs(
                contract_path=args.contract,
                acquisition_path=args.acquisition,
                targets_path=args.targets,
                data_root=Path(data_root),
            )
        )
    except EntityBenchmarkViolation as error:
        print(f"ENTITY_BENCHMARK_VIOLATION: {error}", file=sys.stderr)
        return 1

    problems = failures_for(gate, rebuilt, Path(data_root))
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    print(f"{ARTIFACT_ID} validated {gate['payload_root_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
