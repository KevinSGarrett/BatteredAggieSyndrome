from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence, assert_never

import numpy as np

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    canonical_json_bytes,
    sha256_file,
    stable_hash,
)
from aggie_analytics.modeling import national_expectation_baselines as baselines

SCHEMA_VERSION = "aggie.shadow.week1_2026_forecast_input_binding_successor.v1"
CONTRACT_ID = "CYCLE25-WEEK1-2026-FORECAST-INPUT-BINDING-SUCCESSOR-V1"
REVIEW_CONTRACT_ID = "CYCLE25-WEEK1-2026-CYCLE24-BINDING-REVIEW-V1"
JIRA_KEY = "BAT-686"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-FORECAST-INPUT-BINDING-SUCCESSOR-001"
PARENT_JIRA_KEY = "BAT-523"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_FORECAST_INPUT_BINDING_SUCCESSOR"
REVIEW_PASS_RESULT = "PASS_WEEK1_2026_CYCLE24_BINDING_REVIEW"
CLASSIFICATION = "WEEK1_2026_FORECAST_INPUT_BINDING_SUCCESSOR"
REVIEW_CLASSIFICATION = "WEEK1_2026_CYCLE24_MODEL_INPUT_BINDING_REVIEW"

CONTRACT_RELATIVE = "configs/week1_2026_forecast_input_binding_successor_contract.json"
REVIEW_CONTRACT_RELATIVE = "configs/week1_2026_cycle24_binding_review_contract.json"
GATE_RELATIVE = (
    "artifacts/forecast/week1_2026_forecast_input_binding_successor_gate.json"
)
REVIEW_GATE_RELATIVE = "artifacts/forecast/week1_2026_cycle24_binding_review_gate.json"
PAYLOAD_SLUG = "week1_2026_forecast_input_binding_successor"

PROTECTED_SPLIT = "governance/PROTECTED_SPLIT_REGISTRY.csv"
PROTECTED_JUDGING_CSV = "governance/PROTECTED_JUDGING_RULE_SEAL.csv"
JUDGING_RULE_JSON = "configs/judging_rule_seal.json"

READY = "FORECAST_READY_BOUND_INPUTS_HAVE_TRAINING_ANALOGUES"
ABSTAIN_FEATURES = "ABSTAIN_MISSING_REQUIRED_FEATURES"
ABSTAIN_ENTITY = "ABSTAIN_UNSUPPORTED_ENTITY"
ABSTAIN_AUTHORITY = "ABSTAIN_FEATURE_AUTHORITY_MISMATCH"
LIMITED = "LIMITED_STALE_INPUT_SHADOW_ONLY"

RankingCycle24State = Literal[
    "RANKED_TOP_25",
    "FBS_POLL_ELIGIBLE_UNRANKED",
    "NOT_APPLICABLE_FBS_POLL",
]


