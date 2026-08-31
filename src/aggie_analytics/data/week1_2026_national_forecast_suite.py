from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    canonical_json_bytes,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)
from aggie_analytics.modeling import national_expectation_baselines as baselines

# Cycle #24 executable binding for the five frozen national candidates.
#
# This unit does two things and refuses to do a third.
#
#   A  it refits the two fitted families on the allowed training partition only,
#      with the previously frozen hyperparameters, and reuses the Cycle #24
#      frozen prior for the two rating families rather than refitting Elo here;
#   B  it decides, per candidate and per oriented Week 1 row, whether the model
#      may be executed at all. A feature is either populated from an admitted
#      Week 1 domain or left missing behind a learned indicator; a scope feature
#      that is neither admitted nor indicator-covered forces an abstention,
#      because substituting the training mean would fabricate an average team;
#   C  it does not emit a forecast. The immutable snapshot belongs to the early
#      Week 1 decision unit, which consumes the fitted parameters bound here.
#
# Development metrics and calibration come from the frozen candidate gate, whose
# folds held their evaluation rows out of training. Nothing here is fitted or
# selected on Week Zero, on Week 1, or on the focus contest.

SCHEMA_VERSION = "aggie.shadow.week1_2026_national_forecast_suite.v1"
CONTRACT_ID = "CYCLE24-WEEK1-2026-NATIONAL-FORECAST-SUITE-V1"
JIRA_KEY = "BAT-680"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-NATIONAL-FORECAST-SUITE-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "WEEK1_2026_NATIONAL_FORECAST_SUITE_EXECUTABLE_BINDING"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_NATIONAL_FORECAST_SUITE_BINDING"

CONTRACT_RELATIVE = "configs/week1_2026_national_forecast_suite_contract.json"
GATE_RELATIVE = "artifacts/forecast/week1_2026_national_forecast_suite_gate.json"
PAYLOAD_SLUG = "week1_2026_national_forecast_suite"

MODEL_PAYLOAD_NAME = "week1_2026_forecast_model_binding_rows.jsonl"
FEATURE_PAYLOAD_NAME = "week1_2026_forecast_feature_rows.jsonl"
ADEQUACY_PAYLOAD_NAME = "week1_2026_forecast_candidate_adequacy_rows.jsonl"
PARAMETER_PAYLOAD_NAME = "week1_2026_forecast_fitted_parameter_rows.jsonl"

READY = "FORECAST_READY_ALL_REQUIRED_FEATURES_ADMITTED"
ABSTAIN_FEATURES = "ABSTAIN_MISSING_REQUIRED_FEATURES"
ABSTAIN_ENTITY = "ABSTAIN_UNSUPPORTED_ENTITY"
QUARANTINED = "QUARANTINED_CONFLICT"

ADMITTED = "ADMITTED_PROSPECTIVE_PREKICKOFF"

GATE_IDENTITY_FIELDS = (
    "artifact_type",
    "adequacy",
    "bound_predecessors",
    "candidate_bindings",
    "checkpoints",
    "classification",
    "contract_id",
    "contract_sha256",
    "dataset_identity",
    "decision_unit",
    "deployment_fit",
    "development_evidence",
    "focus_contest_report",
    "jira_key",
    "lane",
    "local_issue_id",
    "manifest",
    "parent_jira_key",
    "payloads",
    "protected_lane",
    "record_hashes",
    "result",
    "schema_version",
    "scientific_nonclaims",
    "season",
    "summary",
    "tamu_policy",
    "uncertainty",
    "week_label",
)


class ForecastSuiteViolation(ValueError):
    """Raised when a forecast-suite invariant is violated."""


# ---------------------------------------------------------------------------
# io helpers
# ---------------------------------------------------------------------------


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    missing = [field for field in GATE_IDENTITY_FIELDS if field not in gate]
    if missing:
        raise ForecastSuiteViolation(f"gate is missing identity fields: {missing}")
    return stable_hash({field: gate[field] for field in GATE_IDENTITY_FIELDS})


def load_contract(repo_root: Path) -> dict[str, Any]:
    return load_contract_mapping(read_json(repo_root / CONTRACT_RELATIVE))


