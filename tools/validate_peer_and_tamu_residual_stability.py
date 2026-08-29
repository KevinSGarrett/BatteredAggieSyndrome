"""Independently validate the predeclared peer-cohort and Texas A&M residual stability test.

The validator is read-only. When a data root is mounted it rebuilds the peer cohorts and
re-evaluates every predeclared test from the walk-forward predictions, so the reported verdict
must follow from the contract's own rules rather than from the producer's word.
"""

from __future__ import annotations

import argparse
import json
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
    GATE_RELATIVE,
    ResidualStabilityViolation,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    summary = validate_artifact(repo_root)
    gate = read_json(repo_root / GATE_RELATIVE)
    checks: list[dict[str, object]] = []

    data_root = args.data_root.resolve() if args.data_root else None
    if data_root is None or not data_root.exists():
        checks.append({"check": "FULL_REPLAY", "state": "SKIP_DATA_ROOT_ABSENT"})
        print(json.dumps({**summary, "checks": checks}, indent=2, sort_keys=True))
        return 0

    contract = load_contract(repo_root)
    peer_rule, peer_rule_sha = load_peer_rule(repo_root, contract)
    if peer_rule_sha != gate["peer_cohort_rule_sha256"]:
        raise ResidualStabilityViolation("the preserved peer-cohort rule no longer hashes correctly")
    checks.append({"check": "PEER_COHORT_RULE_PRESERVED", "state": "PASS"})

    walk_forward_contract = load_walk_forward_contract(repo_root)
    candidates, _ = load_candidates(repo_root, walk_forward_contract)
    matrix_gate = read_json(repo_root / MATRIX_GATE_RELATIVE)
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
    committed_members = {
        row["training_window_max_season_exclusive"]: set(row["members"])
        for row in gate["peer_cohorts_by_training_window"]
    }
    for season, cohort in zip(seasons, cohorts):
        rebuilt = {member["canonical_team_id"] for member in cohort["members"]}
        if committed_members.get(season) != rebuilt:
            raise ResidualStabilityViolation(
                f"the committed peer cohort for the {season} window does not rebuild"
            )
    checks.append({"check": "EVERY_PEER_COHORT_REBUILDS", "state": "PASS"})

    peers_by_season = {
        season: {member["canonical_team_id"] for member in cohort["members"]}
        for season, cohort in zip(seasons, cohorts)
    }
    membership = peer_membership_stability(cohorts)
    groups = group_residuals(
        predictions=predictions, contract=contract, peers_by_season=peers_by_season
    )
    summaries = summarize_groups(groups, contract)
    tests, verdict, _ = run_predeclared_tests(
        summaries=summaries, groups=groups, membership=membership, contract=contract
    )

    if verdict != gate["verdict"]:
        raise ResidualStabilityViolation(
            f"the committed verdict {gate['verdict']} does not reproduce; recomputed {verdict}"
        )
    checks.append({"check": "VERDICT_REPRODUCES_FROM_THE_CONTRACT_RULES", "state": "PASS"})

    committed_tests = {row["test_id"]: row["passed"] for row in gate["predeclared_test_results"]}
    for row in tests:
        if committed_tests.get(row["test_id"]) != row["passed"]:
            raise ResidualStabilityViolation(
                f"predeclared test {row['test_id']} does not reproduce its committed outcome"
            )
    checks.append({"check": "EVERY_PREDECLARED_TEST_REPRODUCES", "state": "PASS"})

    tamu = contract["evaluation"]["texas_am_canonical_team_id"]
    if any(row["canonical_team_id"] == tamu for row in groups["PEER_COHORT"]):
        raise ResidualStabilityViolation("Texas A&M appears inside its own peer cohort")
    checks.append({"check": "TEXAS_AM_IS_NOT_ITS_OWN_PEER", "state": "PASS"})

    print(json.dumps({**summary, "checks": checks}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
