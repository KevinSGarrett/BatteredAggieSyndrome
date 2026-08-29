"""Materialize the predeclared peer-cohort and Texas A&M residual stability test.

The build is fully offline. It replays the BAT-668 walk-forward predictions, rebuilds the
unchanged Cycle #20 peer cohort once per training window, and evaluates every predeclared test.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.modeling.national_multi_year_walk_forward import (  # noqa: E402
    MATRIX_GATE_RELATIVE,
    load_candidates,
    run_walk_forward,
)
from aggie_analytics.modeling.national_multi_year_walk_forward import (  # noqa: E402
    load_contract as load_walk_forward_contract,
)
from aggie_analytics.modeling.peer_and_tamu_residual_stability import (  # noqa: E402
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    WALK_FORWARD_GATE_RELATIVE,
    build_gate,
    group_residuals,
    load_contract,
    load_peer_rule,
    peer_membership_stability,
    peer_members_for_window,
    read_json,
    read_jsonl,
    run_predeclared_tests,
    summarize_groups,
    validate_artifact,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_national_multi_year_walk_forward import matrix_dir, require  # noqa: E402


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    repo_root, data_root = args.repo_root.resolve(), args.data_root.resolve()
    if args.validate_only:
        print(json.dumps(validate_artifact(repo_root), indent=2, sort_keys=True))
        return 0

    contract = load_contract(repo_root)
    peer_rule, peer_rule_sha = load_peer_rule(repo_root, contract)

    walk_forward_contract = load_walk_forward_contract(repo_root)
    candidates, _ = load_candidates(repo_root, walk_forward_contract)
    matrix_gate = read_json(repo_root / MATRIX_GATE_RELATIVE)
    walk_forward_gate = read_json(repo_root / WALK_FORWARD_GATE_RELATIVE)

    base = matrix_dir(data_root, matrix_gate["dataset_identity"])
    matrix = read_jsonl(require(base / "national_development_matrix_features.jsonl"))
    labels = read_jsonl(require(base / "national_development_matrix_labels.jsonl"))

    predictions, _ = run_walk_forward(
        matrix=matrix, labels=labels, candidates=candidates, contract=walk_forward_contract
    )

    seasons = [int(season) for season in contract["evaluation"]["seasons"]]
    cohorts = [
        peer_members_for_window(matrix=matrix, labels=labels, rule=peer_rule, season=season)
        for season in seasons
    ]
    peers_by_season = {
        season: {member["canonical_team_id"] for member in cohort["members"]}
        for season, cohort in zip(seasons, cohorts)
    }
    membership = peer_membership_stability(cohorts)

    groups = group_residuals(
        predictions=predictions, contract=contract, peers_by_season=peers_by_season
    )
    summaries = summarize_groups(groups, contract)
    tests, verdict, sensitivity = run_predeclared_tests(
        summaries=summaries, groups=groups, membership=membership, contract=contract
    )

    gate = build_gate(
        summaries=summaries,
        cohorts=cohorts,
        membership=membership,
        tests=tests,
        verdict=verdict,
        sensitivity=sensitivity,
        contract=contract,
        peer_rule_sha256=peer_rule_sha,
        predecessor_identities={
            "national_chronological_development_matrix_gate_identity": matrix_gate.get(
                "gate_identity"
            ),
            "national_multi_year_walk_forward_gate_identity": walk_forward_gate.get(
                "gate_identity"
            ),
        },
    )

    write_json(repo_root / GATE_RELATIVE, gate)
    write_json(
        repo_root / EVIDENCE_RELATIVE,
        {
            "artifact_type": "PEER_AND_TAMU_RESIDUAL_STABILITY_REPLAY",
            "contract_id": gate["contract_id"],
            "gate_identity": gate["gate_identity"],
            "gate_relative_path": GATE_RELATIVE,
            "peer_cohort_rule_sha256": gate["peer_cohort_rule_sha256"],
            "reproduction": [
                "python tools/build_peer_and_tamu_residual_stability.py"
                " --repo-root . --data-root <data-root>",
                "python tools/validate_peer_and_tamu_residual_stability.py"
                " --repo-root . --data-root <data-root>",
            ],
            "schema_version": "aggie.models.peer_and_tamu_residual_stability_replay.v1",
            "verdict": gate["verdict"],
        },
    )
    print(json.dumps(validate_artifact(repo_root, gate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