class BindingSuccessorViolation(ValueError):
    """Raised when the Cycle #25 binding successor cannot be materialized."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def payload_rows(
    data_root: Path, gate: Mapping[str, Any], name: str
) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise BindingSuccessorViolation(f"source payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = read_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise BindingSuccessorViolation("successor contract identity drifted")
    if contract.get("jira_key") != JIRA_KEY:
        raise BindingSuccessorViolation("successor jira key drifted")
    if contract["checkpoints"]["t_minus_24h_state"] != "OPEN":
        raise BindingSuccessorViolation("T-24H is not OPEN")
    if contract["checkpoints"]["t_minus_90m_state"] != "OPEN":
        raise BindingSuccessorViolation("T-90M is not OPEN")
    if contract["checkpoints"]["market_values_inspected"] is not False:
        raise BindingSuccessorViolation("market values were inspected before freeze")
    if contract["deployment_fit"]["excluded_protected_seasons"] != [2024, 2025]:
        raise BindingSuccessorViolation("protected seasons must remain excluded")
    if contract["deployment_fit"]["refit_fitted_families"] is not False:
        raise BindingSuccessorViolation(
            "fitted families must not be refit in this successor"
        )
    return contract


def load_review_contract(repo_root: Path) -> dict[str, Any]:
    contract = read_json(repo_root / REVIEW_CONTRACT_RELATIVE)
    if contract.get("contract_id") != REVIEW_CONTRACT_ID:
        raise BindingSuccessorViolation("review contract identity drifted")
    return contract


def protected_hash_labels(repo_root: Path) -> dict[str, str]:
    split = sha256_file(repo_root / PROTECTED_SPLIT)
    judging_csv = sha256_file(repo_root / PROTECTED_JUDGING_CSV)
    judging_json = sha256_file(repo_root / JUDGING_RULE_JSON)
    labels = {
        "protected_split_registry_path": PROTECTED_SPLIT,
        "protected_split_registry_sha256": split,
        "protected_judging_rule_seal_csv_path": PROTECTED_JUDGING_CSV,
        "protected_judging_rule_seal_csv_sha256": judging_csv,
        "judging_rule_seal_json_path": JUDGING_RULE_JSON,
        "judging_rule_seal_json_sha256": judging_json,
    }
    if len({split, judging_csv, judging_json}) != 3:
        raise BindingSuccessorViolation("protected artifact hashes are not distinct")
    if judging_csv == judging_json:
        raise BindingSuccessorViolation(
            "governance CSV hash was conflated with the JSON seal"
        )
    return labels


def map_ranking_surface_state(state: str) -> str:
    if state == "RANKED_TOP_25":
        typed: RankingCycle24State = "RANKED_TOP_25"
    elif state == "FBS_POLL_ELIGIBLE_UNRANKED":
        typed = "FBS_POLL_ELIGIBLE_UNRANKED"
    elif state == "NOT_APPLICABLE_FBS_POLL":
        typed = "NOT_APPLICABLE_FBS_POLL"
    else:
        return "SOURCE_MISSING"
    if typed == "RANKED_TOP_25":
        return "TEAM_RANKED"
    if typed == "FBS_POLL_ELIGIBLE_UNRANKED":
        return "TEAM_UNRANKED_FBS"
    if typed == "NOT_APPLICABLE_FBS_POLL":
        return "FCS_NOT_APPLICABLE"
    assert_never(typed)


def terminal_prior_index(
    matrix_rows: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    last: dict[str, dict[str, Any]] = {}
    for row in matrix_rows:
        if int(row["season"]) > 2023:
            continue
        team_id = str(row["canonical_team_id"])
        previous = last.get(team_id)
        if previous is None or int(row["chronological_ordinal"]) > int(
            previous["chronological_ordinal"]
        ):
            last[team_id] = dict(row)
    return last


def ridge_saturation_audit(
    predictions: Sequence[Mapping[str, Any]],
    *,
    clip: Sequence[float],
) -> dict[str, Any]:
    ridge = [
        row for row in predictions if row["candidate_id"] == "national_margin_ridge"
    ]
    if not ridge:
        raise BindingSuccessorViolation("ridge development predictions are absent")
    probabilities = np.array(
        [float(row["predicted_win_probability"]) for row in ridge], dtype=np.float64
    )
    outcomes = np.array(
        [1.0 if row["observed_win"] else 0.0 for row in ridge], dtype=np.float64
    )
    margins = np.array(
        [float(row["predicted_margin"]) for row in ridge], dtype=np.float64
    )
    observed_margins = np.array(
        [float(row["observed_margin"]) for row in ridge], dtype=np.float64
    )
    scored = baselines.score_predictions(
        probabilities, outcomes, clip=clip, bin_count=10
    )
    low = float(clip[0])
    high = float(clip[1])
    return {
        "candidate_id": "national_margin_ridge",
        "development_row_count": int(len(ridge)),
        "probability_min": round(float(np.min(probabilities)), 8),
        "probability_max": round(float(np.max(probabilities)), 8),
        "probability_mean": round(float(np.mean(probabilities)), 8),
        "proportion_below_0_01": round(float(np.mean(probabilities < 0.01)), 8),
        "proportion_above_0_99": round(float(np.mean(probabilities > 0.99)), 8),
        "proportion_at_or_beyond_clip": round(
            float(np.mean((probabilities <= low) | (probabilities >= high))), 8
        ),
        "brier": scored["brier"],
        "log_loss": scored["log_loss"],
        "calibration_intercept": scored.get("calibration_intercept"),
        "calibration_slope": scored.get("calibration_slope"),
        "reliability_bins": scored["calibration_bins"],
        "expected_margin_mean": round(float(np.mean(margins)), 8),
        "expected_margin_stdev": round(float(np.std(margins)), 8),
        "margin_mae": round(float(np.mean(np.abs(margins - observed_margins))), 8),
        "clip": [low, high],
        "mapping_changed": False,
        "changed_because_of_a_and_m_or_market_or_week1_outcome": False,
    }


def _counts(values: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def classify_cycle24_findings(
    *,
    contract: Mapping[str, Any],
    feature_rows: Sequence[Mapping[str, Any]],
    adequacy_rows: Sequence[Mapping[str, Any]],
    early_rows: Sequence[Mapping[str, Any]],
    ridge_audit: Mapping[str, Any],
    labels: Mapping[str, str],
    review_contract: Mapping[str, Any],
) -> list[dict[str, Any]]:
    fitted_ids = {"prior_only", "national_logistic_l2", "national_margin_ridge"}
    principal = list(contract["principal_performance_features"])
    all_principal_missing = all(
        all((row.get("feature_values") or {}).get(name) is None for name in principal)
        for row in feature_rows
    )
    hardcoded_true = all(
        (row.get("feature_values") or {}).get("rankings_source_available") is True
        for row in feature_rows
    )
    opening_in_design = any(
        "opening_rating" in (baselines.FEATURE_SCOPES[scope][0])
        for scope in ("PRIOR_OUTCOME_DOMAIN_AND_SITE", "ALL_ADMITTED_FEATURES")
    )
    domain_absent_prior_admitted = sum(
        1
        for row in feature_rows
        if row.get("prior_admitted")
        and (row.get("domain_admission_states") or {}).get("TEAM_STRENGTH_PRIOR")
        == "SOURCE_EVIDENCE_ABSENT"
    )
    ranking_absent_but_consumed = sum(
        1
        for row in feature_rows
        if (row.get("domain_admission_states") or {}).get("CURRENT_RANKING")
        in {"SOURCE_EVIDENCE_ABSENT", "CANDIDATE_ONLY_NOT_CONSUMED"}
        and (row.get("feature_values") or {}).get("rankings_source_available") is True
    )
    frozen = [row for row in early_rows if row.get("row_state") == "FORECAST_FROZEN"]
    ready_fitted = [
        row
        for row in adequacy_rows
        if row["candidate_id"] in fitted_ids
        and row["readiness_state"] == "FORECAST_READY_ALL_REQUIRED_FEATURES_ADMITTED"
    ]
    csv_hash = labels["protected_judging_rule_seal_csv_sha256"]
    json_hash = labels["judging_rule_seal_json_sha256"]
    expected_csv = review_contract["protected_hash_labels"][
        "protected_judging_rule_seal_csv_sha256"
    ]
    expected_json = review_contract["protected_hash_labels"][
        "judging_rule_seal_json_sha256"
    ]
    findings = [
        {
            "finding_id": "A_OPENING_RATING_NOT_CONSUMED_BY_FITTED_MODELS",
            "disposition": "CONFIRMED",
            "evidence": {
                "opening_rating_present_on_week1_rows": all(
                    row.get("opening_rating") is not None
                    or not row.get("prior_admitted")
                    for row in feature_rows
                ),
                "opening_rating_in_fitted_design_matrix": opening_in_design,
                "fitted_scopes": [
                    "PRIOR_OUTCOME_DOMAIN_AND_SITE",
                    "ALL_ADMITTED_FEATURES",
                ],
                "elo_family_consumes_opening_rating": True,
            },
        },
        {
            "finding_id": "B_STRENGTH_PRIOR_DOMAIN_STATE_CONTRADICTION",
            "disposition": "CONFIRMED",
            "controlling_authority": "prior_admitted",
            "evidence": {
                "rows_prior_admitted_while_domain_source_evidence_absent": domain_absent_prior_admitted,
                "effective_admission_state": "PRIOR_ADMITTED_OVERRIDES_SPINE_DOMAIN_LABEL",
            },
        },
        {
            "finding_id": "C_RANKING_CANDIDATE_ONLY_CONSUMPTION",
            "disposition": "CONFIRMED",
            "bat683_promoted_ranking_surface": True,
            "successor_effective_authority": "EFFECTIVE_AUTHORITY_ADMITTED_BOUND_TO_BAT_683",
            "evidence": {
                "rows_with_absent_or_candidate_only_domain_and_rankings_source_available_true": ranking_absent_but_consumed,
                "cycle24_rows_rewritten": False,
            },
        },
        {
            "finding_id": "D_RANKINGS_SOURCE_AVAILABLE_CONSTANT",
            "disposition": "CONFIRMED",
            "historical_analogue": "poll_snapshot_present_for_the_week",
            "evidence": {
                "all_week1_rows_hardcoded_true": hardcoded_true,
                "separate_surface_states_required": True,
            },
        },
        {
            "finding_id": "E_DOMAIN_READY_BUT_REQUIRED_FIELDS_MISSING",
            "disposition": "CONFIRMED",
            "evidence": {
                "all_oriented_rows_principal_performance_features_none": all_principal_missing,
                "fitted_rows_marked_ready": len(ready_fitted),
                "learned_missingness_is_not_material_presence": True,
            },
        },
        {
            "finding_id": "F_RIDGE_MARGIN_TO_PROBABILITY_SATURATION",
            "disposition": "CONFIRMED",
            "mapping_changed": False,
            "evidence": ridge_audit,
        },
        {
            "finding_id": "G_PROTECTED_HASH_LABEL_DRIFT",
            "disposition": "CONFIRMED",
            "cycle24_report_mislabeled_json_hash_as_governance_csv_hash": True,
            "evidence": {
                "governance_csv_sha256": csv_hash,
                "config_json_sha256": json_hash,
                "expected_governance_csv_sha256": expected_csv,
                "expected_config_json_sha256": expected_json,
                "hashes_match_distinct_expected_values": csv_hash == expected_csv
                and json_hash == expected_json
                and csv_hash != json_hash,
            },
        },
        {
            "finding_id": "H_FULL_SUITE_SIDEARM_FIXTURE_CAVEAT",
            "disposition": "CONFIRMED",
            "test_id": review_contract["sidearm_fixture"]["test_id"],
            "reproduced_on_starting_main": True,
            "trigger": "AGGIE_ANALYTICS_DATA_ROOT present but empty string resolves to Path('.')",
            "remediation": "Skip rebuild when Sidearm schedule HTML is absent from the resolved data root",
        },
    ]
    findings.append(
        {
            "finding_id": "CYCLE24_FORECAST_PRESERVATION",
            "disposition": "CONFIRMED",
            "frozen_row_count": len(frozen),
            "abstained_row_count": len(early_rows) - len(frozen),
            "rewritten": False,
        }
    )
    return findings


def bind_successor_feature_row(
    *,
    cycle24_row: Mapping[str, Any],
    terminal: Mapping[str, Any] | None,
    poll_surface_complete: bool,
    principal: Sequence[str],
) -> dict[str, Any]:
    values = dict(cycle24_row.get("feature_values") or {})
    analogue_bound = False
    if terminal is not None:
        analogue_bound = True
        for feature in (
            *baselines.PRIOR_DOMAIN_NUMERIC,
            "ap_poll_rank",
            "coaches_poll_rank",
            "opponent_ap_poll_rank",
            "opponent_prior_games_played",
            "opponent_prior_win_rate",
            "opponent_prior_margin_mean",
            "opponent_prior_season_win_rate",
            "prior_win_rate_differential",
        ):
            if feature in terminal:
                values[feature] = terminal.get(feature)
                missing_name = f"{feature}_missing"
                if missing_name in values or missing_name in terminal:
                    values[missing_name] = terminal.get(
                        missing_name, terminal.get(feature) is None
                    )
        values["team_conference"] = terminal.get("team_conference")
        values["team_conference_missing"] = terminal.get("team_conference_missing")
        values["team_is_fbs"] = terminal.get("team_is_fbs")
        values["team_is_fbs_missing"] = terminal.get("team_is_fbs_missing")
    values["is_home"] = cycle24_row["site_orientation"] == "HOME"
    values["is_neutral_site"] = cycle24_row["site_orientation"] == "NEUTRAL"
    values["rankings_source_available"] = bool(poll_surface_complete)
    ranking_cycle24 = str(cycle24_row.get("ranking_state") or "SOURCE_MISSING")
    ranking_surface_state = map_ranking_surface_state(ranking_cycle24)
    if ranking_surface_state == "TEAM_RANKED":
        if values.get("ap_poll_rank") == 26:
            raise BindingSuccessorViolation("unranked encoded as rank 26")
    if ranking_surface_state == "FCS_NOT_APPLICABLE":
        values["ap_poll_rank"] = None
        values["ap_poll_rank_missing"] = True
    if ranking_surface_state == "TEAM_UNRANKED_FBS":
        values["ap_poll_rank"] = None
        values["ap_poll_rank_missing"] = True
    principal_present = [name for name in principal if values.get(name) is not None]
    row = {
        "contest_identity": cycle24_row["contest_identity"],
        "ncaa_contest_id": cycle24_row["ncaa_contest_id"],
        "source_team_id": cycle24_row["source_team_id"],
        "canonical_team_id": cycle24_row.get("canonical_team_id"),
        "opponent_source_team_id": cycle24_row.get("opponent_source_team_id"),
        "opponent_canonical_team_id": cycle24_row.get("opponent_canonical_team_id"),
        "site_orientation": cycle24_row["site_orientation"],
        "cycle24_row_identity": cycle24_row["row_identity"],
        "prior_admitted": bool(cycle24_row.get("prior_admitted")),
        "opponent_prior_admitted": bool(cycle24_row.get("opponent_prior_admitted")),
        "opening_rating": cycle24_row.get("opening_rating"),
        "opponent_opening_rating": cycle24_row.get("opponent_opening_rating"),
        "prior_uncertainty_class": cycle24_row.get("prior_uncertainty_class"),
        "cycle24_ranking_state": ranking_cycle24,
        "ranking_surface_state": ranking_surface_state,
        "poll_surface_available": bool(poll_surface_complete),
        "historical_prior_outcome_analogue_bound": analogue_bound,
        "principal_performance_features_present": principal_present,
        "effective_strength_prior_admission": (
            "PRIOR_ADMITTED" if cycle24_row.get("prior_admitted") else "NOT_ADMITTED"
        ),
        "effective_ranking_authority": (
            "EFFECTIVE_AUTHORITY_ADMITTED_BOUND_TO_BAT_683"
            if poll_surface_complete
            else "SOURCE_MISSING"
        ),
        "cycle24_domain_admission_states": cycle24_row.get("domain_admission_states"),
        "feature_values": values,
        "opening_rating_in_fitted_design": False,
    }
    row["row_identity"] = stable_hash(row)
    return row


def score_fitted(
    *,
    family: str,
    scope: str,
    values: Mapping[str, Any],
    design_meta: Mapping[str, Any],
    coefficients: Sequence[float],
    ridge_stdev: float | None,
    ridge_divisor: float | None,
) -> tuple[float, float | None]:
    design, _columns = baselines.build_design(
        [values],
        scope=scope,
        transforms=design_meta["transforms"],
        levels=design_meta["conference_levels"],
        indicators=design_meta["indicators"],
    )
    beta = np.asarray(coefficients, dtype=np.float64)
    if design.shape[1] != beta.shape[0]:
        raise BindingSuccessorViolation(
            f"{family} coefficient length {beta.shape[0]} does not match design {design.shape[1]}"
        )
    if family == "REGULARIZED_LOGISTIC":
        probability = float(baselines.predict_logistic(design, beta)[0])
        return probability, None
    if family == "RIDGE_MARGIN":
        margin = float((design @ beta)[0])
        if ridge_stdev is None or ridge_divisor is None:
            raise BindingSuccessorViolation("ridge mapping parameters are missing")
        link_scale = max(float(ridge_stdev) / float(ridge_divisor), 1e-6)
        probability = float(
            1.0 / (1.0 + math.exp(-float(np.clip(margin / link_scale, -30.0, 30.0))))
        )
        return probability, margin
    raise BindingSuccessorViolation(f"unknown fitted family: {family}")


def elo_probability(
    row: Mapping[str, Any], hyperparameters: Mapping[str, Any]
) -> float:
    own = row.get("opening_rating")
    other = row.get("opponent_opening_rating")
    if own is None or other is None:
        raise BindingSuccessorViolation("elo successor lacks opening ratings")
    advantage = float(hyperparameters["home_advantage_rating"])
    scale = float(hyperparameters["rating_scale"])
    values = row["feature_values"]
    bonus = 0.0
    if not values.get("is_neutral_site"):
        bonus = advantage if values.get("is_home") else -advantage
    return 1.0 / (1.0 + 10.0 ** (-(float(own) + bonus - float(other)) / scale))


def successor_readiness(
    *,
    candidate: Mapping[str, Any],
    feature_row: Mapping[str, Any],
    principal: Sequence[str],
) -> dict[str, Any]:
    reasons: list[str] = []
    family = str(candidate["family"])
    if not feature_row.get("canonical_team_id") or not feature_row.get(
        "opponent_canonical_team_id"
    ):
        state = ABSTAIN_ENTITY
        reasons.append("UNSUPPORTED_ENTITY")
    elif family == "UNFITTED_REFERENCE":
        state = READY
    elif family == "ELO":
        if not (
            feature_row.get("prior_admitted")
            and feature_row.get("opponent_prior_admitted")
            and feature_row.get("opening_rating") is not None
            and feature_row.get("opponent_opening_rating") is not None
        ):
            state = ABSTAIN_FEATURES
            reasons.append("OPENING_RATING_REQUIRED_FOR_ELO")
        else:
            state = READY
    elif family in {"REGULARIZED_LOGISTIC", "RIDGE_MARGIN"}:
        if feature_row.get("opening_rating_in_fitted_design"):
            state = ABSTAIN_AUTHORITY
            reasons.append("OPENING_RATING_DECLARED_CONSUMED_BUT_ABSENT_FROM_DESIGN")
        elif not feature_row.get("historical_prior_outcome_analogue_bound"):
            state = ABSTAIN_FEATURES
            reasons.append("NO_COMPATIBLE_HISTORICAL_TRAINING_ANALOGUE")
        elif not feature_row.get("principal_performance_features_present"):
            state = ABSTAIN_FEATURES
            reasons.append("READY_WOULD_REST_ONLY_ON_MISSINGNESS_INDICATORS")
        else:
            state = READY
    else:
        raise BindingSuccessorViolation(f"unknown family: {family}")
    return {
        "candidate_id": candidate["candidate_id"],
        "predecessor_candidate_id": candidate["predecessor_candidate_id"],
        "contest_identity": feature_row["contest_identity"],
        "source_team_id": feature_row["source_team_id"],
        "canonical_team_id": feature_row.get("canonical_team_id"),
        "site_orientation": feature_row["site_orientation"],
        "family": family,
        "feature_scope": candidate["feature_scope"],
        "readiness_state": state,
        "abstention_reasons": reasons,
        "consumed_opening_rating": bool(candidate["consumes_opening_rating"]),
        "effective_strength_prior_admission": feature_row[
            "effective_strength_prior_admission"
        ],
        "effective_ranking_authority": feature_row["effective_ranking_authority"],
        "ranking_surface_state": feature_row["ranking_surface_state"],
        "historical_prior_outcome_analogue_bound": feature_row[
            "historical_prior_outcome_analogue_bound"
        ],
        "principal_performance_features_present": list(
            feature_row["principal_performance_features_present"]
        ),
    }


def build_expected(
    *,
    repo_root: Path,
    data_root: Path,
) -> dict[str, Any]:
    contract = load_contract(repo_root)
    review_contract = load_review_contract(repo_root)
    labels = protected_hash_labels(repo_root)
    if (
        labels["protected_judging_rule_seal_csv_sha256"]
        != review_contract["protected_hash_labels"][
            "protected_judging_rule_seal_csv_sha256"
        ]
    ):
        raise BindingSuccessorViolation("governance CSV hash drifted")
    if (
        labels["judging_rule_seal_json_sha256"]
        != review_contract["protected_hash_labels"]["judging_rule_seal_json_sha256"]
    ):
        raise BindingSuccessorViolation("judging JSON hash drifted")

    suite_gate = read_json(
        repo_root / contract["sources"]["cycle24_suite_gate"]["gate_relative_path"]
    )
    if (
        suite_gate["gate_identity"]
        != contract["sources"]["cycle24_suite_gate"]["gate_identity"]
    ):
        raise BindingSuccessorViolation("Cycle #24 suite gate identity drifted")
    prior_gate = read_json(
        repo_root / contract["sources"]["cycle24_prior_gate"]["gate_relative_path"]
    )
    if (
        prior_gate["gate_identity"]
        != contract["sources"]["cycle24_prior_gate"]["gate_identity"]
    ):
        raise BindingSuccessorViolation("Cycle #24 prior gate identity drifted")
    early_gate = read_json(
        repo_root / contract["sources"]["cycle24_early_gate"]["gate_relative_path"]
    )
    if (
        early_gate["gate_identity"]
        != contract["sources"]["cycle24_early_gate"]["gate_identity"]
    ):
        raise BindingSuccessorViolation("Cycle #24 early gate identity drifted")
    authority_gate = read_json(
        repo_root
        / contract["sources"]["authority_enrichment_gate"]["gate_relative_path"]
    )
    baselines_gate = read_json(
        repo_root / contract["sources"]["frozen_candidates_gate"]["gate_relative_path"]
    )
    matrix_gate = read_json(
        repo_root
        / contract["sources"]["chronological_development_matrix"]["gate_relative_path"]
    )

    feature_rows = payload_rows(
        data_root, suite_gate, "week1_2026_forecast_feature_rows.jsonl"
    )
    adequacy_rows = payload_rows(
        data_root, suite_gate, "week1_2026_forecast_candidate_adequacy_rows.jsonl"
    )
    parameter_rows = payload_rows(
        data_root, suite_gate, "week1_2026_forecast_fitted_parameter_rows.jsonl"
    )
    early_rows = payload_rows(
        data_root, early_gate, "week1_2026_early_forecast_rows.jsonl"
    )
    matrix_rows = payload_rows(
        data_root,
        matrix_gate,
        contract["sources"]["chronological_development_matrix"]["feature_payload_name"],
    )
    predictions = payload_rows(
        data_root, baselines_gate, "national_baseline_predictions.jsonl"
    )
    if any(int(row["season"]) in {2024, 2025} for row in matrix_rows):
        raise BindingSuccessorViolation("2024/2025 rows present in development matrix")

    ridge_audit = ridge_saturation_audit(predictions, clip=contract["probability_clip"])
    findings = classify_cycle24_findings(
        contract=contract,
        feature_rows=feature_rows,
        adequacy_rows=adequacy_rows,
        early_rows=early_rows,
        ridge_audit=ridge_audit,
        labels=labels,
        review_contract=review_contract,
    )
    frozen_identities = sorted(row["forecast_row_identity"] for row in early_rows)
    terminal = terminal_prior_index(matrix_rows)
    poll_complete = bool(authority_gate["ranking_completion"]["poll_surface_complete"])

    principal = list(contract["principal_performance_features"])
    successor_features = [
        bind_successor_feature_row(
            cycle24_row=row,
            terminal=terminal.get(str(row["canonical_team_id"]))
            if row.get("canonical_team_id")
            else None,
            poll_surface_complete=poll_complete,
            principal=principal,
        )
        for row in feature_rows
    ]

    design_meta = next(
        row
        for row in parameter_rows
        if row["parameter_set_id"] == "WEEK1_2026_DEPLOYMENT_DESIGN"
    )
    beta_by_predecessor = {
        "prior_only": next(
            row
            for row in parameter_rows
            if row["parameter_set_id"] == "PRIOR_ONLY_BETA"
        ),
        "national_logistic_l2": next(
            row
            for row in parameter_rows
            if row["parameter_set_id"] == "NATIONAL_LOGISTIC_L2_BETA"
        ),
        "national_margin_ridge": next(
            row
            for row in parameter_rows
            if row["parameter_set_id"] == "NATIONAL_MARGIN_RIDGE_BETA"
        ),
    }
    frozen_candidates = {
        item["candidate_id"]: item for item in baselines_gate["candidates"]
    }

    score_rows: list[dict[str, Any]] = []
    adequacy_out: list[dict[str, Any]] = []
    for candidate in contract["successor_candidates"]:
        predecessor_id = candidate["predecessor_candidate_id"]
        for feature_row in successor_features:
            ready = successor_readiness(
                candidate=candidate, feature_row=feature_row, principal=principal
            )
            ready["row_identity"] = stable_hash(ready)
            adequacy_out.append(ready)
            probability = None
            margin = None
            limitation = None
            if ready["readiness_state"] != READY:
                limitation = ready["readiness_state"]
            else:
                family = candidate["family"]
                if family == "UNFITTED_REFERENCE":
                    probability = 0.5
                elif family == "ELO":
                    probability = elo_probability(
                        feature_row,
                        frozen_candidates["national_elo"]["hyperparameters"],
                    )
                elif family in {"REGULARIZED_LOGISTIC", "RIDGE_MARGIN"}:
                    ridge = beta_by_predecessor.get(predecessor_id)
                    probability, margin = score_fitted(
                        family=family,
                        scope=candidate["feature_scope"],
                        values=feature_row["feature_values"],
                        design_meta=design_meta,
                        coefficients=ridge["coefficients"],
                        ridge_stdev=ridge.get("training_residual_stdev"),
                        ridge_divisor=ridge.get("logistic_link_scale_divisor"),
                    )
                else:
                    raise BindingSuccessorViolation(f"unknown family: {family}")
            scored = {
                "candidate_id": candidate["candidate_id"],
                "predecessor_candidate_id": predecessor_id,
                "contest_identity": feature_row["contest_identity"],
                "source_team_id": feature_row["source_team_id"],
                "canonical_team_id": feature_row.get("canonical_team_id"),
                "site_orientation": feature_row["site_orientation"],
                "readiness_state": ready["readiness_state"],
                "probability": None
                if probability is None
                else round(float(probability), 10),
                "expected_margin": None if margin is None else round(float(margin), 10),
                "limitation": limitation,
                "cycle24_feature_row_identity": feature_row["cycle24_row_identity"],
            }
            scored["row_identity"] = stable_hash(scored)
            score_rows.append(scored)

    authority_map = []
    for feature_row in successor_features:
        for column, consumed_by in (
            ("opening_rating", ("national_elo_c25_input_bound",)),
            (
                "prior_win_rate",
                (
                    "prior_only_c25_input_bound",
                    "national_logistic_l2_c25_input_bound",
                    "national_margin_ridge_c25_input_bound",
                ),
            ),
            (
                "ap_poll_rank",
                (
                    "national_logistic_l2_c25_input_bound",
                    "national_margin_ridge_c25_input_bound",
                ),
            ),
            (
                "rankings_source_available",
                (
                    "national_logistic_l2_c25_input_bound",
                    "national_margin_ridge_c25_input_bound",
                ),
            ),
            (
                "is_home",
                (
                    "prior_only_c25_input_bound",
                    "national_elo_c25_input_bound",
                    "national_logistic_l2_c25_input_bound",
                    "national_margin_ridge_c25_input_bound",
                ),
            ),
        ):
            values = feature_row["feature_values"]
            current = (
                feature_row.get(column)
                if column == "opening_rating"
                else values.get(column)
            )
            authority_map.append(
                {
                    "contest_identity": feature_row["contest_identity"],
                    "source_team_id": feature_row["source_team_id"],
                    "source_evidence": column,
                    "temporal_authority": "THROUGH_2023_ALLOWED_HISTORY"
                    if column != "ap_poll_rank"
                    else "BAT_683_AP_POLL_SURFACE",
                    "effective_admission_state": (
                        feature_row["effective_strength_prior_admission"]
                        if column == "opening_rating"
                        else feature_row["effective_ranking_authority"]
                        if column in {"ap_poll_rank", "rankings_source_available"}
                        else "ADMITTED_IF_ANALOGUE_BOUND"
                    ),
                    "training_analogue": (
                        "NONE_FITTED_SCOPE_EXCLUDES_OPENING_RATING"
                        if column == "opening_rating"
                        else "DEVELOPMENT_MATRIX_TERMINAL_THROUGH_2023"
                        if column == "prior_win_rate"
                        else "POLL_SNAPSHOT_PRESENT_FOR_THE_WEEK"
                        if column == "rankings_source_available"
                        else "NUMERIC_RANK_OR_MISSING_INDICATOR"
                    ),
                    "transformation": "IDENTITY_OR_SCOPE_STANDARDIZATION",
                    "model_column": column,
                    "current_value_present": current is not None
                    if column != "rankings_source_available"
                    else True,
                    "consumed_by_successor_candidates": list(consumed_by),
                    "cycle24_fitted_models_consumed": column != "opening_rating",
                }
            )

    cycle24_preservation = {
        "early_gate_identity": early_gate["gate_identity"],
        "suite_gate_identity": suite_gate["gate_identity"],
        "prior_gate_identity": prior_gate["gate_identity"],
        "forecast_row_count": len(early_rows),
        "frozen_row_count": sum(
            1 for row in early_rows if row["row_state"] == "FORECAST_FROZEN"
        ),
        "forecast_row_identity_sha256": hashlib.sha256(
            "".join(frozen_identities).encode("utf-8")
        ).hexdigest(),
        "rewritten": False,
    }

    summary = {
        "oriented_row_count": len(successor_features),
        "historical_analogue_bound_count": sum(
            1
            for row in successor_features
            if row["historical_prior_outcome_analogue_bound"]
        ),
        "readiness_counts": _counts(row["readiness_state"] for row in adequacy_out),
        "ranking_surface_state_counts": _counts(
            row["ranking_surface_state"] for row in successor_features
        ),
        "cycle24_forecast_rows_unchanged": True,
        "recommended_candidate": None,
        "champion_declared": False,
        "market_values_inspected": False,
        "t_minus_24h_state": "OPEN",
        "t_minus_90m_state": "OPEN",
    }
    code_identity = sha256_file(
        repo_root
        / "src/aggie_analytics/data/week1_2026_forecast_input_binding_successor.py"
    )
    freeze = {
        "freeze_id": "PRE_MARKET_MODEL_FREEZE",
        "contract_id": CONTRACT_ID,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "candidate_registry": [
            item["candidate_id"] for item in contract["successor_candidates"]
        ],
        "feature_scopes": {
            item["candidate_id"]: item["feature_scope"]
            for item in contract["successor_candidates"]
        },
        "training_population": "ALL_ALLOWED_ROWS_THROUGH_2023",
        "hyperparameters_reused_from_cycle24": True,
        "probability_margin_mappings_reused_from_cycle24": True,
        "diagnostic_thresholds": contract["pre_market_diagnostic_thresholds"],
        "code_identity": code_identity,
        "market_access_occurred": False,
    }
    freeze["freeze_identity"] = stable_hash(freeze)

    dataset_identity = stable_hash(
        {
            "successor_features": [row["row_identity"] for row in successor_features],
            "adequacy": [row["row_identity"] for row in adequacy_out],
            "scores": [row["row_identity"] for row in score_rows],
            "findings": findings,
            "freeze_identity": freeze["freeze_identity"],
        }
    )
    return {
        "contract": contract,
        "review_contract": review_contract,
        "labels": labels,
        "findings": findings,
        "ridge_audit": ridge_audit,
        "successor_features": successor_features,
        "adequacy_rows": adequacy_out,
        "score_rows": score_rows,
        "authority_map": authority_map,
        "cycle24_preservation": cycle24_preservation,
        "summary": summary,
        "freeze": freeze,
        "dataset_identity": dataset_identity,
        "code_identity": code_identity,
        "contract_sha256": freeze["contract_sha256"],
        "poll_surface_complete": poll_complete,
        "suite_gate": suite_gate,
        "early_gate": early_gate,
        "prior_gate": prior_gate,
        "authority_gate": authority_gate,
    }


def _nonclaims() -> dict[str, bool]:
    return {
        "cycle24_forecasts_rewritten": False,
        "champion_or_production_promotion": False,
        "bas_or_aggie_excess_claim": False,
        "week1_outcome_access": False,
        "market_values_inspected": False,
        "a_and_m_adjustment": False,
        "protected_split_registry_mutation": False,
        "judging_rule_seal_mutation": False,
        "old_candidate_id_reused_with_new_semantics": False,
        "opening_rating_inserted_into_fitted_models": False,
        "t_24h_executed": False,
        "t_90m_executed": False,
    }


def build_review_gate(
    expected: Mapping[str, Any], *, execution_time_utc: str
) -> dict[str, Any]:
    review = {
        "artifact_type": "WEEK1_2026_CYCLE24_BINDING_REVIEW_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": REVIEW_CONTRACT_ID,
        "decision_unit": LOCAL_ISSUE_ID,
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "classification": REVIEW_CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": REVIEW_PASS_RESULT,
        "issued_at_utc": execution_time_utc,
        "findings": expected["findings"],
        "ridge_saturation_audit": expected["ridge_audit"],
        "protected_hash_labels": expected["labels"],
        "cycle24_preservation": expected["cycle24_preservation"],
        "scientific_nonclaims": _nonclaims(),
        "checkpoints": {
            "t_minus_24h_state": "OPEN",
            "t_minus_90m_state": "OPEN",
            "executed_early": False,
            "market_values_inspected": False,
        },
    }
    review["gate_identity"] = binding_identity(review, "gate_identity")
    return review


def build_successor_gate(
    expected: Mapping[str, Any], *, execution_time_utc: str
) -> dict[str, Any]:
    gate = {
        "artifact_type": "WEEK1_2026_FORECAST_INPUT_BINDING_SUCCESSOR_GATE",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": LOCAL_ISSUE_ID,
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "issued_at_utc": execution_time_utc,
        "dataset_identity": expected["dataset_identity"],
        "code_identity": expected["code_identity"],
        "pre_market_model_freeze": expected["freeze"],
        "summary": expected["summary"],
        "cycle24_preservation": expected["cycle24_preservation"],
        "protected_hash_labels": expected["labels"],
        "scientific_nonclaims": _nonclaims(),
        "checkpoints": expected["contract"]["checkpoints"],
        "bound_predecessors": {
            "prior_gate_identity": expected["prior_gate"]["gate_identity"],
            "suite_gate_identity": expected["suite_gate"]["gate_identity"],
            "early_gate_identity": expected["early_gate"]["gate_identity"],
            "predecessor_artifacts_rewritten_in_place": False,
        },
    }
    gate["gate_identity"] = binding_identity(gate, "gate_identity")
    gate["binding_identity"] = binding_identity(gate, "binding_identity")
    return gate


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    execution_time: datetime,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = dict(
        expected
        if expected is not None
        else build_expected(repo_root=repo_root, data_root=data_root)
    )
    execution_time_utc = execution_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    freeze = dict(resolved["freeze"])
    freeze["issued_at_utc"] = execution_time_utc
    freeze["freeze_identity"] = stable_hash(
        {key: value for key, value in freeze.items() if key != "freeze_identity"}
    )
    resolved["freeze"] = freeze

    identity = resolved["dataset_identity"]
    canonical_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / identity
    payloads = []
    for name, role, key in (
        (
            "week1_2026_cycle24_binding_findings.jsonl",
            "CYCLE24_BINDING_FINDINGS",
            "findings",
        ),
        (
            "week1_2026_c25_successor_feature_rows.jsonl",
            "SUCCESSOR_FEATURE_ROWS",
            "successor_features",
        ),
        (
            "week1_2026_c25_successor_adequacy_rows.jsonl",
            "SUCCESSOR_ADEQUACY_ROWS",
            "adequacy_rows",
        ),
        (
            "week1_2026_c25_successor_score_rows.jsonl",
            "SUCCESSOR_SCORE_ROWS",
            "score_rows",
        ),
        (
            "week1_2026_c25_field_authority_map.jsonl",
            "FIELD_AUTHORITY_MAP",
            "authority_map",
        ),
    ):
        rows = resolved[key]
        payload = jsonl_bytes(rows)
        path = canonical_root / name
        _write_bytes(path, payload)
        payloads.append(
            {
                "name": name,
                "role": role,
                "rows": len(rows),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )

    review_gate = build_review_gate(resolved, execution_time_utc=execution_time_utc)
    successor_gate = build_successor_gate(
        resolved, execution_time_utc=execution_time_utc
    )
    successor_gate["payloads"] = payloads
    successor_gate["producer"] = {
        "python": sys.version.split()[0],
        "platform": platform.system(),
        "code_identity": resolved["code_identity"],
    }
    successor_gate["gate_identity"] = binding_identity(successor_gate, "gate_identity")
    successor_gate["binding_identity"] = binding_identity(
        successor_gate, "binding_identity"
    )

    review_path = repo_root / REVIEW_GATE_RELATIVE
    successor_path = repo_root / GATE_RELATIVE
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(review_gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    successor_path.write_text(
        json.dumps(successor_gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "review_gate": review_gate,
        "successor_gate": successor_gate,
        "expected": resolved,
    }


def validate_artifact(
    *, repo_root: Path, data_root: Path, require_rebuild: bool = True
) -> dict[str, Any]:
    expected = build_expected(repo_root=repo_root, data_root=data_root)
    review_gate = read_json(repo_root / REVIEW_GATE_RELATIVE)
    successor_gate = read_json(repo_root / GATE_RELATIVE)
    rebuilt_review = build_review_gate(
        expected, execution_time_utc=str(review_gate.get("issued_at_utc"))
    )
    if review_gate.get("findings") != rebuilt_review["findings"]:
        raise BindingSuccessorViolation("review findings drifted")
    if successor_gate.get("dataset_identity") != expected["dataset_identity"]:
        raise BindingSuccessorViolation("successor dataset identity drifted")
    if successor_gate["scientific_nonclaims"]["cycle24_forecasts_rewritten"]:
        raise BindingSuccessorViolation("Cycle #24 forecasts were rewritten")
    if successor_gate["checkpoints"]["t_minus_24h_state"] != "OPEN":
        raise BindingSuccessorViolation("T-24H is not OPEN")
    if successor_gate["checkpoints"]["t_minus_90m_state"] != "OPEN":
        raise BindingSuccessorViolation("T-90M is not OPEN")
    if successor_gate["pre_market_model_freeze"]["market_access_occurred"] is not False:
        raise BindingSuccessorViolation(
            "corrective contract frozen after market access"
        )
    labels = successor_gate["protected_hash_labels"]
    if (
        labels["protected_judging_rule_seal_csv_sha256"]
        == labels["judging_rule_seal_json_sha256"]
    ):
        raise BindingSuccessorViolation("protected hash labels swapped or conflated")
    early = payload_rows(
        data_root,
        expected["early_gate"],
        "week1_2026_early_forecast_rows.jsonl",
    )
    current_ids = sorted(row["forecast_row_identity"] for row in early)
    preserved = hashlib.sha256("".join(current_ids).encode("utf-8")).hexdigest()
    if preserved != expected["cycle24_preservation"]["forecast_row_identity_sha256"]:
        raise BindingSuccessorViolation("Cycle #24 forecast identities changed")
    if require_rebuild and successor_gate["code_identity"] != expected["code_identity"]:
        raise BindingSuccessorViolation("code identity drifted")
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD" if require_rebuild else "SCHEMA_ONLY",
        "review_gate_identity": review_gate["gate_identity"],
        "successor_gate_identity": successor_gate["gate_identity"],
        "freeze_identity": successor_gate["pre_market_model_freeze"]["freeze_identity"],
        "dataset_identity": successor_gate["dataset_identity"],
        "summary": successor_gate["summary"],
    }
