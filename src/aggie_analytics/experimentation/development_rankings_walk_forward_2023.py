from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.experimentation.development_2023_labeled_replay import (
    PROTECTED_SEASONS,
    assert_no_protected_outcomes,
    assert_unique_game_pairing,
    build_folds,
    classification_metrics,
    clip_probability,
    dataframe_record_sha256,
    fold_membership,
    parse_utc,
    prior_only_margin,
    prior_only_probability,
    prior_plus_probability,
    sha256_file,
    summarize_metrics,
    unique_game_eval_rows,
)
from aggie_analytics.validation.protected_split_authority import sha256_file as registry_sha256_file

SCHEMA_VERSION = "aggie.experimentation.development_rankings_walk_forward_2023.v1"
CONTRACT_RELATIVE = "configs/development_rankings_walk_forward_2023_contract.json"
GATE_RELATIVE = "artifacts/pit/development_rankings_walk_forward_2023.json"
CONTRACT_ID = "BAT-568-2023-RANKINGS-DEVELOPMENT-REPLAY-V1"
PASS_RESULT = "PASS_DEVELOPMENT_ONLY_2023_RANKINGS_WALK_FORWARD"
PASS_CLASSIFICATION = "DEVELOPMENT_ONLY_2023_RANKINGS_AUGMENTED_WALK_FORWARD"
DEVELOPMENT_SEASON = 2023
CANDIDATES = (
    "prior_only",
    "prior_plus_play_drive",
    "prior_plus_rankings",
    "prior_plus_play_drive_plus_rankings",
)
RANKING_STATES = (
    "RANKED_NUMERIC",
    "RECEIVING_VOTES",
    "EXPLICITLY_UNRANKED",
    "NOT_LISTED_IN_ELIGIBLE_POLL",
    "NO_ELIGIBLE_POLL",
    "UNRESOLVED_IDENTITY",
)
NON_AUTHORITATIVE_METADATA = ("issued_at_utc", "producer")
GATE_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "parent_identities",
    "input_identities",
    "joined_matrix_identity",
    "code_identity",
    "run_identity",
    "cohort",
    "coverage",
    "candidates",
    "metrics",
    "comparisons",
    "candidate_decisions",
    "authority",
    "scientific_nonclaims",
    "issue_completion",
    "protected_period_exclusions",
)