def load_contract_mapping(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the contract so a relaxed forecast policy can never be honoured."""
    contract = dict(contract)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ForecastSuiteViolation("forecast suite contract identity drift")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ForecastSuiteViolation("forecast suite schema drift")
    if contract.get("lane") != LANE:
        raise ForecastSuiteViolation("forecast suite lane drift")
    if contract.get("protected_lane") != PROTECTED_LANE:
        raise ForecastSuiteViolation("protected lane must remain blocked")
    if contract.get("jira_key") != JIRA_KEY:
        raise ForecastSuiteViolation("forecast suite owner drift")

    declared = [item["candidate_id"] for item in contract["candidates"]]
    if declared != list(contract["candidate_set_is_exactly"]):
        raise ForecastSuiteViolation("the candidate set drifted from the declared five")
    if len(declared) != 5:
        raise ForecastSuiteViolation(
            f"exactly five candidates are allowed, saw {len(declared)}"
        )

    construction = contract["week1_feature_construction"]
    for key in (
        "forbid_fabricated_numeric_value",
        "forbid_training_mean_substitution_without_a_learned_indicator",
        "abstain_when_a_scope_feature_is_neither_admitted_nor_indicator_covered",
    ):
        if construction.get(key) is not True:
            raise ForecastSuiteViolation(f"feature construction policy relaxed: {key}")
    for key in (
        "weather_admitted_as_model_input",
        "venue_coordinates_admitted_as_model_input",
    ):
        if construction.get(key) is not False:
            raise ForecastSuiteViolation(f"forbidden model input admitted: {key}")

    development = contract["development_evidence"]
    for key in (
        "fitted_or_selected_on_week_zero",
        "fitted_or_selected_on_week1",
        "fitted_or_selected_on_the_focus_contest",
        "fitted_or_selected_on_protected_seasons",
        "fitted_or_selected_on_market_data",
    ):
        if development.get(key) is not False:
            raise ForecastSuiteViolation(f"forbidden development evidence: {key}")

    uncertainty = contract["uncertainty"]
    if uncertainty.get("probability_interval_established") is not False:
        raise ForecastSuiteViolation(
            "no per-row probability interval model was fitted, so it cannot be declared established"
        )
    for key in (
        "forbid_inferring_calibration_from_week_zero",
        "forbid_probability_interval_for_the_control",
        "forbid_margin_interval_for_a_probability_only_family",
    ):
        if uncertainty.get(key) is not True:
            raise ForecastSuiteViolation(f"uncertainty policy relaxed: {key}")
    if uncertainty.get("margin_interval_allowed_candidates") != [
        "national_margin_ridge"
    ]:
        raise ForecastSuiteViolation(
            "margin intervals are allowed for the ridge family only"
        )

    fit = contract["deployment_fit"]
    if int(fit["training_season_max"]) != 2023:
        raise ForecastSuiteViolation("the training window must end at 2023")
    if sorted(fit["excluded_protected_seasons"]) != [2024, 2025]:
        raise ForecastSuiteViolation("protected seasons must remain excluded")
    for key in (
        "hyperparameter_search_performed",
        "selection_performed_on_week_zero",
        "selection_performed_on_week1",
        "elo_refit_in_this_unit",
    ):
        if fit.get(key) is not False:
            raise ForecastSuiteViolation(f"forbidden fitting behaviour: {key}")

    for key, value in contract["forbidden"].items():
        if value is not True:
            raise ForecastSuiteViolation(
                f"a forbidden behaviour is no longer forbidden: {key}"
            )
    for key in ("t_minus_24h_state", "t_minus_90m_state"):
        if contract["checkpoints"].get(key) != "OPEN":
            raise ForecastSuiteViolation(f"{key} must remain OPEN in this cycle")
    for key in ("executed_early", "pregame_result_access", "week1_outcome_access"):
        if contract["checkpoints"].get(key) is not False:
            raise ForecastSuiteViolation(f"forbidden checkpoint behaviour: {key}")
    if (
        contract["predecessor_immutability"].get("rewrites_predecessor_artifacts")
        is not False
    ):
        raise ForecastSuiteViolation("predecessor artifacts must not be rewritten")
    for key in ("custom_correction_applied", "tamu_specific_adjustment_applied"):
        if contract["tamu_policy"].get(key) is not False:
            raise ForecastSuiteViolation(
                f"an A&M-specific adjustment is declared: {key}"
            )
    return contract


def payload_rows(
    data_root: Path, gate: Mapping[str, Any], name: str
) -> list[dict[str, Any]]:
    entry = next(item for item in gate["payloads"] if item["name"] == name)
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    located = next(item for item in manifest["payloads"] if item["name"] == name)
    payload = (data_root / located["relative_path"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
        raise ForecastSuiteViolation(f"source payload hash drift: {name}")
    return [json.loads(line) for line in payload.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------


def load_inputs(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Load every pinned predecessor surface and refuse any identity drift."""
    contract = load_contract(repo_root)
    sources = contract["sources"]

    gates: dict[str, dict[str, Any]] = {}
    for name in (
        "frozen_candidates",
        "spine_semantic_successor",
        "authority_enrichment",
        "frozen_strength_prior",
    ):
        source = sources[name]
        gate = read_json(repo_root / source["gate_relative_path"])
        if gate.get("gate_identity") != source["gate_identity"]:
            raise ForecastSuiteViolation(f"predecessor gate identity drift for {name}")
        gates[name] = gate

    matrix_source = sources["chronological_development_matrix"]
    matrix_path = repo_root / matrix_source["gate_relative_path"]
    if sha256_file(matrix_path) != matrix_source["gate_sha256"]:
        raise ForecastSuiteViolation("chronological development matrix gate drift")
    matrix_gate = read_json(matrix_path)

    features = payload_rows(
        data_root, matrix_gate, matrix_source["feature_payload_name"]
    )
    labels = payload_rows(data_root, matrix_gate, matrix_source["label_payload_name"])
    protected = sorted(
        {
            int(row["season"])
            for row in features
            if int(row["season"])
            in set(contract["deployment_fit"]["excluded_protected_seasons"])
        }
    )
    if protected:
        raise ForecastSuiteViolation(
            f"protected seasons present in training evidence: {protected}"
        )

    spine_rows = payload_rows(
        data_root,
        gates["spine_semantic_successor"],
        sources["spine_semantic_successor"]["row_payload_name"],
    )
    cells = payload_rows(
        data_root,
        gates["spine_semantic_successor"],
        sources["spine_semantic_successor"]["cell_payload_name"],
    )
    kickoff_rows = payload_rows(
        data_root,
        gates["authority_enrichment"],
        sources["authority_enrichment"]["kickoff_payload_name"],
    )
    entity_rows = payload_rows(
        data_root,
        gates["authority_enrichment"],
        sources["authority_enrichment"]["entity_payload_name"],
    )
    ranking_rows = payload_rows(
        data_root,
        gates["authority_enrichment"],
        sources["authority_enrichment"]["ranking_payload_name"],
    )
    prior_rows = payload_rows(
        data_root,
        gates["frozen_strength_prior"],
        sources["frozen_strength_prior"]["prior_payload_name"],
    )

    return {
        "contract": contract,
        "gates": gates,
        "matrix_gate": matrix_gate,
        "features": features,
        "labels": labels,
        "spine_rows": spine_rows,
        "cells": cells,
        "kickoff_rows": kickoff_rows,
        "entity_rows": entity_rows,
        "ranking_rows": ranking_rows,
        "prior_rows": prior_rows,
    }


def frozen_hyperparameters(
    candidate_gate: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Read every frozen candidate's hyperparameters and development metrics."""
    out: dict[str, dict[str, Any]] = {}
    for candidate in candidate_gate["candidates"]:
        out[candidate["candidate_id"]] = candidate
    return out


# ---------------------------------------------------------------------------
# deployment fit on the allowed training partition
# ---------------------------------------------------------------------------


def fit_deployment_models(
    *,
    contract: Mapping[str, Any],
    features: Sequence[Mapping[str, Any]],
    labels: Sequence[Mapping[str, Any]],
    frozen: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Refit the fitted families on the allowed training partition only."""
    season_limit = int(contract["deployment_fit"]["training_season_max"])
    training = [row for row in features if int(row["season"]) <= season_limit]
    if not training:
        raise ForecastSuiteViolation("the allowed training partition is empty")
    season_max = max(int(row["season"]) for row in training)
    if season_max > int(contract["deployment_fit"]["training_season_max"]):
        raise ForecastSuiteViolation(
            f"training evidence exceeds the allowed window: {season_max}"
        )

    label_index = {
        (row["canonical_game_id"], row["canonical_team_id"]): row for row in labels
    }
    tie_value = 0.5
    target = np.array(
        [
            baselines._target(
                label_index[(row["canonical_game_id"], row["canonical_team_id"])],
                tie_value,
            )
            for row in training
        ],
        dtype=np.float64,
    )
    margin = np.array(
        [
            float(
                label_index[(row["canonical_game_id"], row["canonical_team_id"])][
                    "label_margin"
                ]
            )
            for row in training
        ],
        dtype=np.float64,
    )

    indicators = tuple(sorted(key for key in training[0] if key.endswith("_missing")))
    levels = baselines.conference_levels(training)
    transforms: dict[str, dict[str, float | None]] = {}
    for feature in baselines.ALL_NUMERIC:
        values = [
            float(row[feature]) for row in training if row.get(feature) is not None
        ]
        if not values:
            transforms[feature] = {"mean": None, "stdev": None, "rows": 0}
            continue
        array = np.array(values, dtype=np.float64)
        transforms[feature] = {
            "mean": float(np.mean(array)),
            "stdev": float(np.std(array, ddof=0)) or None,
            "rows": len(values),
        }

    fitted: dict[str, Any] = {
        "training_row_count": len(training),
        "training_game_count": len({row["canonical_game_id"] for row in training}),
        "training_season_min": min(int(row["season"]) for row in training),
        "training_season_max": season_max,
        "indicators": list(indicators),
        "conference_levels": list(levels),
        "transforms": transforms,
        "base_rate": float(np.mean(target)),
    }

    designs: dict[str, tuple[np.ndarray, list[str]]] = {}
    for scope in ("ALL_ADMITTED_FEATURES", "PRIOR_OUTCOME_DOMAIN_AND_SITE"):
        designs[scope] = baselines.build_design(
            training,
            scope=scope,
            transforms=transforms,
            levels=levels,
            indicators=indicators,
        )
    fitted["design_columns"] = {
        scope: ["intercept", *columns] for scope, (_, columns) in designs.items()
    }
    fitted["candidate_scopes"] = {
        "national_logistic_l2": "ALL_ADMITTED_FEATURES",
        "prior_only": "PRIOR_OUTCOME_DOMAIN_AND_SITE",
        "national_margin_ridge": "ALL_ADMITTED_FEATURES",
    }

    for candidate_id in ("national_logistic_l2", "prior_only"):
        hyperparameters = frozen[candidate_id]["hyperparameters"]
        design = designs[fitted["candidate_scopes"][candidate_id]][0]
        beta = baselines.fit_logistic_l2(
            design,
            target,
            l2_lambda=float(hyperparameters["l2_lambda"]),
            iterations=int(hyperparameters["newton_iterations"]),
            tolerance=float(hyperparameters["tolerance"]),
        )
        fitted[f"{candidate_id}_beta"] = [float(value) for value in beta]

    ridge = frozen["national_margin_ridge"]["hyperparameters"]
    ridge_design = designs["ALL_ADMITTED_FEATURES"][0]
    beta_ridge = baselines.fit_ridge(
        ridge_design, margin, l2_lambda=float(ridge["l2_lambda"])
    )
    residual = margin - ridge_design @ beta_ridge
    fitted["ridge_beta"] = [float(value) for value in beta_ridge]
    fitted["ridge_training_residual_stdev"] = float(np.std(residual, ddof=1))
    fitted["ridge_link_scale_divisor"] = float(ridge["logistic_link_scale_divisor"])
    return fitted


# ---------------------------------------------------------------------------
# Week 1 feature construction
# ---------------------------------------------------------------------------


RESOLVED_IDENTITY_STATES = {
    "EXACT_NORMALIZED_NAME_RESOLVED",
    "RESOLVED_BY_OFFICIAL_RECORD_TUPLE",
    "RESOLVED_AUTHORITATIVE_IDENTITY",
}


def build_feature_rows(
    *,
    contract: Mapping[str, Any],
    spine_rows: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    prior_rows: Sequence[Mapping[str, Any]],
    ranking_rows: Sequence[Mapping[str, Any]],
    kickoff_rows: Sequence[Mapping[str, Any]],
    entity_rows: Sequence[Mapping[str, Any]],
    fitted: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Populate an admitted Week 1 feature vector, or leave a feature missing.

    A numeric feature is only ever populated from an admitted domain. Everything
    else stays missing, and stays missing behind the learned indicator the
    training partition actually produced, so no row is silently handed a
    training mean it did not earn.
    """
    construction = contract["week1_feature_construction"]
    admitted_sources = construction["admitted_feature_sources"]
    indicator_set = set(fitted["indicators"])
    conference_levels = set(fitted["conference_levels"])

    cells_by_row: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for cell in cells:
        key = (cell["contest_identity"], cell["source_team_id"])
        cells_by_row.setdefault(key, {})[cell["domain"]] = cell

    prior_by_source = {row["source_team_id"]: row for row in prior_rows}
    ranking_by_source = {row["source_team_id"]: row for row in ranking_rows}
    kickoff_by_contest = {row["contest_identity"]: row for row in kickoff_rows}
    spine_by_key = {
        (row["contest_identity"], row["source_team_id"]): row for row in spine_rows
    }
    authority_resolved = {
        row["source_team_id"]
        for row in entity_rows
        if row.get("disposition") == "RESOLVED_AUTHORITATIVE_IDENTITY"
        or row.get("authoritative_identity")
    }

    rows: list[dict[str, Any]] = []
    for spine_row in spine_rows:
        key = (spine_row["contest_identity"], spine_row["source_team_id"])
        domains = cells_by_row.get(key, {})
        prior = prior_by_source.get(spine_row["source_team_id"])
        opponent_key = next(
            (
                other
                for other in spine_by_key
                if other[0] == spine_row["contest_identity"]
                and other[1] != spine_row["source_team_id"]
            ),
            None,
        )
        opponent_spine = spine_by_key.get(opponent_key) if opponent_key else None
        opponent_prior = (
            prior_by_source.get(opponent_spine["source_team_id"])
            if opponent_spine
            else None
        )
        ranking = ranking_by_source.get(spine_row["source_team_id"])
        opponent_ranking = (
            ranking_by_source.get(opponent_spine["source_team_id"])
            if opponent_spine
            else None
        )
        kickoff = kickoff_by_contest.get(spine_row["contest_identity"])

        orientation = spine_row["site_orientation"]
        conference = spine_row.get("conference_name")
        subdivision = spine_row.get("subdivision")
        identity_resolved = (
            spine_row["team_identity_state"] in RESOLVED_IDENTITY_STATES
            or spine_row["source_team_id"] in authority_resolved
        )
        opponent_identity_resolved = bool(
            opponent_spine
            and (
                opponent_spine["team_identity_state"] in RESOLVED_IDENTITY_STATES
                or opponent_spine["source_team_id"] in authority_resolved
            )
        )

        feature_values: dict[str, Any] = {
            "canonical_team_id": spine_row.get("canonical_team_id"),
            "opponent_canonical_team_id": spine_row.get("opponent_canonical_team_id"),
            "is_home": orientation == "HOME",
            "is_neutral_site": orientation == "NEUTRAL",
            "team_conference": conference if conference in conference_levels else None,
            "team_is_fbs": (subdivision == "FBS") if subdivision else None,
            "rankings_source_available": True,
            "ap_poll_rank": ranking.get("poll_rank") if ranking else None,
            "opponent_ap_poll_rank": opponent_ranking.get("poll_rank")
            if opponent_ranking
            else None,
            "coaches_poll_rank": None,
            "prior_games_played": prior.get("historical_game_count") if prior else None,
            "opponent_prior_games_played": (
                opponent_prior.get("historical_game_count") if opponent_prior else None
            ),
            "season_to_date_games": (
                1 if spine_row.get("week_zero_result_state") == ADMITTED else 0
            ),
        }
        for feature in baselines.ALL_NUMERIC:
            feature_values.setdefault(feature, None)
        for feature in baselines.ALL_BOOLEAN:
            feature_values.setdefault(feature, None)
        for feature in (
            *baselines.ALL_NUMERIC,
            *baselines.ALL_BOOLEAN,
            "team_conference",
        ):
            name = f"{feature}_missing"
            if name in indicator_set:
                feature_values[name] = feature_values.get(feature) is None

        uncovered = sorted(
            feature
            for feature in baselines.ALL_NUMERIC
            if feature_values.get(feature) is None
            and f"{feature}_missing" not in indicator_set
        )
        admitted_features = sorted(
            feature
            for feature in admitted_sources
            if feature_values.get(feature) is not None
        )

        row = {
            "contest_identity": spine_row["contest_identity"],
            "ncaa_contest_id": spine_row["ncaa_contest_id"],
            "source_team_id": spine_row["source_team_id"],
            "canonical_team_id": spine_row.get("canonical_team_id"),
            "opponent_source_team_id": opponent_spine["source_team_id"]
            if opponent_spine
            else None,
            "opponent_canonical_team_id": spine_row.get("opponent_canonical_team_id"),
            "team_identity_state": spine_row.get("team_identity_state"),
            "participant_identity_resolved": identity_resolved,
            "opponent_identity_resolved": opponent_identity_resolved,
            "site_orientation": orientation,
            "kickoff_bound_utc": (
                kickoff.get("official_kickoff_utc")
                or kickoff.get("predecessor_kickoff_bound_utc")
                if kickoff
                else spine_row.get("kickoff_utc_conservative_lower_bound")
            ),
            "kickoff_confirmation_state": (
                kickoff.get("kickoff_confirmation_state")
                if kickoff
                else "KICKOFF_NOT_BOUND"
            ),
            "prior_disposition": prior.get("prior_disposition") if prior else None,
            "opponent_prior_disposition": (
                opponent_prior.get("prior_disposition") if opponent_prior else None
            ),
            "prior_admitted": bool(prior and prior.get("prior_admitted")),
            "opponent_prior_admitted": bool(
                opponent_prior and opponent_prior.get("prior_admitted")
            ),
            "opening_rating": prior.get("opening_rating") if prior else None,
            "pre_week_zero_rating": prior.get("pre_week_zero_rating")
            if prior
            else None,
            "opponent_opening_rating": opponent_prior.get("opening_rating")
            if opponent_prior
            else None,
            "opponent_pre_week_zero_rating": (
                opponent_prior.get("pre_week_zero_rating") if opponent_prior else None
            ),
            "prior_uncertainty_class": prior.get("uncertainty_class")
            if prior
            else None,
            "prior_age_seasons": prior.get("prior_age_seasons") if prior else None,
            "ranking_state": ranking.get("ranking_state") if ranking else None,
            "domain_admission_states": {
                domain: cell.get("admission_disposition")
                for domain, cell in sorted(domains.items())
            },
            "admitted_feature_names": admitted_features,
            "features_missing_behind_a_learned_indicator": sorted(
                feature
                for feature in baselines.ALL_NUMERIC
                if feature_values.get(feature) is None
                and f"{feature}_missing" in indicator_set
            ),
            "features_neither_admitted_nor_indicator_covered": uncovered,
            "fabricated_numeric_value_count": 0,
            "feature_values": {
                key: feature_values[key]
                for key in sorted(feature_values)
                if key not in {"canonical_team_id", "opponent_canonical_team_id"}
            },
        }
        row["row_identity"] = stable_hash(row)
        rows.append(row)
    return sorted(
        rows, key=lambda item: (item["contest_identity"], item["source_team_id"])
    )


# ---------------------------------------------------------------------------
# per-candidate adequacy
# ---------------------------------------------------------------------------


def candidate_requirements(spine_gate: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["candidate_id"]: item
        for item in spine_gate["candidate_feature_requirements"]
    }


def build_adequacy_rows(
    *,
    contract: Mapping[str, Any],
    requirements: Mapping[str, Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    ranking_completion: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Decide per candidate and oriented row whether execution is permitted."""
    ranking_complete = bool(ranking_completion.get("poll_surface_complete"))
    rows: list[dict[str, Any]] = []
    for candidate in contract["candidates"]:
        candidate_id = candidate["candidate_id"]
        requirement = requirements[candidate_id]
        required = list(requirement["required_domains"])
        for feature_row in feature_rows:
            reasons: list[str] = []
            state = READY
            # Unit B resolved every source participant to an official organization,
            # but a resolved organization with no canonical modelling history is
            # still not a supported entity for a national candidate, so the
            # abstention names that state rather than blaming a missing feature.
            if not (
                feature_row["participant_identity_resolved"]
                and feature_row["opponent_identity_resolved"]
            ):
                state = ABSTAIN_ENTITY
                reasons.append("A_PARTICIPANT_IN_THIS_CONTEST_HAS_NO_RESOLVED_IDENTITY")
            elif ABSTAIN_ENTITY in {
                feature_row["prior_disposition"],
                feature_row["opponent_prior_disposition"],
            }:
                state = ABSTAIN_ENTITY
                reasons.append(
                    "A_PARTICIPANT_HAS_AN_OFFICIAL_IDENTITY_BUT_NO_CANONICAL_MODELLING_HISTORY"
                )
            missing_domains = [
                domain
                for domain in required
                if feature_row["domain_admission_states"].get(domain) != ADMITTED
                and not (
                    domain == "TEAM_STRENGTH_PRIOR" and feature_row["prior_admitted"]
                )
                and not (domain == "CURRENT_RANKING" and ranking_complete)
            ]
            if (
                "TEAM_STRENGTH_PRIOR" in required
                and not (
                    feature_row["prior_admitted"]
                    and feature_row["opponent_prior_admitted"]
                )
                and "TEAM_STRENGTH_PRIOR" not in missing_domains
            ):
                missing_domains.append("TEAM_STRENGTH_PRIOR")
            if (
                requirement.get("requires_kickoff_bound")
                and not feature_row["kickoff_bound_utc"]
            ):
                missing_domains.append("KICKOFF_BOUND")
            if (
                requirement.get("requires_complete_ranking_semantics")
                and not ranking_complete
            ):
                missing_domains.append("COMPLETE_RANKING_SEMANTICS")
            uncovered = list(
                feature_row["features_neither_admitted_nor_indicator_covered"]
            )
            if state == READY and (missing_domains or uncovered):
                state = ABSTAIN_FEATURES
                reasons.extend(
                    f"REQUIRED_DOMAIN_NOT_ADMITTED:{domain}"
                    for domain in sorted(set(missing_domains))
                )
                reasons.extend(
                    f"FEATURE_NEITHER_ADMITTED_NOR_INDICATOR_COVERED:{feature}"
                    for feature in uncovered
                )
            row = {
                "candidate_id": candidate_id,
                "family": candidate["family"],
                "feature_scope": candidate["feature_scope"],
                "contest_identity": feature_row["contest_identity"],
                "ncaa_contest_id": feature_row["ncaa_contest_id"],
                "source_team_id": feature_row["source_team_id"],
                "canonical_team_id": feature_row["canonical_team_id"],
                "site_orientation": feature_row["site_orientation"],
                "required_domains": required,
                "missing_required_domains": sorted(set(missing_domains)),
                "features_neither_admitted_nor_indicator_covered": uncovered,
                "readiness_state": state,
                "abstention_reasons": sorted(set(reasons)),
                "margin_support": candidate["margin_support"],
                "uncertainty_support": candidate["uncertainty_support"],
                "stale_input": bool(feature_row["prior_age_seasons"]),
            }
            row["row_identity"] = stable_hash(row)
            rows.append(row)
    return sorted(
        rows,
        key=lambda item: (
            item["candidate_id"],
            item["contest_identity"],
            item["source_team_id"],
        ),
    )


def _counts(values: Sequence[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items()))


def build_model_binding_rows(
    *,
    contract: Mapping[str, Any],
    frozen: Mapping[str, Mapping[str, Any]],
    fitted: Mapping[str, Any],
    adequacy_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Bind each candidate to its frozen definition and its development evidence."""
    rows: list[dict[str, Any]] = []
    for candidate in contract["candidates"]:
        candidate_id = candidate["candidate_id"]
        source = frozen[candidate_id]
        scoped = [row for row in adequacy_rows if row["candidate_id"] == candidate_id]
        margin_supported = candidate["margin_support"] == "SUPPORTED_BY_MODEL_FAMILY"
        row = {
            "candidate_id": candidate_id,
            "family": candidate["family"],
            "feature_scope": candidate["feature_scope"],
            "frozen_family": source["family"],
            "frozen_feature_scope": source["feature_scope"],
            "hyperparameters": source["hyperparameters"],
            "hyperparameter_drift": (
                source["family"] != candidate["family"]
                or source["feature_scope"] != candidate["feature_scope"]
            ),
            "probability_form": candidate["probability_form"],
            "margin_support": candidate["margin_support"],
            "margin_reason": candidate.get("margin_reason"),
            "uncertainty_support": candidate["uncertainty_support"],
            "uncertainty_reason": candidate.get("uncertainty_reason"),
            "never_recommended": bool(candidate.get("never_recommended")),
            "stale_input_warning_required": bool(
                candidate.get("stale_input_warning_required")
            ),
            "development_rows": source["rows"],
            "development_folds": source["evaluated_folds"],
            "development_brier": source["brier"],
            "development_log_loss": source["log_loss"],
            "development_accuracy": source["accuracy"],
            "development_calibration_slope": source["calibration_slope"],
            "development_calibration_intercept": source["calibration_intercept"],
            "development_calibration_supported": source["calibration_supported"],
            "development_margin_mae": source["margin_mae"],
            "development_margin_rmse": source["margin_rmse"],
            "margin_interval_dispersion": source["margin_rmse"]
            if margin_supported
            else None,
            "promoted": False,
            "recommended": False,
            "week1_ready_row_count": sum(
                1 for item in scoped if item["readiness_state"] == READY
            ),
            "week1_abstention_counts": _counts(
                [
                    item["readiness_state"]
                    for item in scoped
                    if item["readiness_state"] != READY
                ]
            ),
            "training_row_count": fitted["training_row_count"],
            "training_season_max": fitted["training_season_max"],
        }
        if candidate_id in ("national_logistic_l2", "prior_only"):
            row["fitted_parameter_identity"] = stable_hash(
                fitted[f"{candidate_id}_beta"]
            )
        elif candidate_id == "national_margin_ridge":
            row["fitted_parameter_identity"] = stable_hash(fitted["ridge_beta"])
        else:
            row["fitted_parameter_identity"] = None
        if margin_supported and not source["margin_rmse"]:
            raise ForecastSuiteViolation(
                f"{candidate_id} claims margin support without a development residual dispersion"
            )
        if not margin_supported and candidate["uncertainty_support"] not in {
            "UNCERTAINTY_NOT_ESTABLISHED",
        }:
            raise ForecastSuiteViolation(
                f"{candidate_id} claims an interval a probability-only family cannot support"
            )
        row["row_identity"] = stable_hash(row)
        rows.append(row)
    return sorted(rows, key=lambda item: item["candidate_id"])


def build_parameter_rows(fitted: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Persist the fitted deployment parameters so a consumer can score exactly."""
    rows = [
        {
            "parameter_set_id": "WEEK1_2026_DEPLOYMENT_DESIGN",
            "design_columns": fitted["design_columns"],
            "conference_levels": fitted["conference_levels"],
            "indicators": fitted["indicators"],
            "transforms": {
                key: value for key, value in sorted(fitted["transforms"].items())
            },
            "training_row_count": fitted["training_row_count"],
            "training_game_count": fitted["training_game_count"],
            "training_season_min": fitted["training_season_min"],
            "training_season_max": fitted["training_season_max"],
            "base_rate": round(float(fitted["base_rate"]), 10),
        },
        {
            "parameter_set_id": "NATIONAL_LOGISTIC_L2_BETA",
            "candidate_id": "national_logistic_l2",
            "feature_scope": "ALL_ADMITTED_FEATURES",
            "coefficients": [
                round(float(value), 10) for value in fitted["national_logistic_l2_beta"]
            ],
        },
        {
            "parameter_set_id": "PRIOR_ONLY_BETA",
            "candidate_id": "prior_only",
            "feature_scope": "PRIOR_OUTCOME_DOMAIN_AND_SITE",
            "coefficients": [
                round(float(value), 10) for value in fitted["prior_only_beta"]
            ],
        },
        {
            "parameter_set_id": "NATIONAL_MARGIN_RIDGE_BETA",
            "candidate_id": "national_margin_ridge",
            "feature_scope": "ALL_ADMITTED_FEATURES",
            "coefficients": [round(float(value), 10) for value in fitted["ridge_beta"]],
            "training_residual_stdev": round(
                float(fitted["ridge_training_residual_stdev"]), 10
            ),
            "logistic_link_scale_divisor": fitted["ridge_link_scale_divisor"],
        },
    ]
    for row in rows:
        row["row_identity"] = stable_hash(row)
    return rows


# ---------------------------------------------------------------------------
# expected surface
# ---------------------------------------------------------------------------


def build_expected(
    *,
    repo_root: Path,
    data_root: Path,
    inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved = dict(inputs if inputs is not None else load_inputs(repo_root, data_root))
    contract = resolved["contract"]
    frozen = frozen_hyperparameters(resolved["gates"]["frozen_candidates"])

    fitted = fit_deployment_models(
        contract=contract,
        features=resolved["features"],
        labels=resolved["labels"],
        frozen=frozen,
    )
    feature_rows = build_feature_rows(
        contract=contract,
        spine_rows=resolved["spine_rows"],
        cells=resolved["cells"],
        prior_rows=resolved["prior_rows"],
        ranking_rows=resolved["ranking_rows"],
        kickoff_rows=resolved["kickoff_rows"],
        entity_rows=resolved["entity_rows"],
        fitted=fitted,
    )
    requirements = candidate_requirements(resolved["gates"]["spine_semantic_successor"])
    ranking_completion = resolved["gates"]["authority_enrichment"]["ranking_completion"]
    adequacy_rows = build_adequacy_rows(
        contract=contract,
        requirements=requirements,
        feature_rows=feature_rows,
        ranking_completion=ranking_completion,
    )
    model_rows = build_model_binding_rows(
        contract=contract,
        frozen=frozen,
        fitted=fitted,
        adequacy_rows=adequacy_rows,
    )
    parameter_rows = build_parameter_rows(fitted)

    record_hashes = {
        "model_binding_rows": stable_hash(model_rows),
        "feature_rows": stable_hash(feature_rows),
        "adequacy_rows": stable_hash(adequacy_rows),
        "fitted_parameter_rows": stable_hash(parameter_rows),
    }
    contract_sha256 = hashlib.sha256(
        (repo_root / CONTRACT_RELATIVE).read_bytes()
    ).hexdigest()
    code_identity = sha256_file(Path(__file__).resolve())
    dataset_identity = stable_hash(
        {
            "classification": CLASSIFICATION,
            "code_identity": code_identity,
            "contract_sha256": contract_sha256,
            "record_hashes": record_hashes,
        }
    )

    focus_contest_identity = resolved["gates"]["authority_enrichment"][
        "focus_contest_report"
    ]["contest_identity"]
    focus_rows = [
        row
        for row in adequacy_rows
        if row["contest_identity"] == focus_contest_identity
    ]
    summary = {
        "candidate_count": len(model_rows),
        "oriented_row_count": len(feature_rows),
        "contest_count": len({row["contest_identity"] for row in feature_rows}),
        "adequacy_row_count": len(adequacy_rows),
        "readiness_counts": _counts([row["readiness_state"] for row in adequacy_rows]),
        "readiness_counts_by_candidate": {
            candidate["candidate_id"]: _counts(
                [
                    row["readiness_state"]
                    for row in adequacy_rows
                    if row["candidate_id"] == candidate["candidate_id"]
                ]
            )
            for candidate in contract["candidates"]
        },
        "margin_supported_candidates": sorted(
            row["candidate_id"]
            for row in model_rows
            if row["margin_support"] == "SUPPORTED_BY_MODEL_FAMILY"
        ),
        "uncertainty_supported_candidates": sorted(
            row["candidate_id"]
            for row in model_rows
            if row["uncertainty_support"] != "UNCERTAINTY_NOT_ESTABLISHED"
        ),
        "hyperparameter_drift_count": sum(
            1 for row in model_rows if row["hyperparameter_drift"]
        ),
        "fabricated_numeric_value_count": sum(
            int(row["fabricated_numeric_value_count"]) for row in feature_rows
        ),
        "features_neither_admitted_nor_indicator_covered": sorted(
            {
                feature
                for row in feature_rows
                for feature in row["features_neither_admitted_nor_indicator_covered"]
            }
        ),
        "training_row_count": fitted["training_row_count"],
        "training_game_count": fitted["training_game_count"],
        "training_season_min": fitted["training_season_min"],
        "training_season_max": fitted["training_season_max"],
        "forecast_emitted": False,
        "recommended_candidate": None,
    }

    focus_report = {
        "contest_identity": focus_contest_identity,
        "candidate_readiness": {
            row["candidate_id"]: row["readiness_state"]
            for row in sorted(focus_rows, key=lambda r: r["candidate_id"])
        },
        "oriented_row_count": len(focus_rows) // max(len(model_rows), 1),
        "tamu_specific_adjustment_applied": False,
        "custom_correction_applied": False,
    }

    return {
        "contract": contract,
        "contract_sha256": contract_sha256,
        "code_identity": code_identity,
        "dataset_identity": dataset_identity,
        "record_hashes": record_hashes,
        "model_binding_rows": model_rows,
        "feature_rows": feature_rows,
        "adequacy_rows": adequacy_rows,
        "fitted_parameter_rows": parameter_rows,
        "fitted": fitted,
        "summary": summary,
        "focus_contest_report": focus_report,
    }


PAYLOAD_ROLES = (
    (
        MODEL_PAYLOAD_NAME,
        "WEEK1_2026_FORECAST_MODEL_BINDING_ROWS",
        "model_binding_rows",
    ),
    (FEATURE_PAYLOAD_NAME, "WEEK1_2026_FORECAST_FEATURE_ROWS", "feature_rows"),
    (
        ADEQUACY_PAYLOAD_NAME,
        "WEEK1_2026_FORECAST_CANDIDATE_ADEQUACY_ROWS",
        "adequacy_rows",
    ),
    (
        PARAMETER_PAYLOAD_NAME,
        "WEEK1_2026_FORECAST_FITTED_PARAMETER_ROWS",
        "fitted_parameter_rows",
    ),
)


def enforce_invariants(gate: Mapping[str, Any]) -> None:
    """Fail closed on every binding invariant this decision unit owns."""
    if gate["protected_lane"] != PROTECTED_LANE:
        raise ForecastSuiteViolation("protected lane must remain blocked")
    if gate["lane"] != LANE:
        raise ForecastSuiteViolation("forecast suite lane drift")
    if gate["summary"]["candidate_count"] != 5:
        raise ForecastSuiteViolation("exactly five candidates must be represented")
    if gate["summary"]["forecast_emitted"] is not False:
        raise ForecastSuiteViolation("the binding gate must not emit a forecast")
    if gate["summary"]["recommended_candidate"] is not None:
        raise ForecastSuiteViolation("no candidate may be recommended in this cycle")
    if gate["summary"]["hyperparameter_drift_count"]:
        raise ForecastSuiteViolation(
            "hyperparameters drifted from the frozen candidate gate"
        )
    if gate["summary"]["fabricated_numeric_value_count"]:
        raise ForecastSuiteViolation("a numeric feature value was fabricated")
    if gate["summary"]["training_season_max"] > 2023:
        raise ForecastSuiteViolation("training evidence exceeded the allowed window")
    if gate["development_evidence"]["fitted_or_selected_on_week_zero"] is not False:
        raise ForecastSuiteViolation("Week Zero must not fit or select a candidate")
    if gate["development_evidence"]["fitted_or_selected_on_week1"] is not False:
        raise ForecastSuiteViolation("Week 1 must not fit or select a candidate")
    if gate["uncertainty"]["probability_interval_established"] is not False:
        raise ForecastSuiteViolation(
            "no probability interval authority exists in this cycle"
        )
    if (
        gate["bound_predecessors"]["predecessor_artifacts_rewritten_in_place"]
        is not False
    ):
        raise ForecastSuiteViolation("predecessor artifacts must not be rewritten")
    for key in ("t_minus_24h_state", "t_minus_90m_state"):
        if gate["checkpoints"].get(key) != "OPEN":
            raise ForecastSuiteViolation(f"{key} is no longer OPEN")
    for key in ("executed_early", "pregame_result_access", "week1_outcome_access"):
        if gate["checkpoints"].get(key) is not False:
            raise ForecastSuiteViolation(f"forbidden checkpoint behaviour: {key}")
    for key in ("custom_correction_applied", "tamu_specific_adjustment_applied"):
        if gate["tamu_policy"].get(key) is not False:
            raise ForecastSuiteViolation(
                f"an A&M-specific adjustment is declared: {key}"
            )
    for row in gate["candidate_bindings"]:
        if row["recommended"] or row["promoted"]:
            raise ForecastSuiteViolation(
                f"{row['candidate_id']} was promoted or recommended"
            )


def build_gate(
    *,
    expected: Mapping[str, Any],
    manifest_entry: Mapping[str, Any],
    payloads: Sequence[Mapping[str, Any]],
    execution_time_utc: str,
) -> dict[str, Any]:
    contract = expected["contract"]
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_NATIONAL_FORECAST_SUITE_GATE",
        "classification": CLASSIFICATION,
        "contract_id": CONTRACT_ID,
        "contract_sha256": expected["contract_sha256"],
        "decision_unit": contract["decision_unit"],
        "local_issue_id": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "season": contract["season"],
        "week_label": contract["week_label"],
        "result": PASS_RESULT,
        "issued_at_utc": execution_time_utc,
        "dataset_identity": expected["dataset_identity"],
        "record_hashes": expected["record_hashes"],
        "manifest": dict(manifest_entry),
        "payloads": [dict(item) for item in payloads],
        "candidate_bindings": [
            {
                key: row[key]
                for key in (
                    "candidate_id",
                    "family",
                    "feature_scope",
                    "hyperparameters",
                    "probability_form",
                    "margin_support",
                    "uncertainty_support",
                    "development_brier",
                    "development_log_loss",
                    "development_accuracy",
                    "development_calibration_slope",
                    "development_calibration_intercept",
                    "development_margin_mae",
                    "development_margin_rmse",
                    "week1_ready_row_count",
                    "week1_abstention_counts",
                    "never_recommended",
                    "promoted",
                    "recommended",
                    "fitted_parameter_identity",
                )
            }
            for row in expected["model_binding_rows"]
        ],
        "deployment_fit": {
            "training_partition": contract["deployment_fit"]["training_partition"],
            "training_row_count": expected["fitted"]["training_row_count"],
            "training_game_count": expected["fitted"]["training_game_count"],
            "training_season_min": expected["fitted"]["training_season_min"],
            "training_season_max": expected["fitted"]["training_season_max"],
            "transform_fit_scope": contract["deployment_fit"]["transform_fit_scope"],
            "design_column_counts": {
                scope: len(columns)
                for scope, columns in sorted(
                    expected["fitted"]["design_columns"].items()
                )
            },
            "conference_level_count": len(expected["fitted"]["conference_levels"]),
            "learned_indicator_count": len(expected["fitted"]["indicators"]),
            "elo_refit_in_this_unit": False,
            "hyperparameter_search_performed": False,
        },
        "development_evidence": contract["development_evidence"],
        "uncertainty": contract["uncertainty"],
        "adequacy": {
            "verdicts": contract["adequacy_verdicts"],
            "partial_model_input_may_emit_a_forecast": False,
            "readiness_counts": expected["summary"]["readiness_counts"],
            "readiness_counts_by_candidate": expected["summary"][
                "readiness_counts_by_candidate"
            ],
        },
        "bound_predecessors": {
            "frozen_candidate_gate_identity": contract["sources"]["frozen_candidates"][
                "gate_identity"
            ],
            "spine_semantic_successor_gate_identity": contract["sources"][
                "spine_semantic_successor"
            ]["gate_identity"],
            "authority_enrichment_gate_identity": contract["sources"][
                "authority_enrichment"
            ]["gate_identity"],
            "frozen_strength_prior_gate_identity": contract["sources"][
                "frozen_strength_prior"
            ]["gate_identity"],
            "chronological_matrix_gate_sha256": contract["sources"][
                "chronological_development_matrix"
            ]["gate_sha256"],
            "preserved_predecessor_forecast_rows": contract["predecessor_immutability"][
                "preserved_predecessor_forecast_rows"
            ],
            "predecessor_artifacts_rewritten_in_place": False,
        },
        "summary": expected["summary"],
        "focus_contest_report": expected["focus_contest_report"],
        "checkpoints": contract["checkpoints"],
        "tamu_policy": contract["tamu_policy"],
        "scientific_nonclaims": contract["scientific_nonclaims"],
    }
    enforce_invariants(gate)
    gate["gate_identity"] = compute_gate_identity(gate)
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
    identity = resolved["dataset_identity"]
    canonical_root = data_root / "canonical" / PAYLOAD_SLUG / "sha256" / identity
    manifest_root = data_root / "manifests" / PAYLOAD_SLUG / "sha256" / identity

    payloads: list[dict[str, Any]] = []
    for name, role, key in PAYLOAD_ROLES:
        rows = resolved[key]
        payload_bytes = jsonl_bytes(rows)
        path = canonical_root / name
        _write_bytes(path, payload_bytes)
        payloads.append(
            {
                "name": name,
                "role": role,
                "relative_path": _relative(path, data_root),
                "rows": len(rows),
                "bytes": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_NATIONAL_FORECAST_SUITE_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": resolved["contract"]["decision_unit"],
        "local_issue_id": LOCAL_ISSUE_ID,
        "dataset_identity": identity,
        "issued_at_utc": execution_time_utc,
        "classification": CLASSIFICATION,
        "record_hashes": resolved["record_hashes"],
        "summary": resolved["summary"],
        "payloads": payloads,
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "code_identity": resolved["code_identity"],
            "contract_sha256": resolved["contract_sha256"],
        },
    }
    manifest_path = manifest_root / f"{PAYLOAD_SLUG}_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")

    gate = build_gate(
        expected=resolved,
        manifest_entry={
            "relative_path": _relative(manifest_path, data_root),
            "dataset_identity": identity,
            "authoritative_sha256": manifest_authoritative_sha256(manifest),
        },
        payloads=[
            {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256")}
            for item in payloads
        ],
        execution_time_utc=execution_time_utc,
    )
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {"gate": gate, "manifest": manifest, "expected": resolved}


def _compare(path: str, actual: Any, expected: Any, errors: list[str]) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            errors.append(f"{path}: expected object")
            return
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                errors.append(f"{path}.{key}: unexpected key")
            elif key not in actual:
                errors.append(f"{path}.{key}: missing key")
            else:
                _compare(f"{path}.{key}", actual[key], expected[key], errors)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            errors.append(f"{path}: list shape mismatch")
            return
        for index, (left, right) in enumerate(zip(actual, expected)):
            _compare(f"{path}[{index}]", left, right, errors)
        return
    if actual != expected:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    repo_root: Path,
    data_root: Path,
    require_rebuild: bool = True,
) -> dict[str, Any]:
    """Independently refit the binding and refuse any unearned execution claim."""
    gate = read_json(repo_root / GATE_RELATIVE)
    if gate.get("result") != PASS_RESULT:
        raise ForecastSuiteViolation(
            f"forecast suite gate is not passing: {gate.get('result')}"
        )
    enforce_invariants(gate)
    if compute_gate_identity(gate) != gate.get("gate_identity"):
        raise ForecastSuiteViolation(
            "gate identity does not match its identity-bearing fields"
        )
    if binding_identity(gate, "binding_identity") != gate.get("binding_identity"):
        raise ForecastSuiteViolation("cross-surface binding identity drift")
    if not require_rebuild:
        return {
            "result": "PASS",
            "mode": "SCHEMA_ONLY",
            "gate_identity": gate["gate_identity"],
        }

    expected = build_expected(repo_root=repo_root, data_root=data_root)
    errors: list[str] = []
    if gate["dataset_identity"] != expected["dataset_identity"]:
        errors.append("dataset identity drift")
    _compare("record_hashes", gate["record_hashes"], expected["record_hashes"], errors)
    _compare("summary", gate["summary"], expected["summary"], errors)
    _compare(
        "focus_contest_report",
        gate["focus_contest_report"],
        expected["focus_contest_report"],
        errors,
    )

    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    if (
        manifest_authoritative_sha256(manifest)
        != gate["manifest"]["authoritative_sha256"]
    ):
        errors.append("manifest authoritative content drift")
    for payload in gate["payloads"]:
        entry = next(
            (item for item in manifest["payloads"] if item["name"] == payload["name"]),
            None,
        )
        if entry is None:
            errors.append(f"payload missing from manifest: {payload['name']}")
            continue
        for key in ("rows", "bytes", "sha256", "role"):
            if entry[key] != payload[key]:
                errors.append(f"payload {payload['name']} {key} drift")
        path = data_root / entry["relative_path"]
        if not path.is_file():
            errors.append(f"payload absent on disk: {entry['relative_path']}")
        elif sha256_file(path) != entry["sha256"]:
            errors.append(f"payload rehash drift: {entry['relative_path']}")

    for row in expected["adequacy_rows"]:
        if row["readiness_state"] == READY and row["abstention_reasons"]:
            errors.append("a ready row carries an abstention reason")
        if row["readiness_state"] != READY and not row["abstention_reasons"]:
            errors.append("an abstaining row carries no reason")
    for row in expected["feature_rows"]:
        if row["fabricated_numeric_value_count"]:
            errors.append("a fabricated numeric feature value entered a Week 1 row")
    for row in expected["model_binding_rows"]:
        if (
            row["margin_support"] != "SUPPORTED_BY_MODEL_FAMILY"
            and row["margin_interval_dispersion"]
        ):
            errors.append(
                f"{row['candidate_id']} carries a margin dispersion it cannot support"
            )
        if row["hyperparameter_drift"]:
            errors.append(f"{row['candidate_id']} hyperparameters drifted")

    if errors:
        raise ForecastSuiteViolation(
            "independent forecast-suite validation failed: " + "; ".join(errors[:16])
        )
    return {
        "result": "PASS",
        "mode": "INDEPENDENT_REBUILD",
        "dataset_identity": gate["dataset_identity"],
        "gate_identity": gate["gate_identity"],
        "summary": gate["summary"],
        "focus_contest_report": gate["focus_contest_report"],
    }
