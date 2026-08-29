"""Predeclared peer-cohort and Texas A&M residual stability test over 2018-2023.

Every threshold and verdict rule lives in the contract and was committed before any residual
was computed. The peer-cohort rule is loaded verbatim from Cycle #20 and rebuilt per training
window, so no program is hand-picked and membership churn is measurable rather than assumed.
"""

from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from aggie_analytics.modeling.national_expectation_baselines import (
    ROUND_DIGITS,
    bootstrap_interval,
    build_peer_cohort,
)

SCHEMA_VERSION = "aggie.models.peer_and_tamu_residual_stability.v1"
CONTRACT_ID = "BAT-669-PEER-AND-TAMU-RESIDUAL-STABILITY-V1"
CLASSIFICATION = "PREDECLARED_PEER_COHORT_AND_TEXAS_AM_RESIDUAL_STABILITY_TEST_2018_THROUGH_2023"
LANE = "NATIONAL_DEVELOPMENT_EVALUATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
JIRA_KEY = "BAT-669"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-PEER-AND-TAMU-RESIDUAL-STABILITY-001"
PRODUCER = "tools/build_peer_and_tamu_residual_stability.py"

CONTRACT_RELATIVE = "configs/peer_and_tamu_residual_stability_contract.json"
GATE_RELATIVE = "artifacts/experimentation/peer_and_tamu_residual_stability_gate.json"
EVIDENCE_RELATIVE = "artifacts/experimentation/peer_and_tamu_residual_stability_replay.json"
WALK_FORWARD_GATE_RELATIVE = "artifacts/experimentation/national_multi_year_walk_forward_gate.json"

PASS_RESULT = "PASS_PEER_AND_TAMU_RESIDUAL_STABILITY_DEVELOPMENT_ONLY_NO_CLAIM"

NON_AUTHORITATIVE_KEYS = frozenset({"gate_identity"})
NULL_OR_UNSTABLE_VERDICTS = frozenset(
    {
        "INSUFFICIENT_EVIDENCE",
        "NULL_INDISTINGUISHABLE_FROM_PEERS",
        "NULL_NOT_SEPARABLE_FROM_ZERO",
        "UNSTABLE_DEPENDS_ON_A_SINGLE_SEASON",
        "UNSTABLE_PEER_MEMBERSHIP_CHURNS",
        "UNSTABLE_SIGN_FLIPS_ACROSS_SEASONS",
    }
)


class ResidualStabilityViolation(RuntimeError):
    """Raised when the stability input or artifact is not admissible."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _round(value: float | None) -> float | None:
    return None if value is None else round(float(value), ROUND_DIGITS)


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / CONTRACT_RELATIVE
    if not path.exists():
        raise ResidualStabilityViolation(f"the residual stability contract is missing at {path}")
    contract = read_json(path)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ResidualStabilityViolation("the residual stability contract identifier does not match")
    if not contract["predeclaration"]["declared_before_reading_any_2018_2023_residual"]:
        raise ResidualStabilityViolation("the contract does not assert predeclaration")
    return contract


def load_peer_rule(repo_root: Path, contract: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    """Load the Cycle #20 peer-cohort rule verbatim and hash it so preservation is provable."""

    source = contract["peer_cohort_rule_source"]
    path = Path(repo_root) / source["contract_relative_path"]
    if not path.exists():
        raise ResidualStabilityViolation("the Cycle #20 peer-cohort contract is missing")
    predecessor = read_json(path)
    if predecessor.get("contract_id") != source["contract_id"]:
        raise ResidualStabilityViolation("the Cycle #20 peer-cohort contract identifier drifted")
    rule = predecessor["peer_cohort_rule"]
    if rule.get("seeded_from_famous_programs"):
        raise ResidualStabilityViolation("the peer-cohort rule seeds from reputation")
    return rule, sha256_of(rule)


def peer_members_for_window(
    *,
    matrix: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    rule: Mapping[str, Any],
    season: int,
) -> dict[str, Any]:
    """Rebuild the unchanged Cycle #20 cohort from one training window only."""

    window = [
        {**row, "partition": "TRAINING"} for row in matrix if int(row["season"]) < int(season)
    ]
    cohort = build_peer_cohort(
        matrix=window, labels=labels, contract={"peer_cohort_rule": rule}
    )
    cohort["training_window_max_season_exclusive"] = int(season)
    return cohort


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    if not union:
        return 1.0
    return len(left & right) / len(union)


