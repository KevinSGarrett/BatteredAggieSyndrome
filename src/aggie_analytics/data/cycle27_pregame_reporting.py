"""Cycle 27 focus-forecast diagnostic, score-model readiness, and interim pregame report.

Reads frozen A&M/Missouri State payloads. Does not rewrite predecessor rows,
fabricate predicted scores, hardcode a 40-point spread, call an interim report
T24/T90, treat quoted transcripts as captures, or blend BAS margin with a
market total as an independent BAS score.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.data.cycle27_coaching_reporting import (
    CLASSIFICATION as COACHING_CLASSIFICATION,
    COACHES_POLL_FIELDS,
    FOCUS_AWAY_CANONICAL,
    FOCUS_AWAY_LABEL,
    FOCUS_CONTEST_ID,
    FOCUS_HOME_CANONICAL,
    FOCUS_HOME_LABEL,
    NOT_CONSUMED,
    NOT_CONSUMED_BY_MODEL,
    canonical_json_bytes,
    classify_feature_as_staff_evidence,
    load_json,
    load_jsonl,
    payload_relative_path,
    sha256_bytes,
    utc_now_label,
    write_json_dual,
)

SCHEMA_VERSION = "aggie.data.cycle27_pregame_reporting.v1"
CONTRACT_ID = "CYCLE27-PREGAME-REPORTING-V1"
JIRA_KEY = "BAT-690"
PARENT_JIRA_KEY = "BAT-523"
INTERIM_LABEL = "INTERIM_AS_OF_NOW_NOT_T24H_NOT_T90M"
T24H_EVIDENCE_LABEL = "T-24H_EVIDENCE_CAPTURED_NOT_FORECAST_FROZEN"
T90M_EVIDENCE_LABEL = "T-90M_EVIDENCE_CAPTURED_NOT_FORECAST_FROZEN"
CONTROL_CANDIDATE = "national_base_rate"
RIDGE_CANDIDATE = "national_margin_ridge"
CONTRIBUTION_TOLERANCE = 1e-6
CAPTURE_SOURCES = frozenset(
    {
        "provider_retrieval_receipt",
        "official_source_receipt",
        "declared_api_route",
    }
)
TRANSCRIPT_SOURCES = frozenset(
    {
        "user_transcript",
        "quoted_transcript",
        "chat",
        "manager_browser_observation",
        "user_quotation",
        "supplied_cli_time",
    }
)
CONSUMPTION_LABELS = frozenset(
    {
        "ACTUALLY_CONSUMED",
        "CONTEXT_ONLY",
        "CANDIDATE_ONLY",
        "ABSENT",
        "BLOCKED",
    }
)
DIAGNOSTIC_CLASSES = frozenset(
    {
        "CONFIRMED_IMPLEMENTATION_DEFECT",
        "INPUT_LIMITATION",
        "MODEL_SPECIFICATION_LIMITATION",
        "UNEXPLAINED_DISAGREEMENT",
    }
)
SCORE_FOLLOW_ON = (
    "Authority-clean historical points-for/against labels and features.",
    "National chronological training with train-only transforms.",
    "Coherent nonnegative team-score/total/margin joint distribution.",
    "Declared overtime and market-settlement treatment.",
    "Out-of-sample score, total, margin, and probability evaluation.",
    "Interval coverage under the declared joint model.",
    "Immutable future forecasts; algebraic score+margin+total cross-checks.",
)


class PregameReportingError(ValueError):
    """Raised when a pregame diagnostic or report would be dishonest."""


class ContributionSumError(PregameReportingError):
    """Ridge contributions must sum to the reconstructed margin."""


def admit_market_quote(quote: Mapping[str, Any] | None) -> dict[str, Any]:
    """A quoted transcript or user observation is not a capture receipt."""
    if not isinstance(quote, Mapping):
        return {
            "admitted": False,
            "reason": "NO_QUOTE",
            "classification": "ABSENT",
        }
    source = str(
        quote.get("acquisition_source")
        or quote.get("source")
        or quote.get("capture_source")
        or ""
    )
    if source in TRANSCRIPT_SOURCES or not source:
        return {
            "admitted": False,
            "reason": "QUOTED_TRANSCRIPT_IS_NOT_CAPTURE"
            if source in TRANSCRIPT_SOURCES
            else "NOT_A_CAPTURE_RECEIPT",
            "classification": "REJECTED_NOT_CAPTURE",
            "acquisition_source": source or None,
        }
    if source not in CAPTURE_SOURCES:
        return {
            "admitted": False,
            "reason": "NOT_A_CAPTURE_RECEIPT",
            "classification": "REJECTED_NOT_CAPTURE",
            "acquisition_source": source,
        }
    return {
        "admitted": True,
        "reason": "CAPTURE_RECEIPT",
        "classification": "CAPTURED",
        "acquisition_source": source,
        "quote": dict(quote),
    }


def captured_focus_quote_count(
    *,
    consensus: Mapping[str, Any] | None,
    quote_rows: Sequence[Mapping[str, Any]],
    contest_id: str = FOCUS_CONTEST_ID,
) -> dict[str, Any]:
    """Count only consensus quote_count and exact contest-id rows. Names are not receipts."""
    exact_rows = [
        row
        for row in quote_rows
        if str(row.get("ncaa_contest_id") or "") == str(contest_id)
    ]
    consensus_count = int((consensus or {}).get("quote_count") or 0)
    return {
        "quote_count": consensus_count,
        "exact_contest_id_quote_rows": len(exact_rows),
        "name_key_fuzzy_match_used": False,
        "status": "ABSENT" if consensus_count == 0 else "CAPTURED",
        "label": (consensus or {}).get("label") or "INSUFFICIENT_MARKET_COVERAGE",
    }


def market_line_implied_score(
    *,
    total: Any,
    home_spread: Any,
    sportsbook: str | None,
    spread_book: str | None,
    total_book: str | None,
    spread_as_of_utc: str | None,
    total_as_of_utc: str | None,
    contest_identity: str | None = None,
) -> dict[str, Any]:
    """Algebraic line-implied scores; withhold incompatible or incomplete quotes."""
    quotes = {
        "total": total,
        "home_spread": home_spread,
        "sportsbook": sportsbook,
        "spread_book": spread_book,
        "total_book": total_book,
        "spread_as_of_utc": spread_as_of_utc,
        "total_as_of_utc": total_as_of_utc,
        "contest_identity": contest_identity,
    }
    if sportsbook is None and (spread_book is None or total_book is None):
        return _incompatible_score("MISSING_BOOK_IDENTITY", quotes)
    if (spread_book or sportsbook) != (total_book or sportsbook):
        return _incompatible_score("INCOMPATIBLE_SPREAD_TOTAL_PAIRING", quotes)
    if (spread_as_of_utc or "") != (total_as_of_utc or ""):
        return _incompatible_score("INCOMPATIBLE_AS_OF_TIMESTAMPS", quotes)
    try:
        total_value = float(total)
        spread_value = float(home_spread)
    except (TypeError, ValueError):
        return _incompatible_score("NONFINITE_OR_MISSING_NUMERIC_INPUTS", quotes)
    if not math.isfinite(total_value) or not math.isfinite(spread_value):
        return _incompatible_score("NONFINITE_OR_MISSING_NUMERIC_INPUTS", quotes)
    if total_value <= 0:
        return _incompatible_score("NONPOSITIVE_TOTAL", quotes)
    home_margin_ref = -spread_value
    home_points = (total_value + home_margin_ref) / 2.0
    away_points = (total_value - home_margin_ref) / 2.0
    arithmetic = {
        "home_margin_reference": home_margin_ref,
        "home_points": home_points,
        "away_points": away_points,
        "sum": home_points + away_points,
        "difference_home_minus_away": home_points - away_points,
    }
    if home_points < 0 or away_points < 0:
        return {
            "status": "INCOMPATIBLE_SCORE_REFERENCE",
            "reason": "NEGATIVE_IMPLIED_TEAM_POINTS",
            "independent_bas_score": False,
            "quotes_retained": quotes,
            "arithmetic_not_published_as_score": arithmetic,
            "clamped": False,
        }
    if abs(arithmetic["sum"] - total_value) > 1e-9:
        return _incompatible_score("SUM_DOES_NOT_RECOVER_TOTAL", quotes)
    if abs(arithmetic["difference_home_minus_away"] - home_margin_ref) > 1e-9:
        return _incompatible_score("DIFFERENCE_DOES_NOT_RECOVER_MARGIN", quotes)
    return {
        "status": "MARKET_LINE_IMPLIED_SCORE_REFERENCE",
        "independent_bas_score": False,
        "betting_recommendation": False,
        "calibrated_score_distribution": False,
        "quotes": quotes,
        "home_points": home_points,
        "away_points": away_points,
        "formula": "(total + home_margin_ref)/2 and (total - home_margin_ref)/2",
        "home_margin_reference": home_margin_ref,
    }


def _incompatible_score(reason: str, quotes: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "INCOMPATIBLE_SCORE_REFERENCE",
        "reason": reason,
        "independent_bas_score": False,
        "quotes_retained": dict(quotes),
        "clamped": False,
        "home_points": None,
        "away_points": None,
    }


def independent_scores_from_margin_only(
    margin: Any, *, total: Any = None
) -> dict[str, Any]:
    """Margin alone cannot identify both team scores."""
    if total is not None:
        return {
            "independent_predicted_score": None,
            "blocker": "DO_NOT_BLEND_BAS_MARGIN_WITH_MARKET_TOTAL_AS_INDEPENDENT_BAS_SCORE",
            "margin": margin,
            "total_ignored": total,
        }
    return {
        "independent_predicted_score": None,
        "blocker": "MARGIN_ALONE_CANNOT_IDENTIFY_BOTH_TEAM_SCORES",
        "margin": margin,
    }


def ridge_contributions(
    columns: Sequence[str],
    values: Sequence[float],
    coefficients: Sequence[float],
    *,
    reconstructed_margin: float,
    tolerance: float = CONTRIBUTION_TOLERANCE,
) -> list[dict[str, Any]]:
    if not (len(columns) == len(values) == len(coefficients)):
        raise ContributionSumError("contribution vectors have unequal length")
    rows = []
    total = 0.0
    for name, value, coefficient in zip(columns, values, coefficients):
        contribution = float(value) * float(coefficient)
        total += contribution
        rows.append(
            {
                "column": name,
                "value": float(value),
                "coefficient": float(coefficient),
                "contribution": contribution,
            }
        )
    if not math.isfinite(total) or abs(total - float(reconstructed_margin)) > tolerance:
        raise ContributionSumError(
            "ridge contributions do not sum to reconstructed margin: "
            f"{total} vs {reconstructed_margin}"
        )
    return rows


def classify_subgroup_analysis(
    *,
    motivated_by_observed_disagreement: bool,
    labeled_as: str,
) -> dict[str, Any]:
    """Criteria prompted by the already-observed disagreement stay EXPLORATORY."""
    label = str(labeled_as or "")
    confirmation_labels = {
        "CONFIRMATION",
        "INDEPENDENT_CONFIRMATION",
        "CONFIRMED",
        "VALIDATED",
    }
    if motivated_by_observed_disagreement:
        if label in confirmation_labels:
            raise PregameReportingError(
                "exploratory subgroup cannot be relabeled independent confirmation"
            )
        return {
            "status": "EXPLORATORY",
            "motivated_by_observed_disagreement": True,
            "independent_confirmation": False,
            "rejected_relabel": label or None,
        }
    if label in confirmation_labels:
        raise PregameReportingError(
            "confirmation label requires a predeclared untouched evaluation"
        )
    return {
        "status": "EXPLORATORY" if not label else label,
        "motivated_by_observed_disagreement": False,
        "independent_confirmation": False,
    }


def classify_disagreement(classes: Sequence[str]) -> list[str]:
    unique = []
    for item in classes:
        if item not in DIAGNOSTIC_CLASSES:
            raise PregameReportingError(f"illegal diagnostic class: {item}")
        if item not in unique:
            unique.append(item)
    if not unique:
        raise PregameReportingError("diagnostic class list is empty")
    return unique


def reconstruct_ridge_row(
    feature_values: Mapping[str, Any],
    *,
    transforms: Mapping[str, Any],
    levels: Sequence[str],
    indicators: Sequence[str],
    coefficients: Sequence[float],
    reconstructed_margin: float,
) -> dict[str, Any]:
    try:
        from aggie_analytics.modeling.national_expectation_baselines import (
            build_design,
        )
    except ImportError as exc:
        raise PregameReportingError(
            "ridge reconstruction requires numpy-backed design matrices"
        ) from exc
    matrix, columns = build_design(
        [dict(feature_values)],
        scope="ALL_ADMITTED_FEATURES",
        transforms=transforms,
        levels=levels,
        indicators=indicators,
    )
    named = ["intercept", *columns]
    values = [float(item) for item in matrix[0]]
    if len(values) != len(coefficients):
        raise PregameReportingError(
            f"design width {len(values)} != coefficient width {len(coefficients)}"
        )
    prediction = float(
        sum(float(value) * float(coef) for value, coef in zip(values, coefficients))
    )
    contributions = ridge_contributions(
        named,
        values,
        [float(item) for item in coefficients],
        reconstructed_margin=reconstructed_margin,
    )
    ranked = sorted(
        contributions, key=lambda row: abs(row["contribution"]), reverse=True
    )
    return {
        "reconstructed_margin": prediction,
        "target_margin": reconstructed_margin,
        "contribution_sum": sum(row["contribution"] for row in contributions),
        "contributions": contributions,
        "largest_abs_contributions": ranked[:12],
        "causal_interpretation": False,
    }


def input_consumption_table(
    *,
    feature_values_by_orientation: Mapping[str, Mapping[str, Any]],
    admitted_names_by_orientation: Mapping[str, Sequence[str]],
    weather_admitted: bool,
    market_quotes_for_contest: int,
    coaching_consumed: bool,
    coaching_context_label: str = "ABSENT",
) -> list[dict[str, Any]]:
    home = feature_values_by_orientation.get("HOME") or {}
    away = feature_values_by_orientation.get("AWAY") or {}
    admitted = set(admitted_names_by_orientation.get("HOME") or ()) | set(
        admitted_names_by_orientation.get("AWAY") or ()
    )
    strength_fields = [
        name
        for name in (
            "prior_games_played",
            "opponent_prior_games_played",
            "is_home",
            "is_neutral_site",
            "team_is_fbs",
            "team_conference",
            "ap_poll_rank",
            "opponent_ap_poll_rank",
            "rankings_source_available",
            "season_to_date_games",
        )
        if name in home or name in away or name in admitted
    ]
    missingness = [
        name for name in list(home) + list(away) if str(name).endswith("_missing")
    ]
    rows = [
        _consumption_row(
            "coaching",
            "ACTUALLY_CONSUMED" if coaching_consumed else coaching_context_label,
            "No HC/OC/DC/play-caller columns in active Week1 designs. "
            "coaches_poll_rank is a poll, not staff. Official staff packets, if any, "
            "remain CONTEXT_ONLY / NOT_CONSUMED_BY_MODEL.",
            evidence=[
                "week1_2026_national_forecast_suite.py feature_values",
                "ALL_NUMERIC",
            ],
        ),
        _consumption_row(
            "recruiting_talent",
            "ABSENT",
            "national_pit_domain_admission coaching-adjacent recruiting_talent SOURCE_ABSENT.",
            evidence=["configs/national_pit_domain_admission_matrix_contract.json"],
        ),
        _consumption_row(
            "roster_availability",
            "ABSENT",
            "Spine ROSTER_MEMBERSHIP and PREGAME_AVAILABILITY SOURCE_EVIDENCE_ABSENT for 182 cells.",
            evidence=[
                "week1_2026_spine_semantic_successor_gate.json domain_admission_counts"
            ],
        ),
        _consumption_row(
            "weather",
            "CANDIDATE_ONLY" if not weather_admitted else "ACTUALLY_CONSUMED",
            "week1_feature_construction.weather_admitted_as_model_input is false; "
            "weather vintage capture is not a consumed feature.",
            evidence=["configs/week1_2026_national_forecast_suite_contract.json"],
        ),
        _consumption_row(
            "travel_rest",
            "ABSENT",
            "No travel/rest feature columns in ALL_ADMITTED_FEATURES.",
            evidence=["national_expectation_baselines.ALL_NUMERIC/ALL_BOOLEAN"],
        ),
        _consumption_row(
            "market",
            "CONTEXT_ONLY" if market_quotes_for_contest else "ABSENT",
            "Market references attach separately and do not enter the fitted design. "
            f"Captured focus-contest quotes: {market_quotes_for_contest}.",
            evidence=[
                "CYCLE26_MARKET_REFERENCE_DISPOSITION.json",
                "week1_2026_early_market_consensus.jsonl",
            ],
        ),
        _consumption_row(
            "strength_context",
            "ACTUALLY_CONSUMED",
            "Prior game counts, site, FBS, conference (when in training levels), "
            "AP rank when present, and learned missingness indicators.",
            evidence=strength_fields or ["feature_values"],
        ),
        _consumption_row(
            "coaches_poll_rank",
            "ACTUALLY_CONSUMED",
            "Consumed as Coaches Poll ranking with missingness indicator; not staff.",
            evidence=sorted(COACHES_POLL_FIELDS),
        ),
        _consumption_row(
            "learned_missingness",
            "ACTUALLY_CONSUMED",
            "Missing prior rates/margins/ranks/venue fields are explicit indicators, "
            "not imputed means without an indicator.",
            evidence=sorted(set(missingness))[:20],
        ),
    ]
    for row in rows:
        if row["label"] not in CONSUMPTION_LABELS:
            raise PregameReportingError(f"illegal consumption label: {row['label']}")
    return rows


def _consumption_row(
    domain: str, label: str, note: str, evidence: Sequence[str]
) -> dict[str, Any]:
    mapped = "ABSENT" if label == NOT_CONSUMED else label
    return {
        "domain": domain,
        "label": mapped,
        "note": note,
        "evidence": list(evidence),
        "advertised_schema_is_not_model_use": True,
    }


def checkpoint_lineage(
    *,
    c24_ridge: Mapping[str, Any],
    c26_ridge: Mapping[str, Any],
    c24_gate_identity: str,
    c26_gate_identity: str,
    c26_dataset_identity: str,
    predecessor_rows_rewritten: bool,
) -> dict[str, Any]:
    if predecessor_rows_rewritten:
        raise PregameReportingError("predecessor rows must remain immutable")
    return {
        "C24": {
            "checkpoint_id": "EARLY_WEEK1",
            "gate_identity": c24_gate_identity,
            "payload": "week1_2026_early_forecast_adequacy",
            "ridge_probability_home": c24_ridge.get("probability_home"),
            "ridge_expected_margin_home": c24_ridge.get("expected_margin_home"),
            "ridge_interval_home": c24_ridge.get("margin_interval_home"),
            "note": "Original freeze. Ridge probability used the later-corrected saturated link.",
            "rewritten": False,
        },
        "C25": {
            "checkpoint_id": "NOT_A_NEW_FREEZE_OF_THIS_CONTEST",
            "payload": "week1_2026_ridge_distribution_coherence / input-binding successors",
            "status": "DEPRECATED_PREDECESSOR_NOT_USED_AS_ACTIVE_FOCUS_PAYLOAD",
            "note": "C26 reads C24 early forecast rows, not a C25 transplanted row set. Predecessor files remain.",
            "rewritten": False,
        },
        "C26": {
            "checkpoint_id": "EARLY_WEEK1_SUCCESSOR_NOT_T24H_NOT_T90M",
            "gate_identity": c26_gate_identity,
            "dataset_identity": c26_dataset_identity,
            "ridge_probability_home": c26_ridge.get("probability_home"),
            "ridge_expected_margin_home": c26_ridge.get("expected_margin_home"),
            "ridge_interval_home": c26_ridge.get("margin_interval_home"),
            "nominal_interval_level_emitted": c26_ridge.get("nominal_interval_level"),
            "declared_interval_probability": 0.8,
            "forecast_row_identity_reused_from_predecessor": c26_ridge.get(
                "forecast_row_identity"
            ),
            "note": "Probability/interval math changed; expected margin equals C24; row IDs reused.",
            "rewritten_predecessor_files": False,
        },
        "changes": [
            {
                "from": "C24",
                "to": "C26",
                "field": "probability_home",
                "before": c24_ridge.get("probability_home"),
                "after": c26_ridge.get("probability_home"),
                "reason": "Normal residual CDF replaced saturated-link probability; margin unchanged.",
            },
            {
                "from": "C24",
                "to": "C26",
                "field": "expected_margin_home",
                "before": c24_ridge.get("expected_margin_home"),
                "after": c26_ridge.get("expected_margin_home"),
                "reason": "Successor preserves predecessor ridge margin.",
            },
            {
                "from": "C24",
                "to": "C26",
                "field": "margin_interval_home",
                "before": c24_ridge.get("margin_interval_home"),
                "after": c26_ridge.get("margin_interval_home"),
                "reason": "Interval recomputed from residual stdev at declared mass 0.8; emitted label 0.95.",
            },
        ],
        "predecessor_rows_rewritten": False,
    }


def build_score_model_readiness(
    *,
    issued_at_utc: str,
    week1_candidates: Sequence[str],
    ridge_emits_margin: bool,
    joint_score_interface_present: bool,
    poisson_runtime_present: bool,
    elo_offense_defense_exposed_seasons: Sequence[int],
    unprotected_baseline_target_seasons: Sequence[int],
    eligible_week1_score_candidate: bool,
    code_head: str | None = None,
) -> dict[str, Any]:
    exposed = sorted(set(int(year) for year in elo_offense_defense_exposed_seasons))
    unprotected = sorted(set(int(year) for year in unprotected_baseline_target_seasons))
    blocker = (
        None
        if eligible_week1_score_candidate
        else (
            "NO_ELIGIBLE_WEEK1_JOINT_SCORE_OR_TOTAL_CANDIDATE; "
            "active suite emits probability and ridge margin only; "
            "JointScoreDistribution/IndependentPoissonScoreRuntime are interfaces/"
            "experiments, not frozen Week1 outputs; "
            "preliminary Poisson and offense/defense Elo used 2024/2025 which are "
            "historically exposed and not blind; deprecated experiments are not enabled."
        )
    )
    readiness = {
        "artifact_type": "SCORE_MODEL_READINESS",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": "CYCLE27_SCORE_MODEL_READINESS_NOT_WEEK1_ELIGIBLE",
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "issued_at_utc": issued_at_utc,
        "code_head": code_head,
        "planned_interfaces": {
            "JointScoreDistribution": joint_score_interface_present,
            "path": "src/aggie_analytics/modeling/contracts.py",
            "week1_frozen_output": False,
        },
        "experimental_score_models": {
            "IndependentPoissonScoreRuntime": poisson_runtime_present,
            "path": "src/aggie_analytics/modeling/joint.py",
            "requires_expected_team_points_features": True,
            "present_in_active_week1_design": False,
            "enabled_for_week1": False,
            "preliminary_poisson_unprotected_baselines": {
                "tool": "tools/run_preliminary_unprotected_baselines.py",
                "classification": "PRELIMINARY_UNPROTECTED",
                "target_seasons": unprotected,
                "2024_2025_blind": False,
            },
            "elo_offense_defense_score_components": {
                "contract": "configs/elo_offense_defense_challenger_contract.json",
                "classification": "PRELIMINARY_UNPROTECTED_EXPOSURE_AWARE",
                "report_only_exposed_seasons": exposed,
                "candidate_only": True,
                "protected_performance": False,
                "enabled_for_week1": False,
            },
        },
        "fitted_authority_clean_week1_score_candidate": False,
        "prospective_frozen_week1_score_outputs": False,
        "validated_score_performance": False,
        "active_week1_candidates": list(week1_candidates),
        "ridge_emits_margin": ridge_emits_margin,
        "margin_identifies_both_team_scores": False,
        "protected_seasons_2024_2025_not_blind": True,
        "deprecated_experiments_enabled": False,
        "independent_predicted_score": None,
        "independent_predicted_score_blocker": blocker,
        "follow_on_requirements": list(SCORE_FOLLOW_ON),
        "scientific_nonclaims": [
            "Does not state that score modeling was never implemented.",
            "Does not repackage 2024/2025 experiments as blind validation.",
            "Does not invent score intervals from a margin interval alone.",
            "A market-line implied score is not an independent BAS score.",
        ],
        "result": "PASS_SCORE_MODEL_READINESS_NULL_SCORE",
    }
    readiness["gate_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in readiness.items() if key != "gate_identity"}
        )
    )
    return readiness


def _load_receipt_pointer(checkpoint: str) -> dict[str, Any] | None:
    latest = Path(
        r"C:\BatteredAggieSyndrome.data\ops\cycle27\receipts"
        rf"\{checkpoint}\LATEST.json"
    )
    if not latest.is_file():
        return None
    pointer = json.loads(latest.read_text(encoding="utf-8-sig"))
    receipt_path = Path(str(pointer.get("receipt_path") or ""))
    if not receipt_path.is_file():
        return None
    return json.loads(receipt_path.read_text(encoding="utf-8"))


def load_am_t24h_evidence_receipt() -> dict[str, Any] | None:
    return _load_receipt_pointer("AM_T24H_20260904T2300Z")


def load_am_checkpoint_evidence_receipt() -> dict[str, Any] | None:
    t90 = _load_receipt_pointer("AM_T90M_20260905T2130Z")
    if t90 is not None:
        return t90
    return load_am_t24h_evidence_receipt()


def render_pregame_report(
    *,
    issued_at_utc: str,
    candidates: Sequence[Mapping[str, Any]],
    market: Mapping[str, Any],
    implied_score: Mapping[str, Any],
    coaching: Mapping[str, Any],
    disagreement: Mapping[str, Any],
    score_readiness: Mapping[str, Any],
    consumption: Sequence[Mapping[str, Any]],
    other_models: Sequence[Mapping[str, Any]],
    evidence_checkpoint: Mapping[str, Any] | None = None,
) -> str:
    label = INTERIM_LABEL
    title = "INTERIM"
    extra = "This is not a T-24H or T-90M packet."
    checkpoint_label = (evidence_checkpoint or {}).get("checkpoint_label")
    forecast_frozen = bool((evidence_checkpoint or {}).get("forecast_frozen"))
    if checkpoint_label == "T-90M" and not forecast_frozen:
        label = T90M_EVIDENCE_LABEL
        title = "T-90M evidence"
        extra = (
            "T-90M evidence is captured for contest 6607349. "
            "This is EVIDENCE_CAPTURED, not FORECAST_FROZEN. "
            "The table below is the preserved C26 EARLY_WEEK1 successor, not a new T-90M freeze."
        )
    elif checkpoint_label == "T-24H" and not forecast_frozen:
        label = T24H_EVIDENCE_LABEL
        title = "T-24H evidence"
        extra = (
            "T-24H evidence is captured for contest 6607349. "
            "This is EVIDENCE_CAPTURED, not FORECAST_FROZEN. "
            "The table below is the preserved C26 EARLY_WEEK1 successor, not a new T-24H freeze."
        )
    lines = [
        f"# Pregame research report — {title}",
        "",
        f"**Label:** `{label}`. {extra}",
        f"**As of (UTC):** {issued_at_utc}",
        f"**Contest:** NCAA `{FOCUS_CONTEST_ID}` — {FOCUS_HOME_LABEL} (home) vs {FOCUS_AWAY_LABEL} (away).",
        "**Kickoff bound:** 2026-09-05T23:00:00Z (from frozen payload).",
        "**Hold:** ACTIVE. Merge unauthorized. Scientific Done unauthorized.",
        "**Trust:** `UNTRUSTED_SHADOW`. The 50% control is a control, never a recommendation.",
        "",
        "## BAS candidates (frozen C26 successor of C24 EARLY_WEEK1)",
        "",
        "| Candidate | P(home) | P(away) | Margin home | Interval home | Interval level emitted | Trust | Role |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in candidates:
        interval = row.get("margin_interval_home")
        interval_text = "null" if interval is None else str(interval)
        margin = row.get("expected_margin_home")
        margin_text = "null" if margin is None else f"{margin}"
        role = (
            "control"
            if row.get("candidate_id") == CONTROL_CANDIDATE
            else "shadow candidate"
        )
        if row.get("never_recommended"):
            role = "control (never recommended)"
        lines.append(
            "| {candidate} | {p_home} | {p_away} | {margin} | {interval} | {level} | {trust} | {role} |".format(
                candidate=row.get("candidate_id"),
                p_home=row.get("probability_home"),
                p_away=row.get("probability_away"),
                margin=margin_text,
                interval=interval_text,
                level=row.get("nominal_interval_level"),
                trust=row.get("trust_classification") or "UNTRUSTED_SHADOW",
                role=role,
            )
        )
    lines.extend(
        [
            "",
            "Ridge probability, margin, and interval are from the same declared Normal residual. "
            "Emitted `nominal_interval_level=0.95` does not match declared mass 0.8 "
            "(confirmed implementation defect; predecessor rows not rewritten).",
            "",
            "## Market reference",
            "",
        ]
    )
    lines.append(_render_market_block(market))
    lines.extend(["", "## Market-line implied score reference", ""])
    if implied_score.get("status") != "MARKET_LINE_IMPLIED_SCORE_REFERENCE":
        lines.append(
            f"**Withheld:** `{implied_score.get('status')}` "
            f"({implied_score.get('reason') or 'no compatible same-book/as-of spread+total'}). "
            "Not an independent BAS predicted score. Values were not clamped."
        )
    else:
        lines.append(
            f"Home {implied_score.get('home_points')} / away {implied_score.get('away_points')} "
            "as `MARKET_LINE_IMPLIED_SCORE_REFERENCE` only. "
            "Not an independent BAS score, calibrated distribution, or betting recommendation."
        )
    lines.extend(
        [
            "",
            "## Other named models",
            "",
        ]
    )
    if not other_models:
        lines.append(
            "**Other models:** `ABSENT`. No independently sourced, timestamped, "
            "identity-matched external-model capture is attached. "
            "Equal percentages do not make a numberFire quote into ESPN FPI."
        )
    else:
        for model in other_models:
            lines.append(f"- {json.dumps(model, sort_keys=True)}")
    lines.extend(
        [
            "",
            "## Coaching context (CONTEXT_ONLY / NOT_CONSUMED_BY_MODEL)",
            "",
            f"- National domain `coaching_staff`: `{coaching.get('national_domain') or 'SOURCE_ABSENT'}`.",
            f"- Structured acquisition-registry coach entry: `{coaching.get('registry_coach_entry_present')}`.",
            f"- Texas A&M staff fetch: `{_summarize_fetches(coaching.get('home_fetch'))}`.",
            f"- Missouri State staff fetch: `{_summarize_fetches(coaching.get('away_fetch'))}`.",
            "- HC/OC/DC titles, when observed on an official page, remain titles. "
            "Play-caller roles are `UNKNOWN` unless contemporaneous non-title evidence exists.",
            "- Coaching does not affect any displayed BAS number.",
            "",
            "## Other unused/missing domains",
            "",
        ]
    )
    for row in consumption:
        lines.append(f"- `{row['domain']}`: **{row['label']}** — {row['note']}")
    lines.extend(
        [
            "",
            "## Disagreement diagnosis",
            "",
            f"**Classes:** {', '.join(disagreement.get('classes') or [])}.",
            "",
            disagreement.get("narrative") or "",
            "",
            "Linear contributions are model arithmetic, not causal explanations. "
            "An 18-point market gap is not a verified residual unless a captured "
            "same-event quote exists; captured quotes are not automatically a "
            "compatible spread+total pair. Exploratory matchup slices stay `EXPLORATORY`.",
            "",
            "## Independent predicted score",
            "",
            f"`independent_predicted_score = {score_readiness.get('independent_predicted_score')}`",
            "",
            f"**Blocker:** {score_readiness.get('independent_predicted_score_blocker')}",
            "",
            "No actual-score column. Week 1 outcomes are not training data.",
            "",
            "## What a reader may and may not infer",
            "",
            "- May read the shadow probabilities and supported ridge margin as issued, with trust `UNTRUSTED_SHADOW`.",
            "- May not treat the control as a pick.",
            (
                "- May not treat this T-90M evidence packet as FORECAST_FROZEN."
                if label == T90M_EVIDENCE_LABEL
                else (
                    "- May not treat this T-24H evidence packet as FORECAST_FROZEN or as a T-90M freeze."
                    if label == T24H_EVIDENCE_LABEL
                    else "- May not treat this report as T-24H or T-90M."
                )
            ),
            "- May not treat coaching titles as model inputs or play-caller proof.",
            "- May not treat a line-implied score, if later eligible, as a BAS final-score prediction.",
            "- May not conclude calibration, BAS, or persistent underperformance from one game.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _summarize_fetches(value: Any) -> str:
    if value in (None, "", "NOT_ATTACHED"):
        return "NOT_ATTACHED"
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return str(value)
    parts: list[str] = []
    for row in value:
        if not isinstance(row, Mapping):
            continue
        identity = row.get("page_identity") or ""
        identity_bit = f" identity={identity}" if identity else ""
        parts.append(
            f"{row.get('fetch_disposition')} HTTP {row.get('http_status')} "
            f"{row.get('url')} final={row.get('final_url')} "
            f"sha256={row.get('sha256')} retrieved_at={row.get('retrieved_at_utc')}"
            f"{identity_bit}"
            + (f" error={row.get('error')}" if row.get("error") else "")
        )
    return "; ".join(parts) if parts else "NONE"


def _render_market_block(market: Mapping[str, Any]) -> str:
    status = market.get("status") or "ABSENT"
    label = market.get("label") or "INSUFFICIENT_MARKET_COVERAGE"
    quote_count = market.get("quote_count") or 0
    consensus = (
        market.get("consensus") if isinstance(market.get("consensus"), Mapping) else {}
    )
    median = consensus.get("median_home_margin")
    return (
        f"**Market:** `{status}` (`{label}`). Captured quote count: {quote_count}. "
        f"Consensus median home margin: {median if median is not None else 'null'}. "
        "User quotations and browser observations are not receipts. "
        "A captured quote count is not a valid two-sided same-book spread+total pair."
    )


def _focus_feature_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    selected = {}
    for row in rows:
        if str(row.get("ncaa_contest_id")) != FOCUS_CONTEST_ID:
            continue
        selected[str(row.get("site_orientation"))] = dict(row)
    if "HOME" not in selected or "AWAY" not in selected:
        raise PregameReportingError(
            "frozen feature payload missing both 6607349 orientations"
        )
    return selected


def _load_c26_focus(data_root: Path, gate: Mapping[str, Any]) -> list[dict[str, Any]]:
    relative = gate["payloads"]["focus_packet"]["relative_path"]
    return load_jsonl(data_root / relative)


def _load_c24_focus(data_root: Path, gate: Mapping[str, Any]) -> dict[str, Any]:
    manifest = load_json(data_root / gate["manifest"]["relative_path"])
    rows = load_jsonl(
        data_root
        / payload_relative_path(manifest, "week1_2026_early_focus_contest_packet.jsonl")
    )
    if not rows:
        raise PregameReportingError("missing C24 focus packet")
    return rows[0]


def _c24_ridge(packet: Mapping[str, Any]) -> dict[str, Any]:
    for row in packet.get("candidate_rows") or []:
        if row.get("candidate_id") == RIDGE_CANDIDATE:
            return dict(row)
    raise PregameReportingError("C24 focus packet missing ridge candidate")


def _c26_ridge(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("candidate_id") == RIDGE_CANDIDATE:
            return dict(row)
    raise PregameReportingError("C26 focus packet missing ridge candidate")


def build_focus_disagreement_diagnostic(
    *,
    issued_at_utc: str,
    c24_gate: Mapping[str, Any],
    c26_gate: Mapping[str, Any],
    c24_packet: Mapping[str, Any],
    c26_rows: Sequence[Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    parameter_rows: Sequence[Mapping[str, Any]],
    market_consensus: Mapping[str, Any] | None,
    market_quote_count: int,
    weather_admitted: bool,
    coaching_consumed: bool,
    coaching_context_label: str = "ABSENT",
    code_head: str | None = None,
) -> dict[str, Any]:
    c24_ridge = _c24_ridge(c24_packet)
    c26_ridge = _c26_ridge(c26_rows)
    if str(c26_ridge.get("ncaa_contest_id")) != FOCUS_CONTEST_ID:
        raise PregameReportingError("focus diagnostic is not contest 6607349")
    design_row = next(
        row
        for row in parameter_rows
        if row.get("parameter_set_id") == "WEEK1_2026_DEPLOYMENT_DESIGN"
    )
    ridge_params = next(
        row for row in parameter_rows if row.get("candidate_id") == RIDGE_CANDIDATE
    )
    features = _focus_feature_rows(feature_rows)
    home_values = dict(features["HOME"]["feature_values"])
    away_values = dict(features["AWAY"]["feature_values"])
    raw_home = float(c26_ridge["raw_margin_home"])
    raw_away = float(c26_ridge["raw_margin_away"])
    emitted_home = float(c26_ridge["expected_margin_home"])
    home_decomp = reconstruct_ridge_row(
        home_values,
        transforms=design_row["transforms"],
        levels=design_row["conference_levels"],
        indicators=design_row["indicators"],
        coefficients=ridge_params["coefficients"],
        reconstructed_margin=raw_home,
    )
    away_decomp = reconstruct_ridge_row(
        away_values,
        transforms=design_row["transforms"],
        levels=design_row["conference_levels"],
        indicators=design_row["indicators"],
        coefficients=ridge_params["coefficients"],
        reconstructed_margin=raw_away,
    )
    symmetrized = (raw_home - raw_away) / 2.0
    if abs(symmetrized - emitted_home) > CONTRIBUTION_TOLERANCE:
        raise ContributionSumError(
            f"symmetrized raw margins {symmetrized} != emitted {emitted_home}"
        )
    admitted = {
        "HOME": list(features["HOME"].get("admitted_feature_names") or []),
        "AWAY": list(features["AWAY"].get("admitted_feature_names") or []),
    }
    consumption = input_consumption_table(
        feature_values_by_orientation={"HOME": home_values, "AWAY": away_values},
        admitted_names_by_orientation=admitted,
        weather_admitted=weather_admitted,
        market_quotes_for_contest=market_quote_count,
        coaching_consumed=coaching_consumed,
        coaching_context_label=coaching_context_label,
    )
    staff_poll = classify_feature_as_staff_evidence("coaches_poll_rank")
    classes = classify_disagreement(
        [
            "CONFIRMED_IMPLEMENTATION_DEFECT",
            "INPUT_LIMITATION",
            "MODEL_SPECIFICATION_LIMITATION",
            "UNEXPLAINED_DISAGREEMENT",
        ]
    )
    exploratory = classify_subgroup_analysis(
        motivated_by_observed_disagreement=True,
        labeled_as="EXPLORATORY",
    )
    market_gap = None
    if (
        market_quote_count
        and market_consensus
        and market_consensus.get("median_home_margin") is not None
    ):
        market_gap = emitted_home - float(market_consensus["median_home_margin"])
    diagnostic = {
        "artifact_type": "FOCUS_FORECAST_DISAGREEMENT_DIAGNOSTIC",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": "CYCLE27_FOCUS_FORECAST_DISAGREEMENT_DIAGNOSTIC",
        "jira_key": JIRA_KEY,
        "issued_at_utc": issued_at_utc,
        "code_head": code_head,
        "ncaa_contest_id": FOCUS_CONTEST_ID,
        "home_team": {
            "label": FOCUS_HOME_LABEL,
            "canonical_team_id": FOCUS_HOME_CANONICAL,
            "source_team_id": features["HOME"].get("source_team_id"),
            "subdivision_current": "FBS",
            "conference_current": home_values.get("team_conference"),
        },
        "away_team": {
            "label": FOCUS_AWAY_LABEL,
            "canonical_team_id": FOCUS_AWAY_CANONICAL,
            "source_team_id": features["AWAY"].get("source_team_id"),
            "subdivision_current": "FBS",
            "conference_current": away_values.get("team_conference"),
            "note": "Current 2026 subdivision is taken from current contest/spine authority, not copied from an old season as if it were current.",
        },
        "payload": {
            "c26_gate_identity": c26_gate.get("gate_identity"),
            "c26_dataset_identity": c26_gate.get("dataset_identity"),
            "c24_gate_identity": c24_gate.get("gate_identity")
            or c24_gate.get("binding_identity"),
            "source": "frozen focus packets, not report prose",
        },
        "lineage": checkpoint_lineage(
            c24_ridge=c24_ridge,
            c26_ridge=c26_ridge,
            c24_gate_identity=str(
                c24_gate.get("gate_identity") or c24_gate.get("binding_identity")
            ),
            c26_gate_identity=str(c26_gate.get("gate_identity")),
            c26_dataset_identity=str(c26_gate.get("dataset_identity")),
            predecessor_rows_rewritten=False,
        ),
        "emitted": {
            "candidate_id": RIDGE_CANDIDATE,
            "probability_home": c26_ridge.get("probability_home"),
            "probability_away": c26_ridge.get("probability_away"),
            "expected_margin_home": emitted_home,
            "expected_margin_away": c26_ridge.get("expected_margin_away"),
            "raw_margin_home": raw_home,
            "raw_margin_away": raw_away,
            "margin_interval_home": c26_ridge.get("margin_interval_home"),
            "nominal_interval_level_emitted": c26_ridge.get("nominal_interval_level"),
            "declared_interval_probability": 0.8,
            "trust_classification": c26_ridge.get("trust_classification"),
            "adequacy_verdict": c26_ridge.get("adequacy_verdict"),
            "probability_link": c26_ridge.get("probability_link"),
        },
        "ridge_decomposition": {
            "home_raw": home_decomp,
            "away_raw": away_decomp,
            "symmetrized_emitted_margin_home": symmetrized,
            "contributions_are_not_causal": True,
            "tolerance": CONTRIBUTION_TOLERANCE,
        },
        "input_consumption": consumption,
        "coaches_poll_rank_classification": staff_poll,
        "market": {
            "captured_quote_count": market_quote_count,
            "consensus": market_consensus,
            "model_minus_market_margin_gap": market_gap,
            "user_quotes_are_not_receipts": True,
        },
        "diagnostic_classes": classes,
        "class_evidence": {
            "CONFIRMED_IMPLEMENTATION_DEFECT": [
                "C24 ridge P(home)=0.9999979105 used a saturated link; C26 corrected p without changing margin.",
                "C26 emits nominal_interval_level=0.95 while declared/reconstructed mass is 0.8.",
                "C26 reuses predecessor forecast_row_identity while changing probability/interval semantics.",
            ],
            "INPUT_LIMITATION": [
                "Prior win/margin/points rates are missing behind learned indicators for both teams.",
                "Venue coordinates/elevation/surface missing.",
                "Coaches Poll rank missing; AP rank present only for A&M.",
                "No coaching/recruiting/roster/weather/travel/market features consumed.",
                "Priors are stale allowed history (age_seasons=3), not a 2026 frozen current prior.",
            ],
            "MODEL_SPECIFICATION_LIMITATION": [
                "Largest ridge contributions on this row are missingness indicators, intercept, is_home, and prior game-count z-scores, not scheme/staff.",
                "Opening-season season_to_date_games=0; season win rate missingness is a large term.",
                "Missouri State 2026 FBS/CUSA current status is a current-contest field; historical analogue support for opening FBS seasons is not a confirmed skill claim.",
                "Symmetric Normal residual and pair symmetrization are specification choices.",
            ],
            "UNEXPLAINED_DISAGREEMENT": [
                "No captured same-event market quotes for 6607349, so an 18-point market gap is not a verified residual.",
                "Mathematical coherence of p/margin/interval does not establish useful skill.",
            ],
        },
        "exploratory_subgroups": exploratory,
        "independent_predicted_score": independent_scores_from_margin_only(
            emitted_home
        ),
        "scientific_nonclaims": [
            "Does not patch weights or missing values to match a market line.",
            "Does not treat a bookmaker handicap as an expected margin.",
            "Does not claim historical market-beating skill without archived quotes.",
            "Does not rewrite C24/C25/C26 predecessor rows.",
        ],
        "result": "PASS_FOCUS_DISAGREEMENT_DIAGNOSTIC",
    }
    diagnostic["gate_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in diagnostic.items() if key != "gate_identity"}
        )
    )
    return diagnostic


def _coaching_context_label(packets: Mapping[str, Mapping[str, Any]]) -> str:
    if not packets:
        return "ABSENT"
    retrieved = False
    blocked_only = True
    for packet in packets.values():
        fetches = packet.get("fetches") or []
        if not fetches:
            blocked_only = False
            continue
        if any(row.get("fetch_disposition") == "RETRIEVED" for row in fetches):
            retrieved = True
            blocked_only = False
        elif any(row.get("fetch_disposition") != "BLOCKED" for row in fetches):
            blocked_only = False
    if retrieved:
        return "CONTEXT_ONLY"
    if blocked_only:
        return "BLOCKED"
    return "ABSENT"


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    ops_root: Path,
    issued_at_utc: str | None = None,
    coaching_census: Mapping[str, Any] | None = None,
    staff_packets: Mapping[str, Mapping[str, Any]] | None = None,
    code_head: str | None = None,
) -> dict[str, Any]:
    issued = issued_at_utc or utc_now_label()
    packets = staff_packets or {}
    coaching_context_label = _coaching_context_label(packets)
    c24_gate = load_json(
        repo_root / "artifacts/forecast/week1_2026_early_forecast_adequacy_gate.json"
    )
    c26_gate = load_json(
        repo_root
        / "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
    )
    suite_gate = load_json(
        repo_root / "artifacts/forecast/week1_2026_national_forecast_suite_gate.json"
    )
    market_gate = load_json(
        repo_root
        / "artifacts/forecast/week1_2026_market_benchmark_and_adequacy_gate.json"
    )
    suite_manifest = load_json(data_root / suite_gate["manifest"]["relative_path"])
    feature_rows = load_jsonl(
        data_root
        / payload_relative_path(
            suite_manifest, "week1_2026_forecast_feature_rows.jsonl"
        )
    )
    parameter_rows = load_jsonl(
        data_root
        / payload_relative_path(
            suite_manifest, "week1_2026_forecast_fitted_parameter_rows.jsonl"
        )
    )
    c24_packet = _load_c24_focus(data_root, c24_gate)
    c26_rows = _load_c26_focus(data_root, c26_gate)
    market_dir = (
        data_root
        / "canonical/week1_2026_market_benchmark_and_adequacy/sha256"
        / str(market_gate["dataset_identity"])
    )
    consensus_rows = load_jsonl(market_dir / "week1_2026_early_market_consensus.jsonl")
    quote_rows = load_jsonl(market_dir / "week1_2026_early_market_quotes.jsonl")
    market_consensus = next(
        (
            row
            for row in consensus_rows
            if str(row.get("ncaa_contest_id")) == FOCUS_CONTEST_ID
        ),
        None,
    )
    market_quotes = captured_focus_quote_count(
        consensus=market_consensus,
        quote_rows=quote_rows,
        contest_id=FOCUS_CONTEST_ID,
    )
    market_quote_count = int(market_quotes["quote_count"])
    suite_contract = load_json(
        repo_root / "configs/week1_2026_national_forecast_suite_contract.json"
    )
    weather_admitted = bool(
        suite_contract.get("week1_feature_construction", {}).get(
            "weather_admitted_as_model_input"
        )
    )
    diagnostic = build_focus_disagreement_diagnostic(
        issued_at_utc=issued,
        c24_gate=c24_gate,
        c26_gate=c26_gate,
        c24_packet=c24_packet,
        c26_rows=c26_rows,
        feature_rows=feature_rows,
        parameter_rows=parameter_rows,
        market_consensus=market_consensus,
        market_quote_count=market_quote_count,
        weather_admitted=weather_admitted,
        coaching_consumed=False,
        coaching_context_label=coaching_context_label,
        code_head=code_head,
    )
    readiness = build_score_model_readiness(
        issued_at_utc=issued,
        week1_candidates=[
            "national_base_rate",
            "national_elo",
            "national_logistic_l2",
            "national_margin_ridge",
            "prior_only",
        ],
        ridge_emits_margin=True,
        joint_score_interface_present=True,
        poisson_runtime_present=True,
        elo_offense_defense_exposed_seasons=[2023, 2024, 2025],
        unprotected_baseline_target_seasons=[2023, 2024, 2025],
        eligible_week1_score_candidate=False,
        code_head=code_head,
    )
    implied = market_line_implied_score(
        total=None,
        home_spread=None,
        sportsbook=None,
        spread_book=None,
        total_book=None,
        spread_as_of_utc=None,
        total_as_of_utc=None,
        contest_identity=FOCUS_CONTEST_ID,
    )
    home_packet = packets.get(FOCUS_HOME_CANONICAL) or {}
    away_packet = packets.get(FOCUS_AWAY_CANONICAL) or {}
    coaching_summary = {
        "national_domain": "SOURCE_ABSENT",
        "registry_coach_entry_present": False,
        "home_fetch": home_packet.get("fetches") or "NOT_ATTACHED",
        "away_fetch": away_packet.get("fetches") or "NOT_ATTACHED",
        "model_consumption": NOT_CONSUMED_BY_MODEL,
        "census_classification": COACHING_CLASSIFICATION,
    }
    if coaching_census:
        coaching_summary["census_identity"] = coaching_census.get("gate_identity")
        coaching_summary["registry_coach_entry_present"] = (
            coaching_census.get("source_acquisition_registry") or {}
        ).get("coach_entry_present")
    report_md = render_pregame_report(
        issued_at_utc=issued,
        candidates=c26_rows,
        market={
            "status": market_quotes["status"],
            "label": market_quotes["label"],
            "quote_count": market_quote_count,
            "exact_contest_id_quote_rows": market_quotes["exact_contest_id_quote_rows"],
            "name_key_fuzzy_match_used": False,
            "consensus": market_consensus,
        },
        implied_score=implied,
        coaching=coaching_summary,
        disagreement={
            "classes": diagnostic["diagnostic_classes"],
            "narrative": (
                "C26 ridge emits P(home)=0.8951316669 and expected home margin "
                "+22.2506043541 from a Normal residual on ALL_ADMITTED_FEATURES. "
                "The largest arithmetic contributions are learned missingness, "
                "home indicator, intercept, and prior game-count z-scores. "
                "Coaching is not consumed. Captured market quotes for this contest: "
                f"{market_quote_count}."
            ),
        },
        score_readiness=readiness,
        consumption=diagnostic["input_consumption"],
        other_models=[],
        evidence_checkpoint=load_am_checkpoint_evidence_receipt(),
    )
    repo_dir = repo_root / "artifacts/scientific_integrity/cycle27"
    ops_dir = ops_root / "outputs"
    written = {
        "diagnostic": write_json_dual(
            diagnostic,
            repo_path=repo_dir / "FOCUS_FORECAST_DISAGREEMENT_DIAGNOSTIC.json",
            ops_path=ops_dir / "FOCUS_FORECAST_DISAGREEMENT_DIAGNOSTIC.json",
        ),
        "score_readiness": write_json_dual(
            readiness,
            repo_path=repo_dir / "SCORE_MODEL_READINESS.json",
            ops_path=ops_dir / "SCORE_MODEL_READINESS.json",
        ),
    }
    encoded = report_md.encode("utf-8")
    for path in (
        repo_dir / "PREGAME_RESEARCH_REPORT.md",
        ops_dir / "PREGAME_RESEARCH_REPORT.md",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encoded)
    written["report"] = {
        "repo_path": str(repo_dir / "PREGAME_RESEARCH_REPORT.md"),
        "ops_path": str(ops_dir / "PREGAME_RESEARCH_REPORT.md"),
        "sha256": sha256_bytes(encoded),
        "bytes": len(encoded),
        "label": (
            T90M_EVIDENCE_LABEL
            if T90M_EVIDENCE_LABEL in report_md
            else (
                T24H_EVIDENCE_LABEL
                if T24H_EVIDENCE_LABEL in report_md
                else INTERIM_LABEL
            )
        ),
    }
    return {
        "issued_at_utc": issued,
        "written": written,
        "diagnostic_identity": diagnostic["gate_identity"],
        "score_readiness_identity": readiness["gate_identity"],
    }