class RankingsJoinDenied(ValueError):
    """Raised when a rankings join is ambiguous, future, or protected."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("rankings walk-forward contract identity drift")
    if list(contract.get("candidates", [])) != list(CANDIDATES):
        raise ValueError("predeclared candidate list drifted")
    if contract.get("transforms", {}).get("unranked_as_26") is not False:
        raise ValueError("contract must not encode unranked as rank 26")
    if contract.get("authority", {}).get("protected_evaluation_admission") is not False:
        raise ValueError("contract must fail-close protected evaluation")
    if contract.get("authority", {}).get("champion_or_production_promotion") is not False:
        raise ValueError("contract must fail-close champion or production promotion")
    return contract


def expected_parent_identities(contract: Mapping[str, Any]) -> dict[str, str]:
    ids = contract["input_identities"]
    return {
        "BAT-565_label_dataset": ids["bat565_label_dataset_identity"],
        "BAT-566_matrix": ids["bat566_matrix_identity"],
        "BAT-566_replay": ids["bat566_replay_identity"],
        "BAT-527_rankings_run": ids["bat527_rankings_run_identity"],
        "BAT-527_rankings_state": ids["bat527_rankings_state_identity"],
        "BAT-527_rankings_feature": ids["bat527_rankings_feature_identity"],
        "protected_split_registry": ids["protected_split_registry_sha256"],
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "historical_population_ready": False,
        "protected_lane_opened": False,
        "protected_evaluation_admitted": False,
        "protected_performance_claimed": False,
        "champion_or_production_promotion": False,
        "trained_production_champion": False,
        "tamu_specialization_lift_claimed": False,
        "bas_or_aggie_excess_result_claimed": False,
        "unranked_encoded_as_26": False,
    }


def expected_issue_completion() -> dict[str, Any]:
    return {
        "jira_key": "BAT-568",
        "workflow_state": "DONE",
        "logical_state": "DONE",
        "maturity": "IMPLEMENTED",
        "evidence_state": "VERIFIED",
        "issue_complete": True,
        "promotion_authority": False,
        "protected_lane_opened": False,
    }


def expected_authority() -> dict[str, bool]:
    return {
        "development_2023_labeled_evaluation": True,
        "development_metric_reporting": True,
        "retain_development_candidate": True,
        "pregame_feature_use_of_labels": False,
        "protected_training_admission": False,
        "protected_evaluation_admission": False,
        "champion_or_production_promotion": False,
        "protected_performance_claims": False,
        "forecast_publication": False,
        "tamu_specialization_lift_claims": False,
        "bas_or_aggie_excess_claims": False,
    }


def compute_gate_identity(gate: Mapping[str, Any]) -> str:
    return stable_hash({key: gate[key] for key in GATE_IDENTITY_FIELDS if key in gate})


def classify_ranking_state(row: Mapping[str, Any]) -> str:
    if not row.get("canonical_team_id"):
        return "UNRESOLVED_IDENTITY"
    source = str(row.get("rank_state") or "")
    missing = str(row.get("missingness_disposition") or "")
    if source == "RANKED":
        return "RANKED_NUMERIC"
    if source == "RECEIVING_VOTES":
        return "RECEIVING_VOTES"
    if source == "NOT_RANKED":
        return "EXPLICITLY_UNRANKED"
    if missing == "NO_POLL_ELIGIBLE_AT_TARGET_CUTOFF":
        return "NO_ELIGIBLE_POLL"
    if source == "NOT_LISTED_OR_NO_ELIGIBLE_POLL" or missing == "TEAM_NOT_LISTED_IN_LATEST_ELIGIBLE_POLL":
        return "NOT_LISTED_IN_ELIGIBLE_POLL"
    raise RankingsJoinDenied(f"unclassified rankings state: {source}/{missing}")


def rank_signal(row: Mapping[str, Any]) -> float:
    if row.get("ranking_state") != "RANKED_NUMERIC" or row.get("rank") is None:
        return 0.0
    return (13.0 - float(row["rank"])) / 12.0


def receiving_votes_flag(row: Mapping[str, Any]) -> float:
    return 1.0 if row.get("ranking_state") == "RECEIVING_VOTES" else 0.0


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    order = len(vector)
    work = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for pivot in range(order):
        best = max(range(pivot, order), key=lambda index: abs(work[index][pivot]))
        if abs(work[best][pivot]) < 1e-12:
            return None
        work[pivot], work[best] = work[best], work[pivot]
        scale = work[pivot][pivot]
        for col in range(pivot, order + 1):
            work[pivot][col] /= scale
        for row in range(order):
            if row == pivot:
                continue
            factor = work[row][pivot]
            for col in range(pivot, order + 1):
                work[row][col] -= factor * work[pivot][col]
    return [work[index][order] for index in range(order)]


def fit_ols(columns: Sequence[Sequence[float]], residuals: Sequence[float]) -> list[float]:
    width = len(columns)
    length = len(residuals)
    if length == 0 or width == 0:
        return [0.0] * width
    xtx = [
        [sum(columns[left][index] * columns[right][index] for index in range(length)) for right in range(width)]
        for left in range(width)
    ]
    xty = [sum(columns[left][index] * residuals[index] for index in range(length)) for left in range(width)]
    solved = _solve(xtx, xty)
    return [0.0] * width if solved is None else solved


def fit_candidate_models(
    train_rows: Sequence[Mapping[str, Any]],
    label_by_row: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if not train_rows:
        return {
            "kind": "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN",
            "beta_epa": 0.0,
            "epa_mean": 0.0,
            "beta_rank": 0.0,
            "beta_votes": 0.0,
            "train_row_ids": [],
        }
    residuals: list[float] = []
    epas: list[float] = []
    ranks: list[float] = []
    votes: list[float] = []
    for row in train_rows:
        label = label_by_row[str(row["row_id"])]
        y = 1.0 if label["result"] == "WIN" else 0.0
        residuals.append(y - prior_only_probability(row))
        epas.append(0.0 if row.get("epa_mean") is None else float(row["epa_mean"]))
        ranks.append(rank_signal(row))
        votes.append(receiving_votes_flag(row))
    epa_mean = sum(epas) / float(len(epas))
    epa_centered = [value - epa_mean for value in epas]
    beta_epa = fit_ols([epa_centered], residuals)[0]
    beta_rank, beta_votes = fit_ols([ranks, votes], residuals)
    beta_epa_r, beta_rank_r, beta_votes_r = fit_ols([epa_centered, ranks, votes], residuals)
    return {
        "kind": "FOLD_LOCAL_OLS",
        "beta_epa": float(beta_epa),
        "epa_mean": float(epa_mean),
        "beta_rank": float(beta_rank),
        "beta_votes": float(beta_votes),
        "beta_epa_joint": float(beta_epa_r),
        "beta_rank_joint": float(beta_rank_r),
        "beta_votes_joint": float(beta_votes_r),
        "train_row_ids": [str(row["row_id"]) for row in train_rows],
    }


def candidate_probability(name: str, row: Mapping[str, Any], model: Mapping[str, Any]) -> float:
    prior = prior_only_probability(row)
    if model["kind"] == "HISTORICAL_ONLY_IDENTITY_OR_ABSTAIN":
        return prior
    if name == "prior_only":
        return prior
    if name == "prior_plus_play_drive":
        return prior_plus_probability(row, {"beta_epa": model["beta_epa"], "epa_mean": model["epa_mean"]})
    if name == "prior_plus_rankings":
        return clip_probability(
            prior + float(model["beta_rank"]) * rank_signal(row) + float(model["beta_votes"]) * receiving_votes_flag(row)
        )
    if name == "prior_plus_play_drive_plus_rankings":
        epa = 0.0 if row.get("epa_mean") is None else float(row["epa_mean"])
        return clip_probability(
            prior
            + float(model["beta_epa_joint"]) * (epa - float(model["epa_mean"]))
            + float(model["beta_rank_joint"]) * rank_signal(row)
            + float(model["beta_votes_joint"]) * receiving_votes_flag(row)
        )
    raise ValueError(f"unknown candidate: {name}")


def decide_candidates(metrics: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    prior = metrics["prior_only"]["brier"]
    play = metrics["prior_plus_play_drive"]["brier"]
    ranks = metrics["prior_plus_rankings"]["brier"]
    both = metrics["prior_plus_play_drive_plus_rankings"]["brier"]
    decisions = {
        "prior_only": {
            "state": "CORE_REFERENCE",
            "reason": "PREDECLARED_UNFITTED_PRIOR_REFERENCE",
        },
        "prior_plus_play_drive": {
            "state": "RETAIN_DEVELOPMENT_CANDIDATE"
            if play is not None and prior is not None and play < prior
            else "REJECTED_DEVELOPMENT",
            "reason": "PREDECLARED_BRIER_VS_PRIOR_ONLY",
        },
        "prior_plus_rankings": {
            "state": "RETAIN_DEVELOPMENT_CANDIDATE"
            if ranks is not None and prior is not None and ranks < prior
            else "REJECTED_DEVELOPMENT",
            "reason": "PREDECLARED_BRIER_VS_PRIOR_ONLY",
        },
        "prior_plus_play_drive_plus_rankings": {
            "state": "RETAIN_DEVELOPMENT_CANDIDATE"
            if both is not None and prior is not None and play is not None and both < prior and both < play
            else "REJECTED_DEVELOPMENT",
            "reason": "PREDECLARED_BRIER_VS_BOTH_REFERENCES",
        },
    }
    for item in decisions.values():
        if item["state"] in {"PRODUCTION_CHAMPION", "PROTECTED_WINNER", "PROMOTED_FEATURE_SET"}:
            raise ValueError("forbidden candidate state")
    return {
        "predeclared_candidate_count": 4,
        "any_candidate_improved_brier_vs_prior_only": any(
            metrics[name]["brier"] is not None and prior is not None and metrics[name]["brier"] < prior
            for name in CANDIDATES
            if name != "prior_only"
        ),
        "result_uncertain": True,
        "uncertainty_reason": "DEVELOPMENT_ONLY_NO_STATISTICAL_TEST_NO_PROTECTED_REPLICATION",
        "decisions": decisions,
    }


def verify_rankings_manifest(data_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    ids = contract["input_identities"]
    path = data_root / ids["bat527_rankings_manifest_relative_path"]
    digest = sha256_file(path)
    manifest = load_json(path)
    if manifest.get("run_identity") != ids["bat527_rankings_run_identity"]:
        raise ValueError("BAT-527 run identity drift")
    if manifest.get("state_identity") != ids["bat527_rankings_state_identity"]:
        raise ValueError("BAT-527 state identity drift")
    if manifest.get("feature_identity") != ids["bat527_rankings_feature_identity"]:
        raise ValueError("BAT-527 feature identity drift")
    payload = manifest["payloads"]["features"]
    if payload["sha256"] != ids["bat527_rankings_feature_payload_sha256"]:
        raise ValueError("BAT-527 feature payload SHA drift")
    return {
        "manifest_sha256": digest,
        "feature_name": payload["name"],
        "feature_relative_path": f"features/historical_rankings/sha256/{ids['bat527_rankings_feature_identity']}/{payload['name']}",
        "feature_rows": payload["rows"],
    }


def load_bat566_payloads(data_root: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    ids = contract["input_identities"]
    manifest = load_json(data_root / ids["bat566_manifest_relative_path"])
    if manifest.get("matrix_identity") != ids["bat566_matrix_identity"]:
        raise ValueError("active BAT-566 matrix identity drift")
    if manifest.get("replay_identity") != ids["bat566_replay_identity"]:
        raise ValueError("active BAT-566 replay identity drift")
    if manifest.get("matrix_identity") == "84e5aede6ab5e57fbd88185f587ead5b6d0be97265da5d495a417f689bbcbc8a":
        raise ValueError("kickoff-time BAT-566 matrix must not be consumed")
    by_name = {item["name"]: item for item in manifest["payloads"]}
    features_path = data_root / by_name["development_2023_matrix_features.parquet"]["relative_path"]
    labels_path = data_root / by_name["development_2023_matrix_labels.parquet"]["relative_path"]
    if sha256_file(features_path) != ids["bat566_feature_payload_sha256"]:
        raise ValueError("BAT-566 feature payload SHA drift")
    if sha256_file(labels_path) != ids["bat566_label_payload_sha256"]:
        raise ValueError("BAT-566 label payload SHA drift")
    return {"features_path": features_path, "labels_path": labels_path, "manifest": manifest}


def join_rankings(
    *,
    feature_rows: Sequence[Mapping[str, Any]],
    label_rows: Sequence[Mapping[str, Any]],
    rankings_rows: Sequence[Mapping[str, Any]],
    feature_identity: str,
    feature_payload_sha256: str,
) -> list[dict[str, Any]]:
    assert_no_protected_outcomes(feature_rows, context="rankings join features")
    assert_no_protected_outcomes(label_rows, context="rankings join labels")
    labels = {str(row["row_id"]): row for row in label_rows}
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rankings_rows:
        if int(row["season"]) != DEVELOPMENT_SEASON:
            continue
        key = (str(row["target_game_id"]), str(row["canonical_team_id"]))
        if key in by_key:
            raise RankingsJoinDenied("duplicate rankings join key")
        by_key[key] = dict(row)
    joined: list[dict[str, Any]] = []
    for feature in feature_rows:
        if int(feature["season"]) in PROTECTED_SEASONS:
            raise RankingsJoinDenied("protected-year feature entered the 2023 rankings experiment")
        key = (str(feature["target_game_id"]), str(feature["team_id"]))
        ranking = by_key.get(key)
        if ranking is None:
            raise RankingsJoinDenied(f"missing rankings join for {key}")
        if int(ranking["season"]) in PROTECTED_SEASONS:
            raise RankingsJoinDenied("protected-year rankings row joined into 2023 development")
        cutoff = parse_utc(str(feature["cutoff_utc"]))
        eligible = ranking.get("poll_first_eligible_at_utc")
        if eligible is not None and parse_utc(str(eligible)) > cutoff:
            raise RankingsJoinDenied("ineligible future poll used at prediction cutoff")
        state = classify_ranking_state(ranking)
        if state == "RANKED_NUMERIC" and ranking.get("rank") is None:
            raise RankingsJoinDenied("ranked row missing numeric rank")
        if state == "RANKED_NUMERIC" and float(ranking["rank"]) == 26:
            raise RankingsJoinDenied("unranked-as-26 encoding is forbidden")
        label = labels[str(feature["row_id"])]
        joined.append(
            {
                **dict(feature),
                "ranking_state": state,
                "rank": None if ranking.get("rank") is None else float(ranking["rank"]),
                "poll_available": bool(ranking.get("poll_available")),
                "team_listed_in_poll": bool(ranking.get("team_listed_in_poll")),
                "poll_first_eligible_at_utc": ranking.get("poll_first_eligible_at_utc"),
                "missingness_disposition": ranking.get("missingness_disposition"),
                "source_rank_state": ranking.get("rank_state"),
                "rankings_feature_identity": feature_identity,
                "rankings_feature_payload_sha256": feature_payload_sha256,
                "label_available_after_utc": label["label_available_after_utc"],
                "result": label["result"],
                "margin": label.get("margin"),
            }
        )
    if len(joined) != len(feature_rows):
        raise RankingsJoinDenied("joined population drifted from the BAT-566 cohort")
    return joined


def coverage_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = {state: 0 for state in RANKING_STATES}
    for row in rows:
        counts[str(row["ranking_state"])] += 1
    eligible = counts["RANKED_NUMERIC"] + counts["RECEIVING_VOTES"] + counts["EXPLICITLY_UNRANKED"]
    return {
        "team_rows": len(rows),
        "unique_games": len({str(row["target_game_id"]) for row in rows}),
        "ranking_state_counts": counts,
        "eligible_rankings_rows": eligible,
        "missing_or_unlisted_rows": counts["NOT_LISTED_IN_ELIGIBLE_POLL"]
        + counts["NO_ELIGIBLE_POLL"]
        + counts["UNRESOLVED_IDENTITY"],
        "ranked_numeric_rows": counts["RANKED_NUMERIC"],
        "receiving_votes_rows": counts["RECEIVING_VOTES"],
        "explicitly_unranked_rows": counts["EXPLICITLY_UNRANKED"],
        "no_eligible_poll_rows": counts["NO_ELIGIBLE_POLL"],
        "unresolved_identity_rows": counts["UNRESOLVED_IDENTITY"],
    }


def execute_rankings_fold(
    fold: Mapping[str, Any],
    joined_rows: Sequence[Mapping[str, Any]],
    label_by_row: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    membership = fold_membership(fold, joined_rows, label_by_row)
    train_rows = membership["train_rows"]
    eval_rows = membership["eval_rows"]
    model = fit_candidate_models(train_rows, label_by_row)
    first_fold = int(fold["fold_index"]) == 0
    if first_fold and train_rows:
        raise ValueError("first fold unexpectedly received 2023 training labels")
    result: dict[str, Any] = {
        "fold_id": fold["fold_id"],
        "fold_index": fold["fold_index"],
        "fold_evaluation_cutoff_utc": fold.get("fold_evaluation_cutoff_utc") or fold["min_cutoff_utc"],
        "train_row_count": len(train_rows),
        "eval_row_count": len(eval_rows),
        "same_game_excluded": True,
        "model": {key: model[key] for key in model if key != "train_row_ids"},
    }
    game_eval = unique_game_eval_rows(eval_rows)
    for name in CANDIDATES:
        abstain = first_fold and name != "prior_only"
        labels: list[float] = []
        probs: list[float] = []
        true_m: list[float | None] = []
        pred_m: list[float | None] = []
        if not abstain:
            for row in eval_rows:
                label = label_by_row[str(row["row_id"])]
                labels.append(1.0 if label["result"] == "WIN" else 0.0)
                probs.append(candidate_probability(name, row, model))
                true_m.append(None if label.get("margin") is None else float(label["margin"]))
                pred_m.append(prior_only_margin(row))
        metrics = classification_metrics(labels, probs, true_m, pred_m)
        metrics["abstained"] = abstain
        game_labels: list[float] = []
        game_probs: list[float] = []
        game_true: list[float | None] = []
        game_pred: list[float | None] = []
        if not abstain:
            for row in game_eval:
                label = label_by_row[str(row["row_id"])]
                game_labels.append(1.0 if label["result"] == "WIN" else 0.0)
                game_probs.append(candidate_probability(name, row, model))
                game_true.append(None if label.get("margin") is None else float(label["margin"]))
                game_pred.append(prior_only_margin(row))
        game_metrics = classification_metrics(game_labels, game_probs, game_true, game_pred)
        game_metrics["abstained"] = abstain
        result[name] = metrics
        result[f"unique_game_{name}"] = game_metrics
    return result


def apply_decision_rules(metrics: Mapping[str, Any]) -> dict[str, Any]:
    team = {name: metrics[name] for name in CANDIDATES}
    return decide_candidates(team)


def rebuild_expected(*, data_root: Path, repo_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    registry = registry_sha256_file(repo_root / contract["input_identities"]["protected_split_registry_relative_path"])
    if registry != contract["input_identities"]["protected_split_registry_sha256"]:
        raise ValueError("protected split registry drift")
    rankings_meta = verify_rankings_manifest(data_root, contract)
    bat566 = load_bat566_payloads(data_root, contract)
    pl = __import__("polars")
    features = pl.read_parquet(bat566["features_path"]).to_dicts()
    labels = pl.read_parquet(bat566["labels_path"]).to_dicts()
    rankings = pl.read_parquet(data_root / rankings_meta["feature_relative_path"]).to_dicts()
    joined = join_rankings(
        feature_rows=features,
        label_rows=labels,
        rankings_rows=rankings,
        feature_identity=contract["input_identities"]["bat527_rankings_feature_identity"],
        feature_payload_sha256=contract["input_identities"]["bat527_rankings_feature_payload_sha256"],
    )
    pairing = assert_unique_game_pairing(features, labels)
    folds = build_folds(joined)
    label_by_row = {str(row["row_id"]): row for row in labels}
    fold_results = [execute_rankings_fold(fold, joined, label_by_row) for fold in folds]
    metrics = {name: summarize_metrics(fold_results, name) for name in CANDIDATES}
    unique_metrics = {f"unique_game_{name}": summarize_metrics(fold_results, f"unique_game_{name}") for name in CANDIDATES}
    decisions = apply_decision_rules(metrics)
    coverage = coverage_summary(joined)
    joined_identity = stable_hash(
        {
            "rows": [
                {
                    "row_id": row["row_id"],
                    "target_game_id": row["target_game_id"],
                    "team_id": row["team_id"],
                    "ranking_state": row["ranking_state"],
                    "rank": row["rank"],
                    "poll_first_eligible_at_utc": row["poll_first_eligible_at_utc"],
                    "rankings_feature_identity": row["rankings_feature_identity"],
                }
                for row in sorted(joined, key=lambda item: str(item["row_id"]))
            ]
        }
    )
    code_identity = sha256_file(Path(__file__).resolve())
    run_identity = stable_hash({"joined_matrix_identity": joined_identity, "code_identity": code_identity})
    return {
        "contract": contract,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "parent_identities": expected_parent_identities(contract),
        "input_identities": contract["input_identities"],
        "joined": joined,
        "labels": labels,
        "folds": folds,
        "fold_results": fold_results,
        "metrics": {**metrics, **unique_metrics},
        "comparisons": {
            "predeclared_candidate_count": 4,
            "brier_delta_vs_prior_only": {
                name: None
                if metrics[name]["brier"] is None or metrics["prior_only"]["brier"] is None
                else metrics[name]["brier"] - metrics["prior_only"]["brier"]
                for name in CANDIDATES
                if name != "prior_only"
            },
            "brier_delta_vs_prior_plus_play_drive": {
                name: None
                if metrics[name]["brier"] is None or metrics["prior_plus_play_drive"]["brier"] is None
                else metrics[name]["brier"] - metrics["prior_plus_play_drive"]["brier"]
                for name in ("prior_plus_rankings", "prior_plus_play_drive_plus_rankings")
            },
        },
        "candidate_decisions": decisions,
        "coverage": coverage,
        "pairing": pairing,
        "joined_matrix_identity": joined_identity,
        "code_identity": code_identity,
        "run_identity": run_identity,
        "rankings_meta": rankings_meta,
    }


def expected_gate_document(expected: Mapping[str, Any]) -> dict[str, Any]:
    gate = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_2023_RANKINGS_WALK_FORWARD",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": expected["contract"]["contract_id"],
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "parent_identities": expected_parent_identities(expected["contract"]),
        "input_identities": expected["contract"]["input_identities"],
        "joined_matrix_identity": expected["joined_matrix_identity"],
        "code_identity": expected["code_identity"],
        "run_identity": expected["run_identity"],
        "cohort": {
            "season": DEVELOPMENT_SEASON,
            "team_rows": expected["coverage"]["team_rows"],
            "unique_games": expected["coverage"]["unique_games"],
            "fold_count": len(expected["fold_results"]),
            "protected_seasons_excluded": sorted(PROTECTED_SEASONS),
        },
        "coverage": expected["coverage"],
        "candidates": list(CANDIDATES),
        "metrics": expected["metrics"],
        "comparisons": expected["comparisons"],
        "candidate_decisions": expected["candidate_decisions"],
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "issue_completion": expected_issue_completion(),
        "protected_period_exclusions": sorted(PROTECTED_SEASONS),
    }
    gate["gate_identity"] = compute_gate_identity(gate)
    return gate


def materialize(*, data_root: Path, repo_root: Path, issued_at_utc: str) -> dict[str, Any]:
    expected = rebuild_expected(data_root=data_root, repo_root=repo_root)
    gate = expected_gate_document(expected)
    gate["issued_at_utc"] = issued_at_utc
    pl = __import__("polars")
    identity = expected["joined_matrix_identity"]
    payload_root = data_root / "features" / "development_rankings_2023" / "sha256" / identity
    payload_root.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame(expected["joined"], infer_schema_length=None)
    payload_path = payload_root / "development_rankings_2023_joined_rows.parquet"
    frame.write_parquet(payload_path)
    manifest = {
        "joined_matrix_identity": identity,
        "run_identity": expected["run_identity"],
        "code_identity": expected["code_identity"],
        "payloads": [
            {
                "name": payload_path.name,
                "rows": frame.height,
                "sha256": sha256_file(payload_path),
                "record_sha256": dataframe_record_sha256(frame),
                "relative_path": str(payload_path.relative_to(data_root)).replace("\\", "/"),
            }
        ],
        "parent_identities": expected["parent_identities"],
    }
    manifest_root = data_root / "manifests" / "development_rankings_2023" / "sha256" / identity
    manifest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_root / "development_rankings_walk_forward_2023_manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(gate) + b"\n")
    return {
        "gate_identity": gate["gate_identity"],
        "joined_matrix_identity": identity,
        "run_identity": expected["run_identity"],
        "payload_path": str(payload_path),
        "manifest_path": str(manifest_path),
        "candidate_decisions": expected["candidate_decisions"],
        "metrics": expected["metrics"],
    }


def validate_artifact(
    *,
    data_root: Path,
    repo_root: Path,
    require_rebuild: bool = True,
    gate: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    loaded = dict(gate) if gate is not None else load_json(repo_root / GATE_RELATIVE)
    if not require_rebuild:
        if loaded.get("result") != PASS_RESULT:
            raise ValueError("gate result is not a 2023 rankings development pass")
        return {"result": "PASS", "mode": "gate_schema_only", "gate_identity": loaded.get("gate_identity")}
    rebuilt = expected or rebuild_expected(data_root=data_root, repo_root=repo_root)
    expected_gate = expected_gate_document(rebuilt)
    errors: list[str] = []
    if loaded.get("parent_identities") != expected_parent_identities(rebuilt["contract"]):
        errors.append("parent identities were not derived from the authoritative contract")
    if loaded.get("candidates") != list(CANDIDATES):
        errors.append("candidate omission or addition")
    if loaded.get("candidate_decisions", {}).get("predeclared_candidate_count") != 4:
        errors.append("altered comparison count")
    if loaded.get("metrics") != rebuilt["metrics"]:
        errors.append("changed metrics")
    if loaded.get("cohort") != expected_gate["cohort"]:
        errors.append("changed cohort")
    if loaded.get("authority") != expected_authority():
        errors.append("authority fields were accepted from the gate instead of derived")
    if loaded.get("scientific_nonclaims") != expected_scientific_nonclaims():
        errors.append("scientific nonclaims drifted")
    if loaded.get("issue_completion") != expected_issue_completion():
        errors.append("issue completion state drifted")
    if loaded.get("result") != PASS_RESULT or loaded.get("classification") != PASS_CLASSIFICATION:
        errors.append("altered result/classification")
    if loaded.get("authority", {}).get("champion_or_production_promotion") is not False:
        errors.append("promotion authority forged")
    if loaded.get("authority", {}).get("protected_evaluation_admission") is not False:
        errors.append("protected evaluation admission forged")
    for key in GATE_IDENTITY_FIELDS:
        if loaded.get(key) != expected_gate.get(key):
            errors.append(f"gate.{key} is not independently reconstructed")
    recomputed = compute_gate_identity({key: loaded[key] for key in GATE_IDENTITY_FIELDS if key in loaded})
    if loaded.get("gate_identity") != expected_gate["gate_identity"]:
        errors.append("gate identity does not match independently reconstructed authority")
    if recomputed == expected_gate["gate_identity"] and loaded.get("result") != PASS_RESULT:
        errors.append("forged terminal state survived outer identity recomputation")
    if errors:
        raise ValueError("independent 2023 rankings walk-forward validation failed: " + "; ".join(errors[:16]))
    return {
        "result": "PASS",
        "mode": "independent_rebuild",
        "gate_identity": expected_gate["gate_identity"],
        "joined_matrix_identity": rebuilt["joined_matrix_identity"],
        "candidate_decisions": rebuilt["candidate_decisions"],
    }
