from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

# 2023-only labeled development matrix and expanding-window walk-forward.
# Labels are post-completion observations. They are never pregame features.
# Metrics are development-only and grant no protected or promotion authority.

SCHEMA_VERSION = "aggie.experimentation.development_2023_labeled_replay.v3"
CHECKPOINT_SCHEMA = "aggie.experimentation.development_2023_labeled_checkpoint.v3"
CONTRACT_RELATIVE = "configs/development_2023_labeled_replay_contract.json"
GATE_RELATIVE = "artifacts/pit/development_walk_forward_2023.json"
CONTRACT_ID = "BAT-566-2023-LABELED-DEVELOPMENT-REPLAY-V3"
PASS_RESULT = "PASS_DEVELOPMENT_ONLY_2023_LABELED_REPLAY"
PROTECTED_SEASONS = frozenset({2024, 2025})
DEVELOPMENT_SEASON = 2023
SUPERSEDED_KICKOFF_LABEL_IDENTITY = "902f3558a466a3cc26def6f24285032c2d012c0adeaf5bf5a2cfb47101a99cb2"
SUPERSEDED_MATRIX_IDENTITY = "84e5aede6ab5e57fbd88185f587ead5b6d0be97265da5d495a417f689bbcbc8a"
SUPERSEDED_REPLAY_IDENTITY = "584fefb812e36c08c54af5f66df1c49b3cc0ab51b6b45200b88b3b4855b35fd7"
SUPERSEDED_CYCLE6_LABEL_IDENTITY = "bdcacebeaccd3ba69e2445420664749b961f5a3a233a3d66b355e291fa9c6bb8"
SUPERSEDED_CYCLE6_MATRIX_IDENTITY = "04e058375e11e0c53e040e8874f9bb84ca548b551fe7b54552fa7d9b4199ef68"
SUPERSEDED_CYCLE6_REPLAY_IDENTITY = "09995c8baab98842fde54a006a8ac97ca132c79415158bcc405c98984aea70e2"
AUTHORITATIVE_PRIOR_ONLY_BRIER = 0.23135006789663434
AUTHORITATIVE_PRIOR_ONLY_ROWS = 1820
PAIR_COMPLEMENT_TOLERANCE = 1e-12
NON_AUTHORITATIVE_METADATA = frozenset({"issued_at_utc", "producer"})
FORBIDDEN_FEATURE_FIELDS = frozenset(
    {
        "result",
        "points_for",
        "points_against",
        "margin",
        "home_points",
        "away_points",
        "outcome_result",
        "win",
        "loss",
        "tie",
        "label",
        "y_win",
    }
)
PRIOR_FEATURE_FIELDS = (
    "prior_games",
    "prior_win_rate",
    "prior_points_for_mean",
    "prior_points_against_mean",
    "missingness",
)
PLAY_DRIVE_FEATURE_FIELDS = (
    "play_count",
    "play_game_count",
    "play_season_count",
    "epa_mean",
    "stat_yardage_mean",
    "rush_rate",
    "pass_rate",
    "scoring_play_rate",
    "interception_rate",
    "sack_rate",
    "pass_completion_rate",
    "drive_count",
    "drive_game_count",
    "drive_plays_mean",
    "touchdown_drive_rate",
    "field_goal_drive_rate",
    "turnover_drive_rate",
    "cold_start",
)
FEATURE_ROW_FIELDS = (
    "row_id",
    "target_game_id",
    "team_id",
    "opponent_id",
    "site",
    "season",
    "season_type",
    "week",
    "cutoff_utc",
    "target_start_utc",
    "prior_lineage_sha256",
    *PRIOR_FEATURE_FIELDS,
    *PLAY_DRIVE_FEATURE_FIELDS,
    "play_drive_source_known_at_utc",
    "play_drive_source_effective_at_utc_max",
    "play_drive_historical_known_at_eligible",
    "play_drive_protected_eligible",
    "feature_domains",
    "row_lineage_sha256",
)
LABEL_ROW_FIELDS = (
    "row_id",
    "target_game_id",
    "team_id",
    "season",
    "result",
    "points_for",
    "points_against",
    "margin",
    "label_available_after_utc",
    "not_a_pregame_feature",
    "development_label_only",
    "row_lineage_sha256",
)
AUTHORITY_GATE_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "matrix_identity",
    "replay_identity",
    "run_identity",
    "code_identity",
    "manifest",
    "input_identities",
    "population",
    "pairing",
    "folds",
    "metrics",
    "incremental_play_drive_result",
    "proofs",
    "payloads",
    "authority",
    "label_semantics",
    "scientific_nonclaims",
    "issue_completion",
    "supersession",
    "protected_period_exclusions",
)


class ProtectedOutcomeDenied(RuntimeError):
    """Raised when 2024/2025 outcomes are requested or appear in development code."""


class LabelUnavailable(RuntimeError):
    """Raised when a label is requested before completion or from the feature surface."""


class CheckpointRejected(RuntimeError):
    """Raised when a checkpoint is stale, mismatched, or future-fitted."""


def _polars() -> Any:
    try:
        import polars
    except ImportError as exc:
        raise RuntimeError(
            "2023 labeled development replay requires the optional data-engineering environment"
        ) from exc
    return polars


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dataframe_record_sha256(frame: Any) -> str:
    digest = hashlib.sha256()
    for row in frame.iter_rows(named=True):
        digest.update(canonical_json_bytes(row) + b"\n")
    return digest.hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed.astimezone(timezone.utc)


def clip_probability(value: float) -> float:
    return min(max(float(value), 1e-9), 1.0 - 1e-9)


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = repo_root / CONTRACT_RELATIVE
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected 2023 labeled-replay contract identity")
    pinned = contract["input_identities"]["bat565_label_dataset_identity"]
    if pinned == SUPERSEDED_KICKOFF_LABEL_IDENTITY:
        raise ValueError("active BAT-566 contract still pins superseded kickoff-time BAT-565 identity")
    semantics = contract.get("label_semantics") or {}
    if "available_only_after_completion" in semantics:
        raise ValueError("available_only_after_completion claims observed completion and is forbidden")
    if semantics.get("label_eligibility_basis") != "PRECOMMITTED_RETROSPECTIVE_POLICY_BOUND":
        raise ValueError("label eligibility basis is not the precommitted retrospective policy")
    if semantics.get("historical_label_availability_proven") is not False:
        raise ValueError("contract must not claim proven historical label availability")
    authority = contract["authority"]
    if authority.get("development_2023_labeled_evaluation") is not True:
        raise ValueError("2023 labeled evaluation authority is not explicitly enabled")
    for key in (
        "pregame_feature_use_of_labels",
        "same_game_feature_join",
        "protected_training_admission",
        "protected_evaluation_admission",
        "champion_or_production_promotion",
        "protected_performance_claims",
        "forecast_publication",
        "tamu_specialization_lift_claims",
        "bas_or_aggie_excess_claims",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"2023 labeled-replay authority is open: {key}")
    return contract


def verify_protected_registry(repo_root: Path, contract: Mapping[str, Any]) -> str:
    from aggie_analytics.validation.protected import classify_season
    from aggie_analytics.validation.protected_split_authority import (
        assert_labels_cannot_override_protected_membership,
        sha256_file as registry_sha,
    )

    source = contract["input_identities"]
    path = repo_root / source["protected_split_registry_relative_path"]
    digest = registry_sha(path)
    if digest != source["protected_split_registry_sha256"]:
        raise ValueError("protected split registry identity drift")
    for season in (2024, 2025):
        if classify_season(season) != "PROTECTED_TEST":
            raise ValueError("protected-season classifier drift")
        assert_labels_cannot_override_protected_membership(
            repo_root, season, "DEVELOPMENT_ONLY"
        )
    if classify_season(2023) != "DEVELOPMENT_SELECTION":
        raise ValueError("2023 development-selection classifier drift")
    return digest


