"""Cycle #27 active-path dependency trace for the live Week 1 successor.

The map records fields actually read by the executable national forecast
successor and by the historical national-expectation baselines, not advertised
schema support. The current-contest binding helper is traced as unused by the
materializer: Cycle #24 rows are copied and probability/interval fields are
mutated.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

# Duplicated from national_expectation_baselines so this tracer stays numpy-free.
# Tests assert these tuples still appear in that module's source.
PRIOR_DOMAIN_NUMERIC = (
    "prior_games_played",
    "prior_win_rate",
    "prior_points_for_mean",
    "prior_points_against_mean",
    "prior_margin_mean",
    "prior_season_win_rate",
    "season_to_date_games",
    "season_to_date_win_rate",
    "opponent_prior_games_played",
    "opponent_prior_win_rate",
    "opponent_prior_margin_mean",
    "opponent_prior_season_win_rate",
    "prior_win_rate_differential",
)
PRIOR_DOMAIN_BOOLEAN = ("is_home", "is_neutral_site")
ALL_NUMERIC = PRIOR_DOMAIN_NUMERIC + (
    "ap_poll_rank",
    "coaches_poll_rank",
    "opponent_ap_poll_rank",
    "venue_elevation_m",
    "venue_latitude",
    "venue_longitude",
)
ALL_BOOLEAN = PRIOR_DOMAIN_BOOLEAN + (
    "rankings_source_available",
    "venue_dome",
    "venue_grass",
    "team_is_fbs",
)
FEATURE_SCOPES = {
    "NONE": ((), (), False),
    "PRIOR_OUTCOME_DOMAIN_AND_SITE": (PRIOR_DOMAIN_NUMERIC, PRIOR_DOMAIN_BOOLEAN, False),
    "OUTCOME_SEQUENCE_AND_SITE": ((), PRIOR_DOMAIN_BOOLEAN, False),
    "ALL_ADMITTED_FEATURES": (ALL_NUMERIC, ALL_BOOLEAN, True),
}

SCHEMA_VERSION = "aggie.data.cycle27_active_path_dependency_trace.v1"
CONTRACT_ID = "CYCLE27-ACTIVE-PATH-DEPENDENCY-TRACE-V1"
JIRA_KEY = "BAT-690"
LOCAL_ISSUE_ID = "POST-TASK-CYCLE27-ACTIVE-PATH-DEPENDENCY-TRACE-001"
PARENT_JIRA_KEY = "BAT-523"
ARTIFACT_TYPE = "CYCLE27_ACTIVE_PATH_DEPENDENCY_TRACE"
GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/CYCLE27_ACTIVE_PATH_DEPENDENCY_TRACE.json"
)
SUCCESSOR_RELATIVE = (
    "src/aggie_analytics/data/week1_2026_game_grain_national_forecast_successor.py"
)
BASELINES_RELATIVE = "src/aggie_analytics/modeling/national_expectation_baselines.py"
CURRENT_CONTEST_RELATIVE = (
    "src/aggie_analytics/data/week1_2026_current_contest_binding_successor.py"
)
C26_GATE_IDENTITY = "aa4ff84b16e9f00b1e68965cef7ea8730adc456ad16bda6ed1ff564b5bcdcb43"
C26_DATASET_IDENTITY = "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
CURRENT_CONTEST_HELPER = "build_current_contest_row"
ADVERTISED_UNUSED_OPENING_RATINGS = ("opening_rating", "opening_elo", "preseason_rating")
RIDGE_CONSUMED_ROW_FIELDS = (
    "expected_margin_home",
    "contest_identity",
    "home_canonical_team_id",
    "home_source_team_id",
    "away_canonical_team_id",
    "away_source_team_id",
    "forecast_row_identity",
    "checkpoint_id",
    "row_state",
    "candidate_id",
    "abstention_reasons",
)
PROBABILITY_ONLY_CONSUMED_ROW_FIELDS = (
    "candidate_id",
    "row_state",
    "raw_probability_home",
    "raw_probability_away",
    "probability_home",
    "probability_away",
)
ELO_CONSUMED_FIELDS = (
    "canonical_game_id",
    "canonical_team_id",
    "opponent_canonical_team_id",
    "season",
    "is_home",
    "is_neutral_site",
    "chronological_ordinal",
)
LABEL_CONSUMED_FIELDS = ("label_win", "label_tie", "label_margin")


class ActivePathTraceError(ValueError):
    """Raised when the active-path trace cannot be built honestly."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _string_constants(node: ast.AST) -> tuple[str, ...]:
    found: list[str] = []

    class Visitor(ast.NodeVisitor):
        def visit_Constant(self, constant: ast.Constant) -> None:
            if isinstance(constant.value, str):
                found.append(constant.value)

    Visitor().visit(node)
    return tuple(found)


def parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_module_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
            for alias in node.names:
                names.add(alias.name)
    return names


def called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def function_named(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def mapping_key_reads(fn: ast.FunctionDef, mapping_names: Iterable[str]) -> set[str]:
    """Return string keys read from named mappings via subscript or .get()."""

    names = set(mapping_names)
    keys: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id in names and isinstance(node.slice, ast.Constant):
                if isinstance(node.slice.value, str):
                    keys.add(node.slice.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in names
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                keys.add(node.args[0].value)
    return keys


def copies_entire_mapping(fn: ast.FunctionDef, mapping_names: Iterable[str]) -> bool:
    names = set(mapping_names)
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "dict"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in names
        ):
            return True
    return False


def current_contest_helper_consumed(successor_tree: ast.AST) -> bool:
    imported = imported_module_names(successor_tree)
    called = called_names(successor_tree)
    source_blob = " ".join(_string_constants(successor_tree))
    if CURRENT_CONTEST_HELPER in called:
        return True
    if "week1_2026_current_contest_binding_successor" in imported:
        return True
    if CURRENT_CONTEST_HELPER in source_blob:
        return True
    return False


def trace_forecast_successor(repo_root: Path) -> dict[str, Any]:
    path = repo_root / SUCCESSOR_RELATIVE
    if not path.is_file():
        raise ActivePathTraceError(f"missing successor module: {SUCCESSOR_RELATIVE}")
    tree = parse_module(path)
    ridge_fn = function_named(tree, "_rewrite_ridge_row")
    prob_fn = function_named(tree, "_rewrite_probability_only_row")
    materialize_fn = function_named(tree, "materialize")
    residual_fn = function_named(tree, "_residual_stdev")
    early_fn = function_named(tree, "_early_forecast_rows")
    if ridge_fn is None or prob_fn is None or materialize_fn is None:
        raise ActivePathTraceError("successor rewrite/materialize functions missing")
    ridge_keys = mapping_key_reads(ridge_fn, ("row",))
    prob_keys = mapping_key_reads(prob_fn, ("row",))
    residual_keys = mapping_key_reads(residual_fn, ("row", "suite_gate")) if residual_fn else set()
    helper_consumed = current_contest_helper_consumed(tree)
    copies_c24 = copies_entire_mapping(ridge_fn, ("row",)) and copies_entire_mapping(
        prob_fn, ("row",)
    )
    advertised_unused = [
        {
            "field": name,
            "status": "ADVERTISED_UNUSED",
            "evidence": "not read by week1 successor rewrite; Elo training uses initial_rating=1500",
        }
        for name in ADVERTISED_UNUSED_OPENING_RATINGS
    ]
    advertised_unused.append(
        {
            "field": CURRENT_CONTEST_HELPER,
            "status": "HELPER_PRESENT_NOT_CONSUMED_BY_MATERIALIZER",
            "evidence": (
                f"{CURRENT_CONTEST_RELATIVE} is imported/called only by tests, "
                "not by the Week 1 national materializer"
            ),
        }
    )
    return {
        "module": SUCCESSOR_RELATIVE,
        "loads_cycle24_early_forecast_rows": early_fn is not None,
        "copies_cycle24_row_then_mutates_probability_interval": copies_c24,
        "current_contest_binding_helper_consumed": helper_consumed,
        "current_contest_execution": (
            "C24_ROWS_MUTATED"
            if copies_c24 and not helper_consumed
            else "HELPER_CONSUMED"
        ),
        "rebuilds_target_features": False,
        "refits_parameters": False,
        "ridge_row_fields_actually_read": sorted(ridge_keys),
        "probability_only_row_fields_actually_read": sorted(prob_keys),
        "residual_stdev_keys_read": sorted(residual_keys),
        "executable_prediction_inputs": [
            "expected_margin_home from Cycle #24 predecessor row",
            "ridge_training_residual_stdev from suite parameter/deployment_fit",
            "interval_probability hardcoded 0.8",
        ],
        "feature_values_consumed_for_prediction": False,
        "advertised_unused": advertised_unused,
        "c26_gate_identity_preserved": C26_GATE_IDENTITY,
        "c26_dataset_identity_preserved": C26_DATASET_IDENTITY,
    }


def _scope_fields(scope: str) -> dict[str, Any]:
    numeric, boolean, use_conference = FEATURE_SCOPES[scope]
    consumed = list(numeric) + list(boolean)
    if use_conference:
        consumed.append("team_conference")
    missing = [f"{name}_missing" for name in list(numeric) + list(boolean)]
    return {
        "numeric": list(numeric),
        "boolean": list(boolean),
        "conference_indicators": bool(use_conference),
        "missingness_indicators_when_present": missing,
        "actually_consumed": consumed,
    }


def assert_baselines_source_matches(repo_root: Path) -> None:
    source = (repo_root / BASELINES_RELATIVE).read_text(encoding="utf-8")
    tracked = PRIOR_DOMAIN_NUMERIC + PRIOR_DOMAIN_BOOLEAN
    tracked += ALL_NUMERIC[len(PRIOR_DOMAIN_NUMERIC) :]
    tracked += ALL_BOOLEAN[len(PRIOR_DOMAIN_BOOLEAN) :] + ("team_conference",)
    for field in tracked:
        if f'"{field}"' not in source and f"'{field}'" not in source:
            raise ActivePathTraceError(f"baselines source no longer contains field {field}")
    if "initial_rating" not in source:
        raise ActivePathTraceError("Elo initial_rating no longer present in baselines source")
    if "opening_rating" in source:
        raise ActivePathTraceError("unexpected opening_rating consumption in baselines source")


def trace_national_expectation_baselines(*, repo_root: Path) -> dict[str, Any]:
    assert_baselines_source_matches(repo_root)
    candidates = {
        "national_base_rate": {
            "family": "UNFITTED_REFERENCE",
            "feature_scope": "NONE",
            "actually_consumed_fields": ["fold_training_label_win_rate"],
            "advertised_unused_in_this_candidate": list(ALL_NUMERIC + ALL_BOOLEAN)
            + ["opening_rating"],
        },
        "prior_only": {
            "family": "REGULARIZED_LOGISTIC",
            "feature_scope": "PRIOR_OUTCOME_DOMAIN_AND_SITE",
            **_scope_fields("PRIOR_OUTCOME_DOMAIN_AND_SITE"),
            "advertised_unused_in_this_candidate": [
                name
                for name in ALL_NUMERIC + ALL_BOOLEAN
                if name not in PRIOR_DOMAIN_NUMERIC + PRIOR_DOMAIN_BOOLEAN
            ]
            + ["opening_rating"],
        },
        "national_elo": {
            "family": "ELO",
            "feature_scope": "OUTCOME_SEQUENCE_AND_SITE",
            "actually_consumed_fields": list(ELO_CONSUMED_FIELDS) + list(LABEL_CONSUMED_FIELDS),
            "initial_rating": 1500.0,
            "opening_ratings_consumed": False,
            "advertised_unused_in_this_candidate": list(PRIOR_DOMAIN_NUMERIC)
            + ["opening_rating", "ap_poll_rank", "venue_elevation_m"],
        },
        "national_logistic_l2": {
            "family": "REGULARIZED_LOGISTIC",
            "feature_scope": "ALL_ADMITTED_FEATURES",
            **_scope_fields("ALL_ADMITTED_FEATURES"),
            "advertised_unused_in_this_candidate": ["opening_rating"],
        },
        "national_margin_ridge": {
            "family": "RIDGE_MARGIN",
            "feature_scope": "ALL_ADMITTED_FEATURES",
            **_scope_fields("ALL_ADMITTED_FEATURES"),
            "label_consumed": "label_margin",
            "residual_distribution": (
                "fold-local training residual stdev; logistic link_scale = "
                "stdev / logistic_link_scale_divisor"
            ),
            "week1_successor_uses_this_training_link": False,
            "advertised_unused_in_this_candidate": ["opening_rating"],
        },
    }
    return {
        "module": BASELINES_RELATIVE,
        "role": "HISTORICAL_DEVELOPMENT_FIT_NOT_WEEK1_MATERIALIZER",
        "consumed_by_week1_successor_materializer": False,
        "raw_normalized_outcomes": list(LABEL_CONSUMED_FIELDS),
        "partitions": [
            "chronological_ordinal training_max_ordinal_exclusive expanding folds",
            "EVALUATION 2023 development partition",
        ],
        "transforms": [
            "fold_local_transforms mean/stdev standardization of numeric features",
            "missing numeric values left at standardized zero (train mean) plus missingness indicators",
            "conference levels with min-training-row bucket OTHER_OR_MISSING",
        ],
        "new_cold_start_average_invented_for_coverage": False,
        "candidates": candidates,
    }


def build_trace(*, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    successor = trace_forecast_successor(repo_root)
    baselines = trace_national_expectation_baselines(repo_root=repo_root)
    if successor["current_contest_binding_helper_consumed"]:
        raise ActivePathTraceError(
            "trace would claim helper consumption; live successor does not call it"
        )
    stages = [
        {
            "stage": "raw_normalized_outcomes",
            "actually_consumed": list(LABEL_CONSUMED_FIELDS),
            "consumer": BASELINES_RELATIVE,
            "week1_successor_rereads_outcomes": False,
        },
        {
            "stage": "permitted_historical_features_and_labels",
            "actually_consumed": {
                "prior_only": list(PRIOR_DOMAIN_NUMERIC + PRIOR_DOMAIN_BOOLEAN),
                "national_elo": list(ELO_CONSUMED_FIELDS),
                "national_logistic_l2_and_ridge": list(ALL_NUMERIC + ALL_BOOLEAN)
                + ["team_conference"],
                "national_base_rate": ["fold training win labels only"],
            },
            "advertised_unused": ["opening_rating", "opening_elo", "preseason_rating"],
        },
        {
            "stage": "partitions",
            "actually_consumed": [
                "chronological_ordinal",
                "training_max_ordinal_exclusive",
                "evaluation_ordinals",
                "partition=EVALUATION",
            ],
        },
        {
            "stage": "transforms_parameters_residual_distribution",
            "actually_consumed": [
                "fold_local_transforms mean/stdev",
                "ridge fold residual stdev",
                "logistic_link_scale_divisor (training path only)",
                "Week1 residual_stdev from NATIONAL_MARGIN_RIDGE_BETA / deployment_fit",
            ],
            "week1_distribution": "NORMAL_RESIDUAL CDF and interval from residual_stdev",
            "training_ridge_link_differs_from_week1_normal_cdf": True,
        },
        {
            "stage": "current_target_features",
            "actually_consumed": [],
            "current_contest_binding_helper_consumed": False,
            "execution": successor["current_contest_execution"],
            "note": (
                "Week1 successor does not rebuild current-opponent/conference/"
                "subdivision/rank features. It copies Cycle #24 forecast rows."
            ),
        },
        {
            "stage": "executable_prediction",
            "actually_consumed": successor["executable_prediction_inputs"],
            "ridge_row_fields_actually_read": successor["ridge_row_fields_actually_read"],
            "probability_only_row_fields_actually_read": successor[
                "probability_only_row_fields_actually_read"
            ],
            "feature_values_consumed_for_prediction": False,
        },
        {
            "stage": "checkpoint_packet",
            "c26_gate_identity": C26_GATE_IDENTITY,
            "c26_dataset_identity": C26_DATASET_IDENTITY,
            "checkpoint_id": "EARLY_WEEK1",
            "overwritten_in_this_trace": False,
            "publication_label": "UNTRUSTED_SHADOW",
        },
    ]
    trace = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "publication_label": "UNTRUSTED_SHADOW",
        "scientific_trust_gate_open": False,
        "stages": stages,
        "forecast_successor": successor,
        "national_expectation_baselines": baselines,
        "current_contest_binding": {
            "helper_module": CURRENT_CONTEST_RELATIVE,
            "helper_symbol": CURRENT_CONTEST_HELPER,
            "consumed_by_week1_materializer": False,
            "live_execution": "CYCLE24_FORECAST_ROWS_COPIED_AND_MUTATED",
        },
        "c26_gate_identity_preserved": C26_GATE_IDENTITY,
        "c26_dataset_identity_preserved": C26_DATASET_IDENTITY,
        "scientific_nonclaims": [
            "Does not claim a connected current-feature fitted path.",
            "Does not advertise unused opening ratings as consumed.",
            "Does not invent a new cold-start average to improve coverage.",
            "Does not overwrite the Cycle #26 gate or dataset.",
        ],
        "result": "PASS_CYCLE27_ACTIVE_PATH_DEPENDENCY_TRACE",
    }
    trace["trace_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in trace.items() if key != "trace_identity"}
        )
    )
    return trace


def materialize(*, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    trace = build_trace(repo_root=repo_root, issued_at_utc=issued_at_utc)
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return trace