def peer_membership_stability(cohorts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    memberships = [
        {member["canonical_team_id"] for member in cohort["members"]} for cohort in cohorts
    ]
    pairs = [jaccard(left, right) for left, right in combinations(memberships, 2)]
    always = set.intersection(*memberships) if memberships else set()
    ever = set.union(*memberships) if memberships else set()
    return {
        "cohorts_compared": len(memberships),
        "mean_pairwise_jaccard": _round(float(np.mean(pairs))) if pairs else 1.0,
        "members_present_in_every_window": len(always),
        "members_present_in_some_window": len(ever),
        "minimum_pairwise_jaccard": _round(float(np.min(pairs))) if pairs else 1.0,
    }


def group_residuals(
    *,
    predictions: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
    peers_by_season: Mapping[int, set[str]],
) -> dict[str, list[dict[str, Any]]]:
    """Split the reference candidate's residuals into the three predeclared groups."""

    reference = contract["reference_candidate"]["candidate_id"]
    tamu = contract["evaluation"]["texas_am_canonical_team_id"]
    rows = [row for row in predictions if row["candidate_id"] == reference]
    if not rows:
        raise ResidualStabilityViolation(
            f"the reference candidate {reference} has no predictions to residualize"
        )

    groups: dict[str, list[dict[str, Any]]] = {"NATIONAL": [], "PEER_COHORT": [], "TEXAS_AM": []}
    for row in rows:
        season = int(row["evaluation_season"])
        record = {
            "canonical_game_id": row["canonical_game_id"],
            "canonical_team_id": row["canonical_team_id"],
            "residual": float(row["target"]) - float(row["predicted_win_probability"]),
            "season": season,
        }
        groups["NATIONAL"].append(record)
        if row["canonical_team_id"] in peers_by_season.get(season, set()):
            groups["PEER_COHORT"].append(record)
        if row["canonical_team_id"] == tamu:
            groups["TEXAS_AM"].append(record)
    return groups


def _summarize(records: Sequence[Mapping[str, Any]], bootstrap: Mapping[str, Any]) -> dict[str, Any]:
    if not records:
        return {
            "mean_absolute_residual": None,
            "mean_residual": None,
            "residual_bootstrap": None,
            "rows": 0,
        }
    values = np.array([row["residual"] for row in records], dtype=np.float64)
    return {
        "mean_absolute_residual": _round(float(np.mean(np.abs(values)))),
        "mean_residual": _round(float(np.mean(values))),
        "residual_bootstrap": bootstrap_interval(
            values,
            [row["canonical_game_id"] for row in records],
            resamples=int(bootstrap["resamples"]),
            seed=int(bootstrap["seed"]),
        ),
        "rows": len(records),
    }


def summarize_groups(
    groups: Mapping[str, Sequence[Mapping[str, Any]]], contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    evaluation = contract["evaluation"]
    bootstrap = evaluation["bootstrap"]
    summaries: list[dict[str, Any]] = []
    for name in evaluation["comparison_groups"]:
        records = groups[name]
        per_season = []
        for season in evaluation["seasons"]:
            season_rows = [row for row in records if row["season"] == int(season)]
            per_season.append(
                {"season": int(season), **_summarize(season_rows, bootstrap)}
            )
        summaries.append(
            {"aggregate": _summarize(records, bootstrap), "group": name, "per_season": per_season}
        )
    return summaries


def paired_difference(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
    bootstrap: Mapping[str, Any],
) -> dict[str, Any]:
    """Bootstrap the difference of two group means by resampling games within each group."""

    if not left or not right:
        return {"difference": None, "interval_excludes_zero": False, "rows": [len(left), len(right)]}
    generator = np.random.default_rng(int(bootstrap["seed"]))
    resamples = int(bootstrap["resamples"])

    def prepare(records: Sequence[Mapping[str, Any]]) -> tuple[np.ndarray, list[np.ndarray]]:
        values = np.array([row["residual"] for row in records], dtype=np.float64)
        index: dict[str, list[int]] = {}
        for position, row in enumerate(records):
            index.setdefault(row["canonical_game_id"], []).append(position)
        return values, [np.array(index[key]) for key in sorted(index)]

    left_values, left_games = prepare(left)
    right_values, right_games = prepare(right)
    draws = np.empty(resamples, dtype=np.float64)
    for draw in range(resamples):
        left_pick = np.concatenate(
            [left_games[i] for i in generator.integers(0, len(left_games), len(left_games))]
        )
        right_pick = np.concatenate(
            [right_games[i] for i in generator.integers(0, len(right_games), len(right_games))]
        )
        draws[draw] = float(np.mean(left_values[left_pick]) - np.mean(right_values[right_pick]))
    low = float(np.percentile(draws, 2.5))
    high = float(np.percentile(draws, 97.5))
    return {
        "bootstrap_unit": "GAME",
        "difference": _round(float(np.mean(left_values) - np.mean(right_values))),
        "interval_excludes_zero": bool(low > 0.0 or high < 0.0),
        "percentile_2_5": _round(low),
        "percentile_97_5": _round(high),
        "resamples": resamples,
        "rows": [len(left), len(right)],
    }


def leave_one_season_out(
    records: Sequence[Mapping[str, Any]], seasons: Sequence[int]
) -> list[dict[str, Any]]:
    refits = []
    for season in seasons:
        kept = [row for row in records if row["season"] != int(season)]
        mean = float(np.mean([row["residual"] for row in kept])) if kept else None
        refits.append(
            {
                "mean_residual_without_this_season": _round(mean),
                "rows": len(kept),
                "season_removed": int(season),
                "sign": _sign(mean),
            }
        )
    return refits


def _sign(value: float | None) -> str:
    if value is None:
        return "UNDEFINED"
    if value > 0:
        return "POSITIVE"
    if value < 0:
        return "NEGATIVE"
    return "ZERO"


def run_predeclared_tests(
    *,
    summaries: Sequence[Mapping[str, Any]],
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
    membership: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """Evaluate every predeclared test and map the outcome onto a contract verdict."""

    evaluation = contract["evaluation"]
    seasons = [int(season) for season in evaluation["seasons"]]
    by_group = {row["group"]: row for row in summaries}
    tamu = by_group["TEXAS_AM"]
    declared = {row["test_id"]: row for row in contract["predeclared_tests"]}

    aggregate_rows = tamu["aggregate"]["rows"]
    qualifying = [
        row
        for row in tamu["per_season"]
        if row["rows"] >= int(declared["T2_MINIMUM_PER_SEASON_SAMPLE"]["per_season_threshold"])
    ]
    signs = [_sign(row["mean_residual"]) for row in tamu["per_season"] if row["rows"] > 0]
    dominant = max(set(signs), key=signs.count) if signs else "UNDEFINED"
    matching = signs.count(dominant)

    interval = tamu["aggregate"]["residual_bootstrap"] or {}
    separated = bool(
        interval
        and (interval["percentile_2_5"] > 0.0 or interval["percentile_97_5"] < 0.0)
    )
    contrast = paired_difference(
        groups["TEXAS_AM"], groups["PEER_COHORT"], evaluation["bootstrap"]
    )
    refits = leave_one_season_out(groups["TEXAS_AM"], seasons)
    aggregate_sign = _sign(tamu["aggregate"]["mean_residual"])
    refits_agree = sum(1 for row in refits if row["sign"] == aggregate_sign)

    results = [
        {
            "observed": {"aggregate_texas_am_rows": aggregate_rows},
            "passed": aggregate_rows >= int(declared["T1_MINIMUM_AGGREGATE_SAMPLE"]["threshold"]),
            "test_id": "T1_MINIMUM_AGGREGATE_SAMPLE",
        },
        {
            "observed": {
                "qualifying_seasons": len(qualifying),
                "rows_per_season": {
                    str(row["season"]): row["rows"] for row in tamu["per_season"]
                },
            },
            "passed": len(qualifying)
            >= int(declared["T2_MINIMUM_PER_SEASON_SAMPLE"]["qualifying_seasons_required"]),
            "test_id": "T2_MINIMUM_PER_SEASON_SAMPLE",
        },
        {
            "observed": {
                "dominant_sign": dominant,
                "matching_seasons": matching,
                "sign_by_season": {
                    str(row["season"]): _sign(row["mean_residual"])
                    for row in tamu["per_season"]
                },
            },
            "passed": matching
            >= int(declared["T3_SIGN_PERSISTENCE"]["matching_seasons_required"]),
            "test_id": "T3_SIGN_PERSISTENCE",
        },
        {
            "observed": {"aggregate_bootstrap": interval},
            "passed": separated,
            "test_id": "T4_AGGREGATE_SEPARATION_FROM_ZERO",
        },
        {
            "observed": {"texas_am_minus_peer_cohort": contrast},
            "passed": bool(contrast["interval_excludes_zero"]),
            "test_id": "T5_PEER_CONTRAST",
        },
        {
            "observed": {"aggregate_sign": aggregate_sign, "refits": refits},
            "passed": refits_agree
            >= int(declared["T6_LEAVE_ONE_SEASON_OUT_ROBUSTNESS"]["refits_required_to_agree"]),
            "test_id": "T6_LEAVE_ONE_SEASON_OUT_ROBUSTNESS",
        },
        {
            "observed": membership,
            "passed": float(membership["mean_pairwise_jaccard"])
            >= float(declared["T7_PEER_MEMBERSHIP_STABILITY"]["threshold"]),
            "test_id": "T7_PEER_MEMBERSHIP_STABILITY",
        },
    ]
    results.sort(key=lambda row: row["test_id"])

    failed = {row["test_id"] for row in results if not row["passed"]}
    if not failed:
        verdict = "STABLE_PERSISTENT_RESIDUAL_DETECTED"
    else:
        candidates = {declared[test_id]["failure_verdict"] for test_id in failed}
        verdict = next(
            name for name in contract["verdict_precedence"] if name in candidates
        )

    return results, verdict, {"leave_one_season_out": refits, "peer_contrast": contrast}


def build_gate(
    *,
    summaries: Sequence[Mapping[str, Any]],
    cohorts: Sequence[Mapping[str, Any]],
    membership: Mapping[str, Any],
    tests: Sequence[Mapping[str, Any]],
    verdict: str,
    sensitivity: Mapping[str, Any],
    contract: Mapping[str, Any],
    peer_rule_sha256: str,
    predecessor_identities: Mapping[str, Any],
    producer: str = PRODUCER,
) -> dict[str, Any]:
    if verdict not in contract["verdict_rules"]:
        raise ResidualStabilityViolation(f"verdict {verdict} is not declared in the contract")

    bundle = {
        "artifact_type": "PEER_AND_TAMU_RESIDUAL_STABILITY_GATE",
        "authority": {
            "causal_effect_established": False,
            "champion_or_production_promotion": False,
            "national_model_tuned_on_texas_am": False,
            "peer_cohort_hand_picked": False,
            "protected_performance_claimed": False,
            "residual_stability_development_test": True,
        },
        "bound_predecessor_identities": dict(sorted(predecessor_identities.items())),
        "classification": CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_of(contract),
        "decision_unit": LOCAL_ISSUE_ID,
        "evaluation_seasons": [int(season) for season in contract["evaluation"]["seasons"]],
        "jira_key": JIRA_KEY,
        "lane": LANE,
        "local_issue_id": LOCAL_ISSUE_ID,
        "parent_jira_key": PARENT_JIRA_KEY,
        "peer_cohort_rule_sha256": peer_rule_sha256,
        "peer_cohorts_by_training_window": [
            {
                "cohort_size": cohort["cohort_size"],
                "eligible_programs": cohort["eligible_programs"],
                "members": sorted(
                    member["canonical_team_id"] for member in cohort["members"]
                ),
                "training_window_max_season_exclusive": cohort[
                    "training_window_max_season_exclusive"
                ],
            }
            for cohort in cohorts
        ],
        "peer_membership_stability": membership,
        "predeclaration": contract["predeclaration"],
        "predeclared_test_results": list(tests),
        "producer": producer,
        "protected_lane": PROTECTED_LANE,
        "reference_candidate": contract["reference_candidate"]["candidate_id"],
        "residual_definition": contract["residual_definition"],
        "residual_summaries": list(summaries),
        "result": PASS_RESULT,
        "schema_version": SCHEMA_VERSION,
        "scientific_nonclaims": contract["scientific_nonclaims"],
        "sensitivity": dict(sensitivity),
        "verdict": verdict,
        "verdict_meaning": contract["verdict_rules"][verdict],
    }
    bundle["gate_identity"] = gate_identity_of(bundle)
    return bundle


def gate_identity_of(bundle: Mapping[str, Any]) -> str:
    return sha256_of({k: v for k, v in bundle.items() if k not in NON_AUTHORITATIVE_KEYS})


def validate_artifact(repo_root: Path, gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Check the committed stability test for consistency and for unauthorized claims."""

    repo_root = Path(repo_root)
    contract = load_contract(repo_root)
    if gate is None:
        gate_path = repo_root / GATE_RELATIVE
        if not gate_path.exists():
            raise ResidualStabilityViolation("the residual stability gate has not been materialized")
        gate = read_json(gate_path)

    if gate.get("schema_version") != SCHEMA_VERSION:
        raise ResidualStabilityViolation("the committed gate schema version does not match")
    if gate.get("contract_sha256") != sha256_of(contract):
        raise ResidualStabilityViolation("the committed gate is bound to a different contract body")
    if gate_identity_of(gate) != gate.get("gate_identity"):
        raise ResidualStabilityViolation("the committed gate identity does not cover its content")

    _, expected = load_peer_rule(repo_root, contract)
    if gate.get("peer_cohort_rule_sha256") != expected:
        raise ResidualStabilityViolation(
            "the committed peer-cohort rule does not match the preserved Cycle #20 rule"
        )

    declared = {row["test_id"] for row in contract["predeclared_tests"]}
    observed = {row["test_id"] for row in gate.get("predeclared_test_results", [])}
    if observed != declared:
        raise ResidualStabilityViolation(
            "the reported tests do not cover exactly the predeclared test set"
        )

    verdict = gate.get("verdict")
    if verdict not in contract["verdict_rules"]:
        raise ResidualStabilityViolation("the gate reports an undeclared verdict")
    failed = {row["test_id"] for row in gate["predeclared_test_results"] if not row["passed"]}
    if verdict == "STABLE_PERSISTENT_RESIDUAL_DETECTED" and failed:
        raise ResidualStabilityViolation(
            "the gate claims a stable persistent residual while predeclared tests failed"
        )
    if verdict in NULL_OR_UNSTABLE_VERDICTS and not failed:
        raise ResidualStabilityViolation(
            "the gate reports a null or unstable verdict while every test passed"
        )

    if gate.get("protected_lane") != PROTECTED_LANE:
        raise ResidualStabilityViolation("the test does not retain the blocked protected lane")
    for key, value in gate.get("authority", {}).items():
        if key != "residual_stability_development_test" and value:
            raise ResidualStabilityViolation(f"the gate asserts unauthorized authority: {key}")
    for key, value in gate.get("scientific_nonclaims", {}).items():
        if value:
            raise ResidualStabilityViolation(f"the gate makes a forbidden claim: {key}")

    forbidden = set(contract["evaluation"]["forbidden_seasons"])
    if forbidden.intersection(gate.get("evaluation_seasons", [])):
        raise ResidualStabilityViolation("a forbidden season appears in the evaluation set")

    return {
        "gate_identity": gate["gate_identity"],
        "peer_membership_mean_jaccard": gate["peer_membership_stability"][
            "mean_pairwise_jaccard"
        ],
        "result": gate["result"],
        "test_results": {
            row["test_id"]: row["passed"] for row in gate["predeclared_test_results"]
        },
        "texas_am_aggregate": next(
            row["aggregate"] for row in gate["residual_summaries"] if row["group"] == "TEXAS_AM"
        ),
        "verdict": verdict,
    }