def _require_file(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing pinned payload: {path}")
    if sha256_file(path) != expected_sha256:
        raise ValueError(f"payload SHA-256 drift: {path}")


def assert_no_protected_outcomes(rows: Sequence[Mapping[str, Any]], *, context: str) -> None:
    seasons = {int(row["season"]) for row in rows if row.get("season") is not None}
    if seasons & PROTECTED_SEASONS:
        raise ProtectedOutcomeDenied(f"protected 2024/2025 outcome entered {context}")
    if seasons and seasons != {DEVELOPMENT_SEASON}:
        raise ValueError(f"{context} season drift: {sorted(seasons)}")


def assert_feature_surface(rows: Sequence[Mapping[str, Any]]) -> None:
    leaked = sorted(FORBIDDEN_FEATURE_FIELDS.intersection(rows[0] if rows else {}))
    if leaked:
        raise ValueError(f"feature surface contains outcome columns: {leaked}")
    for row in rows:
        extra = FORBIDDEN_FEATURE_FIELDS.intersection(row)
        if extra:
            raise ValueError(f"feature row leaked outcome columns: {sorted(extra)}")
        if int(row["season"]) in PROTECTED_SEASONS:
            raise ProtectedOutcomeDenied("protected-season row entered the feature surface")


def complementary_results(left: str, right: str) -> bool:
    if left == "TIE" and right == "TIE":
        return True
    return {left, right} == {"WIN", "LOSS"}


def canonical_game_orientation(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    if len(rows) != 2:
        raise ValueError("canonical orientation requires exactly two opposing team rows")
    homes = [row for row in rows if str(row.get("site", "")).upper() == "HOME"]
    if len(homes) == 1:
        return homes[0]
    return sorted(rows, key=lambda item: (str(item["team_id"]), str(item["row_id"])))[0]


def assert_unique_game_pairing(
    feature_rows: Sequence[Mapping[str, Any]],
    label_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    labels_by_row = {str(row["row_id"]): row for row in label_rows}
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in feature_rows:
        grouped.setdefault(str(row["target_game_id"]), []).append(row)
    for game_id, rows in grouped.items():
        if len(rows) != 2:
            raise ValueError(f"game {game_id} does not have exactly two opposing team rows")
        left, right = rows
        if str(left["team_id"]) == str(right["team_id"]):
            raise ValueError(f"game {game_id} has duplicate team identity")
        if str(left["opponent_id"]) != str(right["team_id"]) or str(right["opponent_id"]) != str(left["team_id"]):
            raise ValueError(f"game {game_id} opponent pairing is not complementary")
        left_label = labels_by_row[str(left["row_id"])]
        right_label = labels_by_row[str(right["row_id"])]
        if not complementary_results(str(left_label["result"]), str(right_label["result"])):
            raise ValueError(f"game {game_id} team/opponent labels are not complementary")
        if int(left_label["points_for"]) != int(right_label["points_against"]) or int(
            left_label["points_against"]
        ) != int(right_label["points_for"]):
            raise ValueError(f"game {game_id} paired scores are not complementary")
        canonical_game_orientation(rows)
    return {
        "unique_games": len(grouped),
        "team_rows": len(feature_rows),
        "required_rows_per_game": 2,
        "orientation": "HOME_THEN_TEAM_ID",
        "complementary_labels": True,
        "game_counted_once_in_game_metrics": True,
    }


class PairProbabilityDenied(ValueError):
    """Raised when raw pair probabilities cannot be normalized fail-closed."""


def normalize_pair_probabilities(p_a_raw: float, p_b_raw: float) -> dict[str, float]:
    try:
        p_a = float(p_a_raw)
        p_b = float(p_b_raw)
    except (TypeError, ValueError) as exc:
        raise PairProbabilityDenied("raw pair probability is not numeric") from exc
    if not math.isfinite(p_a) or not math.isfinite(p_b):
        raise PairProbabilityDenied("raw pair probability is NaN or infinite")
    if p_a < 0.0 or p_b < 0.0:
        raise PairProbabilityDenied("raw pair probability is negative")
    if p_a == 0.0 or p_b == 0.0:
        raise PairProbabilityDenied("raw pair probability is zero")
    raw_sum = p_a + p_b
    if raw_sum == 0.0:
        raise PairProbabilityDenied("raw pair probability sum is zero")
    p_a_game = p_a / raw_sum
    p_b_game = 1.0 - p_a_game
    complement_error = abs((p_a_game + p_b_game) - 1.0)
    if complement_error > PAIR_COMPLEMENT_TOLERANCE:
        raise PairProbabilityDenied("normalized pair is not complementary")
    return {
        "p_a_game": p_a_game,
        "p_b_game": p_b_game,
        "raw_sum": raw_sum,
        "complement_error": complement_error,
    }


def unique_game_eval_rows(
    eval_rows: Sequence[Mapping[str, Any]],
    probability_fn: Callable[[Mapping[str, Any]], float] | None = None,
) -> list[Mapping[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in eval_rows:
        grouped.setdefault(str(row["target_game_id"]), []).append(row)
    selected: list[Mapping[str, Any]] = []
    for game_id, rows in grouped.items():
        if len(rows) != 2:
            raise ValueError(f"evaluation game {game_id} is not a unique complementary pair")
        if probability_fn is None:
            selected.append(canonical_game_orientation(rows))
            continue
        left, right = rows[0], rows[1]
        p_left = float(probability_fn(left))
        p_right = float(probability_fn(right))
        norm = normalize_pair_probabilities(p_left, p_right)
        enriched = [
            {**dict(left), "p_raw": p_left, "p_game": norm["p_a_game"], "pair_normalization": norm},
            {**dict(right), "p_raw": p_right, "p_game": norm["p_b_game"], "pair_normalization": norm},
        ]
        selected.append(canonical_game_orientation(enriched))
    selected.sort(key=lambda item: (str(item.get("cutoff_utc", "")), str(item["row_id"])))
    return selected


def pair_probability_diagnostics(
    eval_rows: Sequence[Mapping[str, Any]],
    probability_fn: Callable[[Mapping[str, Any]], float],
) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in eval_rows:
        grouped.setdefault(str(row["target_game_id"]), []).append(row)
    raw_sums: list[float] = []
    complement_errors: list[float] = []
    selected_ids: list[str] = []
    for game_id, rows in grouped.items():
        if len(rows) != 2:
            raise ValueError(f"evaluation game {game_id} is not a unique complementary pair")
        p_a = float(probability_fn(rows[0]))
        p_b = float(probability_fn(rows[1]))
        raw_sums.append(p_a + p_b)
        norm = normalize_pair_probabilities(p_a, p_b)
        complement_errors.append(abs(float(norm["complement_error"])))
        selected = canonical_game_orientation(
            [
                {**dict(rows[0]), "p_game": norm["p_a_game"]},
                {**dict(rows[1]), "p_game": norm["p_b_game"]},
            ]
        )
        selected_ids.append(str(selected["row_id"]))
    return {
        "raw_pair_count": len(raw_sums),
        "raw_pair_sum_min": None if not raw_sums else min(raw_sums),
        "raw_pair_sum_max": None if not raw_sums else max(raw_sums),
        "raw_pair_sum_mean": None if not raw_sums else sum(raw_sums) / float(len(raw_sums)),
        "mean_abs_deviation_from_1": None
        if not raw_sums
        else sum(abs(value - 1.0) for value in raw_sums) / float(len(raw_sums)),
        "normalized_pair_count": len(complement_errors),
        "max_normalized_complement_error": None if not complement_errors else max(complement_errors),
        "canonical_orientation_identity": stable_hash(
            {"rule": "HOME_THEN_TEAM_ID", "selected_row_ids": selected_ids}
        ),
        "orientation": "HOME_THEN_TEAM_ID",
    }


def load_verified_inputs(data_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    pl = _polars()
    source = contract["input_identities"]
    prior_manifest_path = data_root / source["bat523_prior_manifest_relative_path"]
    pd_manifest_path = data_root / source["play_drive_manifest_relative_path"]
    label_manifest_path = data_root / source["bat565_label_manifest_relative_path"]
    prior_manifest = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
    pd_manifest = json.loads(pd_manifest_path.read_text(encoding="utf-8"))
    label_manifest = json.loads(label_manifest_path.read_text(encoding="utf-8"))
    if prior_manifest.get("dataset_identity") != source["bat523_prior_dataset_identity"]:
        raise ValueError("BAT-523 prior identity drift")
    if pd_manifest.get("dataset_identity") != source["play_drive_dataset_identity"]:
        raise ValueError("play/drive identity drift")
    if label_manifest.get("dataset_identity") != source["bat565_label_dataset_identity"]:
        raise ValueError("BAT-565 label identity drift")
    if source["bat565_label_dataset_identity"] == SUPERSEDED_KICKOFF_LABEL_IDENTITY:
        raise ValueError("active BAT-566 artifact consumes superseded kickoff-time label identity")
    if label_manifest.get("dataset_identity") == SUPERSEDED_KICKOFF_LABEL_IDENTITY:
        raise ValueError("active BAT-566 manifest still binds the superseded kickoff-time label identity")
    prior_listed = next(
        item for item in prior_manifest["payloads"] if item["name"] == "pregame_prior_rows.parquet"
    )
    pd_listed = next(
        item
        for item in pd_manifest["payloads"]
        if str(item.get("role")) == "DEVELOPMENT_ONLY_TARGET_GAME_TEAM_FEATURES"
        or str(item.get("path", "")).endswith("target_game_team_play_drive_features.parquet")
    )
    label_listed = next(
        item
        for item in label_manifest["payloads"]
        if item["name"] == "team_outcome_observations.parquet"
    )
    prior_path = data_root / "features" / "historical_known_at" / "sha256" / source[
        "bat523_prior_dataset_identity"
    ] / "pregame_prior_rows.parquet"
    pd_path = data_root / "features" / "historical_known_at" / "sha256" / source[
        "play_drive_dataset_identity"
    ] / "target_game_team_play_drive_features.parquet"
    label_path = data_root / "pit_state" / "development_outcomes" / "sha256" / source[
        "bat565_label_dataset_identity"
    ] / "team_outcome_observations.parquet"
    _require_file(prior_path, source["bat523_pregame_prior_rows_sha256"])
    _require_file(pd_path, source["play_drive_feature_sha256"])
    _require_file(label_path, source["bat565_team_outcome_sha256"])
    if sha256_file(prior_path) != prior_listed["sha256"]:
        raise ValueError("BAT-523 prior listed hash drift")
    if sha256_file(pd_path) != pd_listed["sha256"]:
        raise ValueError("play/drive listed hash drift")
    if sha256_file(label_path) != label_listed["sha256"]:
        raise ValueError("BAT-565 listed hash drift")
    priors = pl.read_parquet(prior_path)
    play_drive = pl.read_parquet(pd_path)
    labels = pl.read_parquet(label_path)
    if priors.height != int(source["bat523_pregame_prior_rows"]):
        raise ValueError("BAT-523 prior row-count drift")
    if play_drive.height != int(source["play_drive_feature_rows"]):
        raise ValueError("play/drive row-count drift")
    if labels.height != int(source["bat565_team_outcome_rows"]):
        raise ValueError("BAT-565 label row-count drift")
    return {
        "priors": priors,
        "play_drive": play_drive,
        "labels": labels,
        "prior_manifest": prior_manifest,
        "play_drive_manifest": pd_manifest,
        "label_manifest": label_manifest,
    }


def build_matrix(inputs: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    pl = _polars()
    priors = inputs["priors"].filter(pl.col("season") == DEVELOPMENT_SEASON)
    play_drive = inputs["play_drive"].filter(pl.col("season") == DEVELOPMENT_SEASON)
    labels = inputs["labels"]
    if priors.height == 0 or play_drive.height == 0 or labels.height == 0:
        raise ValueError("2023 matrix source population is empty")
    assert_no_protected_outcomes(priors.to_dicts(), context="2023 priors")
    assert_no_protected_outcomes(play_drive.to_dicts(), context="2023 play/drive features")
    assert_no_protected_outcomes(labels.to_dicts(), context="2023 labels")
    if play_drive.filter(pl.col("protected_eligible") == True).height:  # noqa: E712
        raise ValueError("play/drive rows unexpectedly claim protected eligibility")
    joined = priors.join(
        play_drive,
        left_on=["target_game_id", "team_id"],
        right_on=["game_id", "team_id"],
        how="inner",
        suffix="_pd",
    )
    anti_pd = priors.join(
        play_drive, left_on=["target_game_id", "team_id"], right_on=["game_id", "team_id"], how="anti"
    )
    labeled = joined.join(
        labels,
        left_on=["target_game_id", "team_id"],
        right_on=["canonical_game_id", "team_id"],
        how="inner",
        suffix="_lb",
    )
    anti_lb = joined.join(
        labels,
        left_on=["target_game_id", "team_id"],
        right_on=["canonical_game_id", "team_id"],
        how="anti",
    )
    acceptance = contract["acceptance"]
    if anti_pd.height or anti_lb.height:
        raise ValueError(
            f"join is not one-to-one: play/drive anti={anti_pd.height} label anti={anti_lb.height}"
        )
    if labeled.height != int(acceptance["expected_feature_rows"]):
        raise ValueError(f"joined row-count drift: {labeled.height}")
    if not (labeled["opponent_id"] == labeled["opponent_team_id"]).all():
        raise ValueError("paired team orientation drifted between priors and play/drive")
    opponent_label = labeled["opponent_id_lb"] if "opponent_id_lb" in labeled.columns else labeled["opponent_id"]
    if not (labeled["opponent_id"] == opponent_label).all():
        raise ValueError("paired team orientation drifted between features and labels")
    cutoff_right = labeled["cutoff_utc_pd"] if "cutoff_utc_pd" in labeled.columns else labeled["cutoff_utc"]
    if not (labeled["cutoff_utc"] == cutoff_right).all():
        raise ValueError("prior/play-drive cutoff identity drifted")
    late_known = labeled.filter(
        pl.col("source_known_at_utc").is_not_null()
        & (pl.col("source_known_at_utc") > pl.col("cutoff_utc"))
    )
    late_effective = labeled.filter(
        pl.col("source_effective_at_utc_max").is_not_null()
        & (pl.col("source_effective_at_utc_max") > pl.col("cutoff_utc"))
    )
    if late_known.height or late_effective.height:
        raise ValueError("play/drive evidence is after target cutoff")
    per_game = labeled.group_by("target_game_id").len()
    if per_game["len"].min() != 2 or per_game["len"].max() != 2:
        raise ValueError("target-game/team cardinality is not exactly two rows per game")
    feature_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    for raw in labeled.to_dicts():
        feature = {
            "row_id": raw["row_id"],
            "target_game_id": raw["target_game_id"],
            "team_id": raw["team_id"],
            "opponent_id": raw["opponent_id"],
            "site": raw["site"],
            "season": int(raw["season"]),
            "season_type": raw["season_type"],
            "week": int(raw["week"]),
            "cutoff_utc": raw["cutoff_utc"],
            "target_start_utc": raw["target_start_utc"],
            "prior_lineage_sha256": raw["lineage_sha256"],
            "prior_games": raw["prior_games"],
            "prior_win_rate": raw["prior_win_rate"],
            "prior_points_for_mean": raw["prior_points_for_mean"],
            "prior_points_against_mean": raw["prior_points_against_mean"],
            "missingness": raw["missingness"],
            "cold_start": bool(raw["cold_start"]),
            "play_drive_source_known_at_utc": raw.get("source_known_at_utc"),
            "play_drive_source_effective_at_utc_max": raw.get("source_effective_at_utc_max"),
            "play_drive_historical_known_at_eligible": raw.get("historical_known_at_eligible"),
            "play_drive_protected_eligible": bool(raw.get("protected_eligible") or False),
            "feature_domains": ["bat523_pregame_priors", "historical_play_drive_2010_2022"],
        }
        for name in PLAY_DRIVE_FEATURE_FIELDS:
            if name == "cold_start":
                continue
            feature[name] = raw.get(name)
        feature["row_lineage_sha256"] = stable_hash(
            {key: value for key, value in feature.items() if key != "row_lineage_sha256"}
        )
        label = {
            "row_id": raw["row_id"],
            "target_game_id": raw["target_game_id"],
            "team_id": raw["team_id"],
            "season": int(raw["season_lb"] if raw.get("season_lb") is not None else raw["season"]),
            "result": raw["result"],
            "points_for": raw["points_for"],
            "points_against": raw["points_against"],
            "margin": raw["margin"],
            "label_available_after_utc": raw["label_available_after_utc"],
            "not_a_pregame_feature": True,
            "development_label_only": True,
        }
        label["row_lineage_sha256"] = stable_hash(
            {key: value for key, value in label.items() if key != "row_lineage_sha256"}
        )
        if int(label["season"]) in PROTECTED_SEASONS:
            raise ProtectedOutcomeDenied("protected-year label entered the 2023 matrix")
        if parse_utc(str(label["label_available_after_utc"])) <= parse_utc(str(feature["cutoff_utc"])):
            raise ValueError("label availability is not strictly after the pregame cutoff")
        if parse_utc(str(label["label_available_after_utc"])) <= parse_utc(str(feature["target_start_utc"])):
            raise ValueError("label availability is not strictly after kickoff")
        feature_rows.append(feature)
        label_rows.append(label)
    feature_rows.sort(key=lambda item: (item["cutoff_utc"], item["row_id"]))
    label_by_id = {row["row_id"]: row for row in label_rows}
    label_rows = [label_by_id[row["row_id"]] for row in feature_rows]
    assert_feature_surface(feature_rows)
    assert_no_protected_outcomes(feature_rows, context="matrix features")
    assert_no_protected_outcomes(label_rows, context="matrix labels")
    pairing = assert_unique_game_pairing(feature_rows, label_rows)
    population = {
        "feature_rows": len(feature_rows),
        "label_rows": len(label_rows),
        "games": pairing["unique_games"],
        "unique_games": pairing["unique_games"],
        "team_rows": pairing["team_rows"],
        "cold_start_rows": sum(1 for row in feature_rows if row["cold_start"]),
        "protected_eligible_rows": sum(1 for row in feature_rows if row["play_drive_protected_eligible"]),
        "join_anti_rows": 0,
        "seasons": [DEVELOPMENT_SEASON],
        "season_types": dict(sorted(Counter(row["season_type"] for row in feature_rows).items())),
        "results": dict(sorted(Counter(row["result"] for row in label_rows).items())),
        "feature_domains": ["bat523_pregame_priors", "historical_play_drive_2010_2022"],
        "label_domain": "bat565_2023_development_outcomes",
        "pairing": pairing,
    }
    for key, expected in (
        ("feature_rows", "expected_feature_rows"),
        ("label_rows", "expected_label_rows"),
        ("games", "expected_games"),
        ("cold_start_rows", "expected_cold_start_rows"),
        ("protected_eligible_rows", "expected_protected_eligible_rows"),
        ("join_anti_rows", "expected_join_anti_rows"),
    ):
        if int(population[key]) != int(acceptance[expected]):
            raise ValueError(f"population drift: {key}={population[key]} expected={acceptance[expected]}")
    return {"feature_rows": feature_rows, "label_rows": label_rows, "population": population}


def build_folds(feature_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in feature_rows:
        key = (str(row["season_type"]), int(row["week"]))
        grouped.setdefault(key, []).append(dict(row))
    folds: list[dict[str, Any]] = []
    for (season_type, week), rows in grouped.items():
        rows.sort(key=lambda item: (str(item["cutoff_utc"]), str(item["row_id"])))
        cutoffs = [parse_utc(str(item["cutoff_utc"])) for item in rows]
        folds.append(
            {
                "fold_id": f"2023-{season_type}-W{week:02d}",
                "season": DEVELOPMENT_SEASON,
                "season_type": season_type,
                "week": week,
                "min_cutoff_utc": min(cutoffs).isoformat().replace("+00:00", "Z"),
                "max_cutoff_utc": max(cutoffs).isoformat().replace("+00:00", "Z"),
                "fold_evaluation_cutoff_utc": min(cutoffs).isoformat().replace("+00:00", "Z"),
                "rows": rows,
            }
        )
    folds.sort(key=lambda item: (item["min_cutoff_utc"], item["fold_id"]))
    for index, fold in enumerate(folds):
        fold["fold_index"] = index
        if index and fold["min_cutoff_utc"] < folds[index - 1]["min_cutoff_utc"]:
            raise ValueError("folds are not chronological")
    return folds


def derive_membership_proof(
    train_membership: Sequence[Mapping[str, Any]],
    eval_membership: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    train_games = {str(row["target_game_id"]) for row in train_membership}
    eval_games = {str(row["target_game_id"]) for row in eval_membership}
    train_ids = {str(row["row_id"]) for row in train_membership}
    eval_ids = {str(row["row_id"]) for row in eval_membership}
    return {
        "train_game_ids": sorted(train_games),
        "eval_game_ids": sorted(eval_games),
        "game_id_intersection": sorted(train_games & eval_games),
        "row_id_intersection": sorted(train_ids & eval_ids),
        "same_game_excluded": not (train_games & eval_games) and not (train_ids & eval_ids),
        "train_membership_sha256": stable_hash(list(train_membership)),
        "eval_membership_sha256": stable_hash(list(eval_membership)),
    }


def fold_membership(
    fold: Mapping[str, Any],
    feature_rows: Sequence[Mapping[str, Any]],
    label_by_row: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    eval_rows = list(fold["rows"])
    eval_game_ids = {str(row["target_game_id"]) for row in eval_rows}
    eval_row_ids = {str(row["row_id"]) for row in eval_rows}
    cutoff = parse_utc(str(fold.get("fold_evaluation_cutoff_utc") or fold["min_cutoff_utc"]))
    train_rows: list[Mapping[str, Any]] = []
    excluded_candidates: list[dict[str, Any]] = []
    availability_exclusions: list[dict[str, Any]] = []
    for row in feature_rows:
        row_id = str(row["row_id"])
        game_id = str(row["target_game_id"])
        label = label_by_row[row_id]
        reasons: list[str] = []
        if parse_utc(str(label["label_available_after_utc"])) >= cutoff:
            reasons.append("LABEL_NOT_AVAILABLE_BEFORE_CUTOFF")
        if game_id in eval_game_ids:
            reasons.append("SAME_GAME_EXCLUDED")
        if row_id in eval_row_ids:
            reasons.append("SAME_ROW_EXCLUDED")
        if reasons:
            record = {
                "row_id": row_id,
                "target_game_id": game_id,
                "label_available_after_utc": label["label_available_after_utc"],
                "reasons": reasons,
            }
            if "LABEL_NOT_AVAILABLE_BEFORE_CUTOFF" in reasons:
                availability_exclusions.append(record)
            else:
                excluded_candidates.append(record)
            continue
        train_rows.append(row)
    train_rows.sort(key=lambda item: (str(item["cutoff_utc"]), str(item["row_id"])))
    excluded_candidates.sort(key=lambda item: (item["label_available_after_utc"], item["row_id"]))
    availability_exclusions.sort(key=lambda item: (item["label_available_after_utc"], item["row_id"]))
    train_membership = [
        {"row_id": str(row["row_id"]), "target_game_id": str(row["target_game_id"])} for row in train_rows
    ]
    eval_membership = [
        {"row_id": str(row["row_id"]), "target_game_id": str(row["target_game_id"])} for row in eval_rows
    ]
    proof = derive_membership_proof(train_membership, eval_membership)
    proof["excluded_candidates"] = excluded_candidates
    proof["availability_exclusions"] = availability_exclusions
    proof["same_game_excluded"] = (
        not proof["game_id_intersection"]
        and not proof["row_id_intersection"]
        and all(
            "SAME_GAME_EXCLUDED" in item["reasons"] or "SAME_ROW_EXCLUDED" in item["reasons"]
            for item in excluded_candidates
        )
    )
    return {
        "train_rows": train_rows,
        "eval_rows": eval_rows,
        "train_membership": train_membership,
        "eval_membership": eval_membership,
        **proof,
    }


def prior_only_probability(row: Mapping[str, Any]) -> float:
    raw = row.get("prior_win_rate")
    if raw is None:
        return 0.5
    return clip_probability(float(raw))


def prior_only_margin(row: Mapping[str, Any]) -> float | None:
    points_for = row.get("prior_points_for_mean")
    points_against = row.get("prior_points_against_mean")
    if points_for is None or points_against is None:
        return None
    return float(points_for) - float(points_against)


def fit_prior_plus(train_rows: Sequence[Mapping[str, Any]], label_by_row: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if not train_rows:
        return {
            "kind": "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN",
            "beta_epa": 0.0,
            "epa_mean": 0.0,
            "train_row_ids": [],
        }
    residuals: list[float] = []
    epas: list[float] = []
    for row in train_rows:
        label = label_by_row[str(row["row_id"])]
        y = 1.0 if label["result"] == "WIN" else 0.0
        residuals.append(y - prior_only_probability(row))
        epas.append(0.0 if row.get("epa_mean") is None else float(row["epa_mean"]))
    epa_mean = sum(epas) / float(len(epas))
    centered = [value - epa_mean for value in epas]
    variance = sum(value * value for value in centered)
    if variance == 0.0:
        beta = 0.0
    else:
        beta = sum(residual * value for residual, value in zip(residuals, centered, strict=True)) / variance
    return {
        "kind": "FOLD_LOCAL_LINEAR_PROBABILITY_ON_EPA_MEAN_RESIDUAL",
        "beta_epa": float(beta),
        "epa_mean": float(epa_mean),
        "train_row_ids": [str(row["row_id"]) for row in train_rows],
    }


def prior_plus_probability(row: Mapping[str, Any], model: Mapping[str, Any]) -> float:
    epa = 0.0 if row.get("epa_mean") is None else float(row["epa_mean"])
    return clip_probability(
        prior_only_probability(row) + float(model["beta_epa"]) * (epa - float(model["epa_mean"]))
    )


def classification_metrics(
    labels: Sequence[float],
    probabilities: Sequence[float],
    margins_true: Sequence[float | None],
    margins_pred: Sequence[float | None],
) -> dict[str, Any]:
    if not labels:
        return {
            "rows": 0,
            "accuracy": None,
            "brier": None,
            "log_loss": None,
            "margin_mae": None,
            "calibration": {"omitted": True, "reason": "NO_EVALUATED_ROWS"},
        }
    wins = 0
    brier = 0.0
    log_loss = 0.0
    margin_errors: list[float] = []
    for y, p, y_m, p_m in zip(labels, probabilities, margins_true, margins_pred, strict=True):
        wins += int((p >= 0.5) == (y >= 0.5))
        brier += (p - y) ** 2
        log_loss += -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))
        if y_m is not None and p_m is not None:
            margin_errors.append(abs(float(y_m) - float(p_m)))
    n = float(len(labels))
    calibration: dict[str, Any]
    if len(labels) < 50:
        calibration = {"omitted": True, "reason": "INSUFFICIENT_SAMPLE_SUPPORT"}
    else:
        bins = []
        edges = [index / 10.0 for index in range(11)]
        adequate = True
        for index in range(10):
            selected = [
                (y, p)
                for y, p in zip(labels, probabilities, strict=True)
                if (p >= edges[index] and (p <= edges[index + 1] if index == 9 else p < edges[index + 1]))
            ]
            if selected and len(selected) < 5:
                adequate = False
            bins.append(
                {
                    "bin": index,
                    "count": len(selected),
                    "mean_p": None
                    if not selected
                    else sum(p for _, p in selected) / float(len(selected)),
                    "mean_y": None
                    if not selected
                    else sum(y for y, _ in selected) / float(len(selected)),
                }
            )
        calibration = (
            {"omitted": True, "reason": "BIN_SUPPORT_BELOW_5"}
            if not adequate
            else {"omitted": False, "bins": bins}
        )
    return {
        "rows": len(labels),
        "accuracy": wins / n,
        "brier": brier / n,
        "log_loss": log_loss / n,
        "margin_mae": None if not margin_errors else sum(margin_errors) / float(len(margin_errors)),
        "calibration": calibration,
    }


def execute_fold(
    fold: Mapping[str, Any],
    feature_rows: Sequence[Mapping[str, Any]],
    label_by_row: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    membership = fold_membership(fold, feature_rows, label_by_row)
    train_rows = membership["train_rows"]
    eval_rows = membership["eval_rows"]
    if any(int(row["season"]) in PROTECTED_SEASONS for row in [*train_rows, *eval_rows]):
        raise ProtectedOutcomeDenied("protected season entered fold membership")
    for row in eval_rows:
        label = label_by_row[str(row["row_id"])]
        if parse_utc(str(label["label_available_after_utc"])) <= parse_utc(str(row["cutoff_utc"])):
            raise LabelUnavailable("evaluation label is not strictly after the pregame cutoff")
        if parse_utc(str(label["label_available_after_utc"])) <= parse_utc(str(row["target_start_utc"])):
            raise LabelUnavailable("evaluation label is not strictly after kickoff")
    prior_plus = fit_prior_plus(train_rows, label_by_row)
    first_fold = int(fold["fold_index"]) == 0
    if first_fold and train_rows:
        raise ValueError("first fold unexpectedly received 2023 training labels")
    prior_labels: list[float] = []
    prior_probs: list[float] = []
    plus_labels: list[float] = []
    plus_probs: list[float] = []
    prior_true_m: list[float | None] = []
    prior_pred_m: list[float | None] = []
    plus_true_m: list[float | None] = []
    plus_pred_m: list[float | None] = []
    for row in eval_rows:
        label = label_by_row[str(row["row_id"])]
        y = 1.0 if label["result"] == "WIN" else 0.0
        y_m = None if label.get("margin") is None else float(label["margin"])
        prior_labels.append(y)
        prior_probs.append(prior_only_probability(row))
        prior_true_m.append(y_m)
        prior_pred_m.append(prior_only_margin(row))
        if prior_plus["kind"] != "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN":
            plus_labels.append(y)
            plus_probs.append(prior_plus_probability(row, prior_plus))
            plus_true_m.append(y_m)
            plus_pred_m.append(prior_only_margin(row))
    game_eval_rows = unique_game_eval_rows(eval_rows, prior_only_probability)
    plus_fn = None if prior_plus["kind"] == "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN" else (
        lambda row, model=prior_plus: prior_plus_probability(row, model)
    )
    game_plus_eval_rows = (
        [] if plus_fn is None else unique_game_eval_rows(eval_rows, plus_fn)
    )
    game_prior_labels: list[float] = []
    game_prior_probs: list[float] = []
    game_plus_labels: list[float] = []
    game_plus_probs: list[float] = []
    game_prior_true_m: list[float | None] = []
    game_prior_pred_m: list[float | None] = []
    game_plus_true_m: list[float | None] = []
    game_plus_pred_m: list[float | None] = []
    for row in game_eval_rows:
        label = label_by_row[str(row["row_id"])]
        y = 1.0 if label["result"] == "WIN" else 0.0
        y_m = None if label.get("margin") is None else float(label["margin"])
        game_prior_labels.append(y)
        game_prior_probs.append(float(row["p_game"]))
        game_prior_true_m.append(y_m)
        game_prior_pred_m.append(prior_only_margin(row))
    for row in game_plus_eval_rows:
        label = label_by_row[str(row["row_id"])]
        y = 1.0 if label["result"] == "WIN" else 0.0
        y_m = None if label.get("margin") is None else float(label["margin"])
        game_plus_labels.append(y)
        game_plus_probs.append(float(row["p_game"]))
        game_plus_true_m.append(y_m)
        game_plus_pred_m.append(prior_only_margin(row))
    prior_pair = pair_probability_diagnostics(eval_rows, prior_only_probability)
    plus_pair = (
        None
        if plus_fn is None
        else pair_probability_diagnostics(eval_rows, plus_fn)
    )
    result = {
        "fold_id": fold["fold_id"],
        "fold_index": fold["fold_index"],
        "season": DEVELOPMENT_SEASON,
        "season_type": fold["season_type"],
        "week": fold["week"],
        "min_cutoff_utc": fold["min_cutoff_utc"],
        "max_cutoff_utc": fold["max_cutoff_utc"],
        "fold_evaluation_cutoff_utc": fold.get("fold_evaluation_cutoff_utc") or fold["min_cutoff_utc"],
        "eval_row_count": len(eval_rows),
        "eval_unique_games": len(game_eval_rows),
        "train_row_count": len(train_rows),
        "train_unique_games": len({str(row["target_game_id"]) for row in train_rows}),
        "train_row_ids": [str(row["row_id"]) for row in train_rows],
        "eval_row_ids": [str(row["row_id"]) for row in eval_rows],
        "train_game_ids": list(membership["train_game_ids"]),
        "eval_game_ids": list(membership["eval_game_ids"]),
        "membership": {
            "train": membership["train_membership"],
            "eval": membership["eval_membership"],
            "game_id_intersection": membership["game_id_intersection"],
            "row_id_intersection": membership["row_id_intersection"],
            "excluded_candidates": membership["excluded_candidates"],
            "train_membership_sha256": membership["train_membership_sha256"],
            "eval_membership_sha256": membership["eval_membership_sha256"],
        },
        "same_game_excluded": bool(membership["same_game_excluded"]),
        "first_fold_no_fit": first_fold,
        "prior_plus_model": {
            "kind": prior_plus["kind"],
            "beta_epa": prior_plus["beta_epa"],
            "epa_mean": prior_plus["epa_mean"],
            "identity": stable_hash(prior_plus),
        },
        "prior_only": {
            **classification_metrics(prior_labels, prior_probs, prior_true_m, prior_pred_m),
            "perspective": "CORRELATED_TEAM_ROW",
            "authoritative_for_decisions": True,
        },
        "prior_plus_play_drive": {
            **(
                classification_metrics(plus_labels, plus_probs, plus_true_m, plus_pred_m)
                if plus_labels
                else {
                    "rows": 0,
                    "accuracy": None,
                    "brier": None,
                    "log_loss": None,
                    "margin_mae": None,
                    "calibration": {"omitted": True, "reason": "ABSTAIN_NO_FIT"},
                    "abstained": True,
                }
            ),
            "perspective": "CORRELATED_TEAM_ROW",
            "authoritative_for_decisions": True,
        },
        "unique_game_prior_only": {
            **classification_metrics(
                game_prior_labels, game_prior_probs, game_prior_true_m, game_prior_pred_m
            ),
            **prior_pair,
            "perspective": "COHERENT_UNIQUE_GAME",
            "authoritative_for_decisions": False,
        },
        "unique_game_prior_plus_play_drive": {
            **(
                classification_metrics(
                    game_plus_labels, game_plus_probs, game_plus_true_m, game_plus_pred_m
                )
                if game_plus_labels
                else {
                    "rows": 0,
                    "accuracy": None,
                    "brier": None,
                    "log_loss": None,
                    "margin_mae": None,
                    "calibration": {"omitted": True, "reason": "ABSTAIN_NO_FIT"},
                    "abstained": True,
                }
            ),
            **(plus_pair or {}),
            "perspective": "COHERENT_UNIQUE_GAME",
            "authoritative_for_decisions": False,
        },
        "paired_probability": prior_pair,
    }
    result["fold_result_hash"] = stable_hash(
        {key: value for key, value in result.items() if key != "fold_result_hash"}
    )
    return result


def summarize_metrics(fold_results: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    labels_n = 0
    weighted = {"accuracy": 0.0, "brier": 0.0, "log_loss": 0.0}
    margin_n = 0
    margin_sum = 0.0
    abstained = 0
    evaluated_folds = 0
    for fold in fold_results:
        block = fold[key]
        rows = int(block.get("rows") or 0)
        if rows == 0 or block.get("abstained"):
            abstained += 1
            continue
        evaluated_folds += 1
        labels_n += rows
        for metric in weighted:
            weighted[metric] += float(block[metric]) * rows
        if block.get("margin_mae") is not None:
            margin_n += rows
            margin_sum += float(block["margin_mae"]) * rows
    if labels_n == 0:
        return {
            "evaluated_rows": 0,
            "evaluated_folds": 0,
            "abstained_folds": abstained,
            "accuracy": None,
            "brier": None,
            "log_loss": None,
            "margin_mae": None,
        }
    return {
        "evaluated_rows": labels_n,
        "evaluated_folds": evaluated_folds,
        "abstained_folds": abstained,
        "accuracy": weighted["accuracy"] / labels_n,
        "brier": weighted["brier"] / labels_n,
        "log_loss": weighted["log_loss"] / labels_n,
        "margin_mae": None if margin_n == 0 else margin_sum / margin_n,
    }


def checkpoint_dir(data_root: Path, run_identity: str) -> Path:
    return data_root / "checkpoints" / "development_2023_labeled_replay" / run_identity


def write_checkpoint(directory: Path, payload: Mapping[str, Any]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"fold_{int(payload['fold_index']):02d}.json"
    path.write_bytes(canonical_json_bytes(payload))
    return path


def validate_checkpoint(
    checkpoint: Mapping[str, Any],
    *,
    run_identity: str,
    matrix_identity: str,
    code_identity: str,
    fold: Mapping[str, Any],
) -> None:
    if checkpoint.get("schema_version") != CHECKPOINT_SCHEMA:
        raise CheckpointRejected("schema-incompatible checkpoint")
    if checkpoint.get("run_identity") != run_identity:
        raise CheckpointRejected("identity-mismatched checkpoint run")
    if checkpoint.get("matrix_identity") != matrix_identity:
        raise CheckpointRejected("identity-mismatched checkpoint matrix")
    if checkpoint.get("code_identity") != code_identity:
        raise CheckpointRejected("stale checkpoint code identity")
    if checkpoint.get("fold_id") != fold["fold_id"]:
        raise CheckpointRejected("checkpoint fold identity mismatch")
    if parse_utc(str(checkpoint.get("train_cutoff_utc"))) > parse_utc(str(fold["min_cutoff_utc"])):
        raise CheckpointRejected("future-fitted checkpoint")


def run_walk_forward(
    *,
    folds: Sequence[Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    label_by_row: Mapping[str, Mapping[str, Any]],
    data_root: Path,
    run_identity: str,
    matrix_identity: str,
    code_identity: str,
    resume: bool = True,
    stop_after: int | None = None,
) -> list[dict[str, Any]]:
    directory = checkpoint_dir(data_root, run_identity)
    directory.mkdir(parents=True, exist_ok=True)
    completed: list[dict[str, Any]] = []
    for fold in folds:
        if stop_after is not None and int(fold["fold_index"]) >= stop_after:
            break
        path = directory / f"fold_{int(fold['fold_index']):02d}.json"
        if resume and path.is_file():
            checkpoint = json.loads(path.read_text(encoding="utf-8"))
            validate_checkpoint(
                checkpoint,
                run_identity=run_identity,
                matrix_identity=matrix_identity,
                code_identity=code_identity,
                fold=fold,
            )
            completed.append(checkpoint["fold_result"])
            continue
        fold_result = execute_fold(fold, feature_rows, label_by_row)
        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA,
            "run_identity": run_identity,
            "matrix_identity": matrix_identity,
            "code_identity": code_identity,
            "fold_id": fold["fold_id"],
            "fold_index": fold["fold_index"],
            "train_cutoff_utc": fold["min_cutoff_utc"],
            "fold_result": fold_result,
        }
        write_checkpoint(directory, checkpoint)
        completed.append(fold_result)
    return completed


def prove_future_append_invariance(
    folds: Sequence[Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    label_by_row: Mapping[str, Mapping[str, Any]],
    baseline: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    appended = list(feature_rows)
    last = folds[-1]
    synthetic = {
        **last["rows"][0],
        "row_id": "synthetic-future-append-row",
        "target_game_id": "synthetic-future-game",
        "cutoff_utc": "2099-12-31T00:00:00Z",
        "week": 99,
    }
    appended.append(synthetic)
    labels = dict(label_by_row)
    labels[synthetic["row_id"]] = {
        "row_id": synthetic["row_id"],
        "target_game_id": synthetic["target_game_id"],
        "team_id": synthetic["team_id"],
        "season": 2023,
        "result": "WIN",
        "points_for": 1,
        "points_against": 0,
        "margin": 1,
        "label_available_after_utc": "2099-12-31T12:00:00Z",
        "not_a_pregame_feature": True,
        "development_label_only": True,
    }
    mutated = [execute_fold(fold, appended, labels) for fold in folds]
    unchanged = [
        before["fold_id"]
        for before, after in zip(baseline, mutated, strict=True)
        if before["fold_result_hash"] == after["fold_result_hash"]
    ]
    return {
        "mutation": "append synthetic 2099 row",
        "pass": unchanged == [fold["fold_id"] for fold in folds],
        "unchanged_fold_ids": unchanged,
    }


def prove_postgame_append_invariance(
    folds: Sequence[Mapping[str, Any]],
    feature_rows: Sequence[Mapping[str, Any]],
    label_by_row: Mapping[str, Mapping[str, Any]],
    baseline: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(folds) < 2:
        return {"mutation": "flip last-fold label", "pass": True, "unchanged_fold_ids": []}
    victim = folds[-1]["rows"][0]
    mutated_labels = dict(label_by_row)
    current = mutated_labels[str(victim["row_id"])]
    mutated_labels[str(victim["row_id"])] = {
        **current,
        "result": "WIN" if current["result"] != "WIN" else "LOSS",
    }
    earlier = [fold for fold in folds if int(fold["fold_index"]) < int(folds[-1]["fold_index"])]
    mutated = [execute_fold(fold, feature_rows, mutated_labels) for fold in earlier]
    unchanged = [
        before["fold_id"]
        for before, after in zip(baseline[:-1], mutated, strict=True)
        if before["fold_result_hash"] == after["fold_result_hash"]
    ]
    return {
        "mutation": "flip a later-fold postgame label after earlier folds evaluated",
        "unchanged_fold_ids": unchanged,
        "pass": unchanged == [fold["fold_id"] for fold in earlier],
    }


def prove_same_game_exclusion(
    fold: Mapping[str, Any],
    feature_rows: Sequence[Mapping[str, Any]],
    label_by_row: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    membership = fold_membership(fold, feature_rows, label_by_row)
    return {
        "fold_id": fold["fold_id"],
        "game_id_intersection": membership["game_id_intersection"],
        "row_id_intersection": membership["row_id_intersection"],
        "same_game_excluded": membership["same_game_excluded"],
        "pass": membership["same_game_excluded"] is True,
    }


def prove_protected_outcome_denial(repo_root: Path) -> dict[str, Any]:
    from aggie_analytics.validation.protected_split_authority import (
        assert_labels_cannot_override_protected_membership,
    )

    denied = []
    for season in (2024, 2025):
        role = assert_labels_cannot_override_protected_membership(
            repo_root, season, "DEVELOPMENT_EVALUATION_UNPROTECTED"
        )
        denied.append({"season": season, "registry_role": role})
    return {"denied": denied, "pass": all(item["registry_role"] == "PROTECTED_TEST" for item in denied)}


def prove_stale_checkpoint_rejection(
    fold: Mapping[str, Any],
    *,
    run_identity: str,
    matrix_identity: str,
    code_identity: str,
) -> dict[str, Any]:
    stale = {
        "schema_version": CHECKPOINT_SCHEMA,
        "run_identity": run_identity,
        "matrix_identity": matrix_identity,
        "code_identity": "0" * 64,
        "fold_id": fold["fold_id"],
        "fold_index": fold["fold_index"],
        "train_cutoff_utc": fold["min_cutoff_utc"],
        "fold_result": {},
    }
    try:
        validate_checkpoint(
            stale,
            run_identity=run_identity,
            matrix_identity=matrix_identity,
            code_identity=code_identity,
            fold=fold,
        )
    except CheckpointRejected:
        return {"pass": True, "reason": "stale code identity rejected"}
    return {"pass": False, "reason": "stale checkpoint was accepted"}


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".tmp-{os.getpid()}-{hashlib.sha256(payload).hexdigest()[:8]}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _frame(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> Any:
    return _polars().DataFrame([{key: row[key] for key in fields} for row in rows], infer_schema_length=None)


def identity_core(
    *,
    contract_sha256: str,
    input_identities: Mapping[str, Any],
    record_hashes: Mapping[str, str],
    population: Mapping[str, Any],
    fold_hashes: Sequence[str],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "classification": "DEVELOPMENT_ONLY_2023_LABELED_WALK_FORWARD",
        "contract_sha256": contract_sha256,
        "input_identities": {
            key: input_identities[key]
            for key in (
                "bat523_prior_dataset_identity",
                "bat523_pregame_prior_rows_sha256",
                "play_drive_dataset_identity",
                "play_drive_feature_sha256",
                "bat565_label_dataset_identity",
                "bat565_team_outcome_sha256",
                "protected_split_registry_sha256",
            )
        },
        "record_hashes": dict(record_hashes),
        "population": {
            key: population[key]
            for key in (
                "feature_rows",
                "label_rows",
                "games",
                "unique_games",
                "team_rows",
                "cold_start_rows",
                "seasons",
            )
        },
        "pairing": population.get("pairing"),
        "fold_hashes": list(fold_hashes),
        "metrics": metrics,
    }


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    verify_protected_registry(repo_root, contract)
    inputs = load_verified_inputs(data_root, contract)
    matrix = build_matrix(inputs, contract)
    folds = build_folds(matrix["feature_rows"])
    label_by_row = {row["row_id"]: row for row in matrix["label_rows"]}
    feature_frame = _frame(matrix["feature_rows"], FEATURE_ROW_FIELDS)
    label_frame = _frame(matrix["label_rows"], LABEL_ROW_FIELDS)
    record_hashes = {
        "features": dataframe_record_sha256(feature_frame),
        "labels": dataframe_record_sha256(label_frame),
    }
    contract_sha256 = sha256_file(repo_root / CONTRACT_RELATIVE)
    matrix_identity = stable_hash(
        {
            "contract_sha256": contract_sha256,
            "record_hashes": record_hashes,
            "population": matrix["population"],
            "input_identities": contract["input_identities"],
        }
    )
    return {
        "contract": contract,
        "matrix": matrix,
        "folds": folds,
        "label_by_row": label_by_row,
        "feature_frame": feature_frame,
        "label_frame": label_frame,
        "record_hashes": record_hashes,
        "contract_sha256": contract_sha256,
        "matrix_identity": matrix_identity,
        "code_identity": sha256_file(Path(__file__).resolve()),
    }


def materialize(
    *,
    data_root: Path,
    repo_root: Path,
    issued_at_utc: str,
    output_data_root: Path | None = None,
) -> dict[str, Any]:
    output_root = (output_data_root or data_root).resolve()
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    matrix_identity = expected["matrix_identity"]
    run_identity = stable_hash({"matrix_identity": matrix_identity, "code_identity": expected["code_identity"]})
    checkpoint_root = checkpoint_dir(output_root, run_identity)
    if checkpoint_root.exists():
        for path in checkpoint_root.glob("fold_*.json"):
            path.unlink()
    fold_results = run_walk_forward(
        folds=expected["folds"],
        feature_rows=expected["matrix"]["feature_rows"],
        label_by_row=expected["label_by_row"],
        data_root=output_root,
        run_identity=run_identity,
        matrix_identity=matrix_identity,
        code_identity=expected["code_identity"],
        resume=False,
    )
    resumed = run_walk_forward(
        folds=expected["folds"],
        feature_rows=expected["matrix"]["feature_rows"],
        label_by_row=expected["label_by_row"],
        data_root=output_root,
        run_identity=run_identity,
        matrix_identity=matrix_identity,
        code_identity=expected["code_identity"],
        resume=True,
    )
    crash_equivalent = [left["fold_result_hash"] for left in fold_results] == [
        right["fold_result_hash"] for right in resumed
    ]
    rerun = [execute_fold(fold, expected["matrix"]["feature_rows"], expected["label_by_row"]) for fold in expected["folds"]]
    deterministic = [left["fold_result_hash"] for left in fold_results] == [
        right["fold_result_hash"] for right in rerun
    ]
    metrics = {
        "prior_only": summarize_metrics(fold_results, "prior_only"),
        "prior_plus_play_drive": summarize_metrics(fold_results, "prior_plus_play_drive"),
        "unique_game_prior_only": summarize_metrics(fold_results, "unique_game_prior_only"),
        "unique_game_prior_plus_play_drive": summarize_metrics(
            fold_results, "unique_game_prior_plus_play_drive"
        ),
    }
    incremental = None
    if (
        metrics["prior_only"]["brier"] is not None
        and metrics["prior_plus_play_drive"]["brier"] is not None
    ):
        incremental = {
            "brier_delta_plus_minus_prior": metrics["prior_plus_play_drive"]["brier"]
            - metrics["prior_only"]["brier"],
            "accuracy_delta_plus_minus_prior": metrics["prior_plus_play_drive"]["accuracy"]
            - metrics["prior_only"]["accuracy"],
            "promotion_authority": False,
        }
    proofs = {
        "deterministic_full_rerun": {"pass": deterministic},
        "crash_resume_equivalence": {"pass": crash_equivalent},
        "future_append_invariance": prove_future_append_invariance(
            expected["folds"], expected["matrix"]["feature_rows"], expected["label_by_row"], fold_results
        ),
        "postgame_append_invariance": prove_postgame_append_invariance(
            expected["folds"], expected["matrix"]["feature_rows"], expected["label_by_row"], fold_results
        ),
        "same_game_exclusion": prove_same_game_exclusion(
            expected["folds"][0], expected["matrix"]["feature_rows"], expected["label_by_row"]
        ),
        "fold_local_fitting": {
            "pass": fold_results[0]["first_fold_no_fit"] is True
            and fold_results[0]["prior_plus_model"]["kind"] == "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN"
            and all(
                fold["prior_plus_model"]["kind"] == "FOLD_LOCAL_LINEAR_PROBABILITY_ON_EPA_MEAN_RESIDUAL"
                for fold in fold_results[1:]
            )
        },
        "stale_checkpoint_rejection": prove_stale_checkpoint_rejection(
            expected["folds"][0],
            run_identity=run_identity,
            matrix_identity=matrix_identity,
            code_identity=expected["code_identity"],
        ),
        "protected_outcome_denial": prove_protected_outcome_denial(repo_root),
        "label_availability_after_completion": {
            "pass": all(
                parse_utc(str(expected["label_by_row"][row_id]["label_available_after_utc"]))
                < parse_utc(str(fold.get("fold_evaluation_cutoff_utc") or fold["min_cutoff_utc"]))
                for fold in fold_results
                for row_id in fold["train_row_ids"]
            )
            and all(
                parse_utc(str(expected["label_by_row"][str(row["row_id"])]["label_available_after_utc"]))
                > parse_utc(str(row["cutoff_utc"]))
                for fold in expected["folds"]
                for row in fold["rows"]
            )
            and all(
                parse_utc(str(expected["label_by_row"][str(row["row_id"])]["label_available_after_utc"]))
                > parse_utc(str(row["target_start_utc"]))
                for fold in expected["folds"]
                for row in fold["rows"]
            )
        },
        "unique_game_pairing": {
            "pass": expected["matrix"]["population"]["pairing"]["complementary_labels"] is True
            and expected["matrix"]["population"]["unique_games"]
            == expected["matrix"]["population"]["games"]
            and all(int(fold["eval_row_count"]) == 2 * int(fold["eval_unique_games"]) for fold in fold_results)
        },
    }
    if not all(item.get("pass") for item in proofs.values()):
        failed = [name for name, item in proofs.items() if not item.get("pass")]
        raise ValueError(f"development replay proofs failed: {failed}")
    payload_root = output_root / "features" / "development_2023_matrix" / "sha256" / matrix_identity
    manifest_root = output_root / "manifests" / "development_2023_matrix" / "sha256" / matrix_identity
    payload_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    feature_path = payload_root / "development_2023_matrix_features.parquet"
    label_path = payload_root / "development_2023_matrix_labels.parquet"
    expected["feature_frame"].write_parquet(feature_path, compression="zstd", statistics=True)
    expected["label_frame"].write_parquet(label_path, compression="zstd", statistics=True)
    fold_hashes = [row["fold_result_hash"] for row in fold_results]
    replay_identity = stable_hash(
        identity_core(
            contract_sha256=expected["contract_sha256"],
            input_identities=expected["contract"]["input_identities"],
            record_hashes=expected["record_hashes"],
            population=expected["matrix"]["population"],
            fold_hashes=fold_hashes,
            metrics=metrics,
        )
    )
    payloads = [
        {
            "name": "development_2023_matrix_features.parquet",
            "role": "DEVELOPMENT_ONLY_2023_FEATURE_MATRIX",
            "relative_path": str(feature_path.relative_to(output_root)).replace("\\", "/"),
            "rows": expected["feature_frame"].height,
            "bytes": feature_path.stat().st_size,
            "sha256": sha256_file(feature_path),
            "record_sha256": expected["record_hashes"]["features"],
            "columns": list(FEATURE_ROW_FIELDS),
        },
        {
            "name": "development_2023_matrix_labels.parquet",
            "role": "DEVELOPMENT_ONLY_2023_LABELS_NOT_FEATURES",
            "relative_path": str(label_path.relative_to(output_root)).replace("\\", "/"),
            "rows": expected["label_frame"].height,
            "bytes": label_path.stat().st_size,
            "sha256": sha256_file(label_path),
            "record_sha256": expected["record_hashes"]["labels"],
            "columns": list(LABEL_ROW_FIELDS),
        },
    ]
    compact_folds = [
        {
            "fold_id": fold["fold_id"],
            "fold_index": fold["fold_index"],
            "season_type": fold["season_type"],
            "week": fold["week"],
            "min_cutoff_utc": fold["min_cutoff_utc"],
            "max_cutoff_utc": fold["max_cutoff_utc"],
            "fold_evaluation_cutoff_utc": fold["fold_evaluation_cutoff_utc"],
            "eval_row_count": fold["eval_row_count"],
            "eval_unique_games": fold["eval_unique_games"],
            "train_row_count": fold["train_row_count"],
            "train_unique_games": fold["train_unique_games"],
            "same_game_excluded": fold["same_game_excluded"],
            "first_fold_no_fit": fold["first_fold_no_fit"],
            "prior_plus_model": fold["prior_plus_model"],
            "prior_only": fold["prior_only"],
            "prior_plus_play_drive": fold["prior_plus_play_drive"],
            "unique_game_prior_only": fold["unique_game_prior_only"],
            "unique_game_prior_plus_play_drive": fold["unique_game_prior_plus_play_drive"],
            "paired_probability": fold["paired_probability"],
            "fold_result_hash": fold["fold_result_hash"],
            "membership": {
                "train_membership_sha256": fold["membership"]["train_membership_sha256"],
                "eval_membership_sha256": fold["membership"]["eval_membership_sha256"],
                "game_id_intersection": fold["membership"]["game_id_intersection"],
                "row_id_intersection": fold["membership"]["row_id_intersection"],
                "excluded_candidate_count": len(fold["membership"]["excluded_candidates"]),
            },
        }
        for fold in fold_results
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_2023_LABELED_WALK_FORWARD",
        "classification": expected["contract"]["classification"],
        "contract_id": expected["contract"]["contract_id"],
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "parent_jira_key": expected["contract"]["parent_jira_key"],
        "matrix_identity": matrix_identity,
        "replay_identity": replay_identity,
        "issued_at_utc": issued_at_utc,
        "input_identities": expected["contract"]["input_identities"],
        "producer": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "polars": _polars().__version__,
            "code_identity": expected["code_identity"],
        },
        "population": expected["matrix"]["population"],
        "payloads": payloads,
        "authority": expected["contract"]["authority"],
        "label_semantics": expected["contract"]["label_semantics"],
        "negative_findings": expected["contract"]["negative_findings"],
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "issue_completion": expected_issue_completion(),
        "supersession": expected_supersession(),
        "protected_period_exclusions": sorted(PROTECTED_SEASONS),
        "pairing": expected["matrix"]["population"]["pairing"],
    }
    manifest_path = manifest_root / "development_2023_labeled_replay_manifest.json"
    _write_bytes(manifest_path, canonical_json_bytes(manifest) + b"\n")
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_2023_LABELED_WALK_FORWARD",
        "classification": expected["contract"]["classification"],
        "contract_id": expected["contract"]["contract_id"],
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "result": PASS_RESULT,
        "matrix_identity": matrix_identity,
        "replay_identity": replay_identity,
        "run_identity": run_identity,
        "code_identity": expected["code_identity"],
        "manifest": {
            "relative_path": str(manifest_path.relative_to(output_root)).replace("\\", "/"),
            "sha256": sha256_file(manifest_path),
        },
        "input_identities": expected["contract"]["input_identities"],
        "population": expected["matrix"]["population"],
        "pairing": expected["matrix"]["population"]["pairing"],
        "folds": compact_folds,
        "metrics": metrics,
        "incremental_play_drive_result": incremental,
        "proofs": proofs,
        "payloads": [
            {key: item[key] for key in ("name", "role", "rows", "bytes", "sha256", "record_sha256")}
            for item in payloads
        ],
        "authority": expected["contract"]["authority"],
        "label_semantics": expected["contract"]["label_semantics"],
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "issue_completion": expected_issue_completion(),
        "supersession": expected_supersession(),
        "protected_period_exclusions": sorted(PROTECTED_SEASONS),
        "issued_at_utc": issued_at_utc,
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    gate["artifact_identity"] = replay_identity
    _write_bytes(repo_root / GATE_RELATIVE, canonical_json_bytes(gate) + b"\n")
    return {
        "matrix_identity": matrix_identity,
        "replay_identity": replay_identity,
        "manifest_path": str(manifest_path),
        "gate_path": str(repo_root / GATE_RELATIVE),
        "population": expected["matrix"]["population"],
        "metrics": metrics,
        "incremental_play_drive_result": incremental,
        "proofs": {name: item["pass"] for name, item in proofs.items()},
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "bas_or_aggie_excess_result_claimed": False,
        "protected_performance_claimed": False,
        "production_model_ready": False,
        "trained_production_champion": False,
        "tamu_specialization_lift_claimed": False,
        "historical_population_ready": False,
        "protected_lane_opened": False,
    }


def expected_issue_completion() -> dict[str, Any]:
    return {
        "issue_complete": True,
        "logical_state": "DONE",
        "maturity": "IMPLEMENTED",
        "evidence_state": "VERIFIED",
        "protected_lane_opened": False,
        "promotion_authority": False,
    }


def expected_supersession() -> dict[str, str]:
    return {
        "matrix_identity": SUPERSEDED_CYCLE6_MATRIX_IDENTITY,
        "replay_identity": SUPERSEDED_CYCLE6_REPLAY_IDENTITY,
        "bat565_label_dataset_identity": SUPERSEDED_CYCLE6_LABEL_IDENTITY,
        "reason": "PAIR_PROBABILITY_AND_LABEL_AVAILABILITY_TRUTH",
        "kickoff_matrix_identity": SUPERSEDED_MATRIX_IDENTITY,
        "kickoff_replay_identity": SUPERSEDED_REPLAY_IDENTITY,
        "kickoff_bat565_label_dataset_identity": SUPERSEDED_KICKOFF_LABEL_IDENTITY,
        "kickoff_reason": "KICKOFF_TIME_LABEL_PARENT_INVALID",
    }


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({key: gate[key] for key in AUTHORITY_GATE_FIELDS if key in gate})


def expected_incremental(metrics: Mapping[str, Any]) -> dict[str, Any] | None:
    prior = metrics.get("prior_only") or {}
    plus = metrics.get("prior_plus_play_drive") or {}
    if prior.get("brier") is None or plus.get("brier") is None:
        return None
    return {
        "brier_delta_plus_minus_prior": plus["brier"] - prior["brier"],
        "accuracy_delta_plus_minus_prior": plus["accuracy"] - prior["accuracy"],
        "promotion_authority": False,
    }


def rebuild_metrics(fold_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "prior_only": summarize_metrics(fold_results, "prior_only"),
        "prior_plus_play_drive": summarize_metrics(fold_results, "prior_plus_play_drive"),
        "unique_game_prior_only": summarize_metrics(fold_results, "unique_game_prior_only"),
        "unique_game_prior_plus_play_drive": summarize_metrics(
            fold_results, "unique_game_prior_plus_play_drive"
        ),
    }


def compact_fold_summary(fold: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "fold_id": fold["fold_id"],
        "fold_index": fold["fold_index"],
        "season_type": fold["season_type"],
        "week": fold["week"],
        "min_cutoff_utc": fold["min_cutoff_utc"],
        "max_cutoff_utc": fold["max_cutoff_utc"],
        "fold_evaluation_cutoff_utc": fold["fold_evaluation_cutoff_utc"],
        "eval_row_count": fold["eval_row_count"],
        "eval_unique_games": fold["eval_unique_games"],
        "train_row_count": fold["train_row_count"],
        "train_unique_games": fold["train_unique_games"],
        "same_game_excluded": fold["same_game_excluded"],
        "first_fold_no_fit": fold["first_fold_no_fit"],
        "prior_plus_model": fold["prior_plus_model"],
        "prior_only": fold["prior_only"],
        "prior_plus_play_drive": fold["prior_plus_play_drive"],
        "unique_game_prior_only": fold["unique_game_prior_only"],
        "unique_game_prior_plus_play_drive": fold["unique_game_prior_plus_play_drive"],
        "paired_probability": fold["paired_probability"],
        "fold_result_hash": fold["fold_result_hash"],
        "membership": {
            "train_membership_sha256": fold["membership"]["train_membership_sha256"],
            "eval_membership_sha256": fold["membership"]["eval_membership_sha256"],
            "game_id_intersection": fold["membership"]["game_id_intersection"],
            "row_id_intersection": fold["membership"]["row_id_intersection"],
            "excluded_candidate_count": len(fold["membership"]["excluded_candidates"]),
        },
    }


def _compare(expected: Any, actual: Any, path: str, errors: list[str]) -> None:
    if type(expected) is not type(actual) and not (
        isinstance(expected, (int, float)) and isinstance(actual, (int, float))
    ):
        errors.append(f"{path}: type {type(actual).__name__} != {type(expected).__name__}")
        return
    if isinstance(expected, Mapping):
        extra = set(actual) - set(expected)
        missing = set(expected) - set(actual)
        if extra:
            errors.append(f"{path}: unexpected keys {sorted(extra)}")
        if missing:
            errors.append(f"{path}: missing keys {sorted(missing)}")
        for key in expected:
            if key in actual:
                _compare(expected[key], actual[key], f"{path}.{key}", errors)
        return
    if isinstance(expected, list):
        if len(expected) != len(actual):
            errors.append(f"{path}: length {len(actual)} != {len(expected)}")
            return
        for index, (left, right) in enumerate(zip(expected, actual)):
            _compare(left, right, f"{path}[{index}]", errors)
        return
    if expected != actual:
        errors.append(f"{path}: {actual!r} != {expected!r}")


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    gate_path = repo_root / GATE_RELATIVE
    loaded_gate = dict(gate) if gate is not None else json.loads(gate_path.read_text(encoding="utf-8"))
    if not require_rebuild:
        if loaded_gate.get("result") != PASS_RESULT:
            raise ValueError("gate result is not a 2023 labeled-replay pass")
        return {
            "result": "PASS",
            "mode": "gate_schema_only",
            "replay_identity": loaded_gate.get("replay_identity"),
        }
    rebuilt = expected or rebuild_expected(data_root=data_root, repo_root=repo_root)
    fold_results = [
        execute_fold(fold, rebuilt["matrix"]["feature_rows"], rebuilt["label_by_row"])
        for fold in rebuilt["folds"]
    ]
    metrics = rebuild_metrics(fold_results)
    incremental = expected_incremental(metrics)
    replay_identity = stable_hash(
        identity_core(
            contract_sha256=rebuilt["contract_sha256"],
            input_identities=rebuilt["contract"]["input_identities"],
            record_hashes=rebuilt["record_hashes"],
            population=rebuilt["matrix"]["population"],
            fold_hashes=[row["fold_result_hash"] for row in fold_results],
            metrics=metrics,
        )
    )
    run_identity = stable_hash(
        {"matrix_identity": rebuilt["matrix_identity"], "code_identity": rebuilt["code_identity"]}
    )
    identity = rebuilt["matrix_identity"]
    manifest_path = (
        data_root / "manifests" / "development_2023_matrix" / "sha256" / identity
        / "development_2023_labeled_replay_manifest.json"
    )
    loaded_manifest = (
        dict(manifest)
        if manifest is not None
        else json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    errors: list[str] = []
    if rebuilt["contract"]["input_identities"]["bat565_label_dataset_identity"] == SUPERSEDED_KICKOFF_LABEL_IDENTITY:
        errors.append("corrected BAT-565 identity is not bound")
    if loaded_gate.get("input_identities", {}).get("bat565_label_dataset_identity") == SUPERSEDED_KICKOFF_LABEL_IDENTITY:
        errors.append("altered BAT-565 parent identity")
    if loaded_gate.get("input_identities", {}).get("bat565_label_dataset_identity") != rebuilt["contract"][
        "input_identities"
    ]["bat565_label_dataset_identity"]:
        errors.append("altered BAT-565 parent identity")
    if loaded_gate.get("matrix_identity") != identity:
        errors.append("gate matrix identity does not match independently rebuilt identity")
    if loaded_gate.get("replay_identity") != replay_identity:
        errors.append("gate replay identity does not match independently rebuilt identity")
    if loaded_gate.get("run_identity") != run_identity:
        errors.append("gate run identity does not match independently rebuilt identity")
    if loaded_gate.get("code_identity") != rebuilt["code_identity"]:
        errors.append("gate code identity does not match independently rebuilt identity")
    if loaded_gate.get("population") != rebuilt["matrix"]["population"]:
        errors.append("gate population does not match rebuilt population")
    if loaded_gate.get("pairing") != rebuilt["matrix"]["population"]["pairing"]:
        errors.append("unique-game pairing was not independently reconstructed")
    if loaded_gate.get("metrics") != metrics:
        errors.append("gate metrics do not match independently rebuilt metrics")
    prior = metrics.get("prior_only") or {}
    unique = metrics.get("unique_game_prior_only") or {}
    if prior.get("evaluated_rows") != AUTHORITATIVE_PRIOR_ONLY_ROWS:
        errors.append("authoritative prior_only row count drifted")
    if prior.get("brier") != AUTHORITATIVE_PRIOR_ONLY_BRIER:
        errors.append("authoritative prior_only team-row Brier drifted")
    if unique.get("evaluated_rows") == prior.get("evaluated_rows"):
        errors.append("unique-game metrics silently replaced team-row metrics")
    if loaded_gate.get("incremental_play_drive_result") != incremental:
        errors.append("changed incremental result")
    if loaded_gate.get("authority") != rebuilt["contract"]["authority"]:
        errors.append("gate authority drift")
    if loaded_gate.get("authority", {}).get("champion_or_production_promotion") is not False:
        errors.append("promotion authority changed to true")
    if loaded_gate.get("scientific_nonclaims") != expected_scientific_nonclaims():
        errors.append("protected-performance claim changed to true")
    if loaded_gate.get("scientific_nonclaims", {}).get("protected_performance_claimed") is not False:
        errors.append("protected-performance claim changed to true")
    if loaded_gate.get("result") != PASS_RESULT:
        errors.append("altered result/classification")
    if loaded_gate.get("classification") != rebuilt["contract"]["classification"]:
        errors.append("altered result/classification")
    if loaded_gate.get("label_semantics") != rebuilt["contract"]["label_semantics"]:
        errors.append("altered label semantics")
    if loaded_gate.get("issue_completion") != expected_issue_completion():
        errors.append("altered issue completion state")
    if loaded_gate.get("supersession") != expected_supersession():
        errors.append("missing supersession record")
    if loaded_gate.get("protected_period_exclusions") != sorted(PROTECTED_SEASONS):
        errors.append("protected-period exclusions drifted")
    if loaded_gate.get("matrix_identity") == SUPERSEDED_MATRIX_IDENTITY:
        errors.append("superseded kickoff-time matrix identity is still active")
    if loaded_gate.get("replay_identity") == SUPERSEDED_REPLAY_IDENTITY:
        errors.append("superseded kickoff-time replay identity is still active")
    rebuilt_fold_hashes = [row["fold_result_hash"] for row in fold_results]
    actual_fold_hashes = [row.get("fold_result_hash") for row in loaded_gate.get("folds", [])]
    if rebuilt_fold_hashes != actual_fold_hashes:
        errors.append("changed fold membership")
    expected_compacts = [compact_fold_summary(row) for row in fold_results]
    if loaded_gate.get("folds") != expected_compacts:
        errors.append("fold summaries do not match independently rebuilt folds")
    for expected_fold, actual_fold in zip(expected_compacts, loaded_gate.get("folds", []), strict=False):
        if actual_fold.get("train_row_count") != expected_fold["train_row_count"]:
            errors.append("changed train-row count")
        if actual_fold.get("fold_evaluation_cutoff_utc") != expected_fold["fold_evaluation_cutoff_utc"]:
            errors.append("changed fold cutoff")
        if actual_fold.get("membership", {}).get("train_membership_sha256") != expected_fold["membership"][
            "train_membership_sha256"
        ]:
            errors.append("changed fold membership")
        if actual_fold.get("same_game_excluded") is not True:
            errors.append("changed same-game proof")
        if expected_fold["same_game_excluded"] is not True:
            errors.append("same-game exclusion was not independently derived")
        if actual_fold.get("membership", {}).get("game_id_intersection"):
            errors.append("target-game exclusion proof failed")
    same_game = prove_same_game_exclusion(
        rebuilt["folds"][0], rebuilt["matrix"]["feature_rows"], rebuilt["label_by_row"]
    )
    if same_game.get("pass") is not True:
        errors.append("changed same-game proof")
    availability_ok = all(
        parse_utc(str(rebuilt["label_by_row"][row_id]["label_available_after_utc"]))
        < parse_utc(str(fold.get("fold_evaluation_cutoff_utc") or fold["min_cutoff_utc"]))
        for fold in fold_results
        for row_id in fold["train_row_ids"]
    ) and all(
        parse_utc(str(rebuilt["label_by_row"][str(row["row_id"])]["label_available_after_utc"]))
        > parse_utc(str(row["cutoff_utc"]))
        for fold in rebuilt["folds"]
        for row in fold["rows"]
    )
    if not availability_ok:
        errors.append("availability-boundary proof failed")
    if loaded_gate.get("proofs", {}).get("deterministic_full_rerun", {}).get("pass") is not True:
        errors.append("full-rerun determinism proof missing")
    if loaded_gate.get("proofs", {}).get("crash_resume_equivalence", {}).get("pass") is not True:
        errors.append("crash/resume proof missing")
    if loaded_gate.get("proofs", {}).get("future_append_invariance", {}).get("pass") is not True:
        errors.append("future-append invariance proof missing")
    feature_payload = (
        data_root / "features" / "development_2023_matrix" / "sha256" / identity
        / "development_2023_matrix_features.parquet"
    )
    label_payload = (
        data_root / "features" / "development_2023_matrix" / "sha256" / identity
        / "development_2023_matrix_labels.parquet"
    )
    expected_payloads = [
        {
            "name": "development_2023_matrix_features.parquet",
            "path": feature_payload,
            "record_sha256": rebuilt["record_hashes"]["features"],
        },
        {
            "name": "development_2023_matrix_labels.parquet",
            "path": label_payload,
            "record_sha256": rebuilt["record_hashes"]["labels"],
        },
    ]
    listed = {item.get("name"): item for item in loaded_manifest.get("payloads", [])}
    gate_listed = {item.get("name"): item for item in loaded_gate.get("payloads", [])}
    for item in expected_payloads:
        if item["name"] not in listed:
            errors.append("omitted payload")
            continue
        if not item["path"].is_file():
            errors.append("omitted payload")
            continue
        digest = sha256_file(item["path"])
        if listed[item["name"]].get("sha256") != digest:
            errors.append("substituted matrix payload")
        if listed[item["name"]].get("record_sha256") != item["record_sha256"]:
            errors.append("substituted matrix payload")
        if gate_listed.get(item["name"], {}).get("sha256") != digest:
            errors.append("substituted matrix payload")
    if not loaded_manifest:
        errors.append("omitted payload")
    independently_recomputed = compute_gate_identity(
        {key: loaded_gate[key] for key in AUTHORITY_GATE_FIELDS if key in loaded_gate}
    )
    expected_gate_identity = compute_gate_identity(
        {
            **{key: loaded_gate.get(key) for key in AUTHORITY_GATE_FIELDS},
            "result": PASS_RESULT,
            "classification": rebuilt["contract"]["classification"],
            "matrix_identity": identity,
            "replay_identity": replay_identity,
            "run_identity": run_identity,
            "code_identity": rebuilt["code_identity"],
            "input_identities": rebuilt["contract"]["input_identities"],
            "population": rebuilt["matrix"]["population"],
            "pairing": rebuilt["matrix"]["population"]["pairing"],
            "folds": expected_compacts,
            "metrics": metrics,
            "incremental_play_drive_result": incremental,
            "payloads": loaded_gate.get("payloads"),
            "authority": rebuilt["contract"]["authority"],
            "label_semantics": rebuilt["contract"]["label_semantics"],
            "scientific_nonclaims": expected_scientific_nonclaims(),
            "issue_completion": expected_issue_completion(),
            "supersession": expected_supersession(),
            "protected_period_exclusions": sorted(PROTECTED_SEASONS),
            "schema_version": SCHEMA_VERSION,
            "artifact_type": "DEVELOPMENT_2023_LABELED_WALK_FORWARD",
            "contract_id": rebuilt["contract"]["contract_id"],
            "decision_unit": rebuilt["contract"]["decision_unit"],
            "jira_key": rebuilt["contract"]["jira_key"],
            "manifest": loaded_gate.get("manifest"),
            "proofs": loaded_gate.get("proofs"),
        }
    )
    if loaded_gate.get("gate_identity") != independently_recomputed:
        errors.append("gate identity does not match independently reconstructed authority")
    if independently_recomputed == expected_gate_identity and loaded_gate.get("result") != PASS_RESULT:
        errors.append("forged terminal state survived outer identity recomputation")
    if loaded_gate.get("result") != PASS_RESULT and independently_recomputed != expected_gate_identity:
        errors.append("forged terminal state after identity recomputation")
    if errors:
        raise ValueError("independent 2023 labeled-replay validation failed: " + "; ".join(errors[:16]))
    return {
        "result": "PASS",
        "mode": "independent_rebuild",
        "matrix_identity": identity,
        "replay_identity": replay_identity,
        "gate_identity": independently_recomputed,
        "population": rebuilt["matrix"]["population"],
        "metrics": metrics,
        "supersedes": SUPERSEDED_REPLAY_IDENTITY,
    }
