from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "aggie.experimentation.development_candidate_evidence_ledger.v1"
CONTRACT_RELATIVE = "configs/development_candidate_feature_registry.json"
LEDGER_RELATIVE = "artifacts/experimentation/development_candidate_evidence_ledger.json"
CONTRACT_ID = "BAT-569-DEVELOPMENT-CANDIDATE-EVIDENCE-LEDGER-V1"
PASS_RESULT = "PASS_DEVELOPMENT_CANDIDATE_EVIDENCE_LEDGER"
PASS_CLASSIFICATION = "DEVELOPMENT_ONLY_CANDIDATE_EVIDENCE_LEDGER"
DEVELOPMENT_SEASON = 2023
PROTECTED_SEASONS = (2024, 2025)
CANDIDATES = (
    "prior_only",
    "prior_plus_play_drive",
    "prior_plus_rankings",
    "prior_plus_play_drive_plus_rankings",
)
ALLOWED_STATES = (
    "CORE_REFERENCE",
    "RETAIN_DEVELOPMENT_CANDIDATE",
    "REJECTED_DEVELOPMENT",
    "BLOCKED_INSUFFICIENT_EVIDENCE",
    "BLOCKED_PROTECTED_EVALUATION",
)
FORBIDDEN_STATES = (
    "PRODUCTION_CHAMPION",
    "PROTECTED_WINNER",
    "PROMOTED_FEATURE_SET",
)
LEDGER_IDENTITY_FIELDS = (
    "schema_version",
    "artifact_type",
    "result",
    "classification",
    "contract_id",
    "decision_unit",
    "jira_key",
    "parent_identities",
    "bound_identities",
    "fold_definition_identity",
    "cohort",
    "coverage",
    "candidates",
    "entries",
    "comparison_count",
    "supersession",
    "authority",
    "scientific_nonclaims",
    "issue_completion",
    "protected_period_exclusions",
)
SHARED_METRIC_CANDIDATES = ("prior_only", "prior_plus_play_drive")
SHARED_METRIC_FIELDS = (
    "accuracy",
    "brier",
    "evaluated_folds",
    "evaluated_rows",
    "abstained_folds",
)


class LedgerValidationDenied(ValueError):
    """Raised when the development candidate ledger fails closed."""


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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract(repo_root: Path) -> dict[str, Any]:
    contract = load_json(repo_root / CONTRACT_RELATIVE)
    if contract.get("contract_id") != CONTRACT_ID:
        raise LedgerValidationDenied("development candidate ledger contract identity drift")
    if list(contract.get("required_candidates", [])) != list(CANDIDATES):
        raise LedgerValidationDenied("predeclared candidate list drifted")
    if list(contract.get("allowed_states", [])) != list(ALLOWED_STATES):
        raise LedgerValidationDenied("allowed ledger states drifted")
    if list(contract.get("forbidden_states", [])) != list(FORBIDDEN_STATES):
        raise LedgerValidationDenied("forbidden ledger states drifted")
    if contract.get("authority", {}).get("protected_evaluation_admission") is not False:
        raise LedgerValidationDenied("contract must fail-close protected evaluation")
    if contract.get("authority", {}).get("champion_or_production_promotion") is not False:
        raise LedgerValidationDenied("contract must fail-close champion or production promotion")
    if contract.get("authority", {}).get("production_feature_registry") is not False:
        raise LedgerValidationDenied("contract must not claim production feature-registry authority")
    return contract


def compute_ledger_identity(ledger: Mapping[str, Any]) -> str:
    return stable_hash({key: ledger[key] for key in LEDGER_IDENTITY_FIELDS if key in ledger})


def compute_fold_definition_identity(folds: Sequence[Mapping[str, Any]]) -> str:
    definition = [
        {
            "eval_row_count": fold["eval_row_count"],
            "eval_unique_games": fold["eval_unique_games"],
            "first_fold_no_fit": fold["first_fold_no_fit"],
            "fold_evaluation_cutoff_utc": fold["fold_evaluation_cutoff_utc"],
            "fold_id": fold["fold_id"],
            "fold_index": fold.get("fold_index"),
            "max_cutoff_utc": fold.get("max_cutoff_utc"),
            "min_cutoff_utc": fold.get("min_cutoff_utc"),
            "season_type": fold.get("season_type"),
            "train_row_count": fold.get("train_row_count"),
            "train_unique_games": fold.get("train_unique_games"),
            "week": fold.get("week"),
        }
        for fold in folds
    ]
    if len(definition) != 16:
        raise LedgerValidationDenied("2023 fold definition must contain exactly 16 folds")
    return stable_hash(definition)


def expected_authority() -> dict[str, bool]:
    return {
        "bas_or_aggie_excess_claims": False,
        "champion_or_production_promotion": False,
        "development_evidence_inventory": True,
        "development_metric_reporting": True,
        "forecast_publication": False,
        "pregame_feature_use_of_labels": False,
        "production_feature_registry": False,
        "protected_evaluation_admission": False,
        "protected_performance_claims": False,
        "protected_training_admission": False,
        "retain_development_candidate": True,
        "tamu_specialization_lift_claims": False,
    }


def expected_scientific_nonclaims() -> dict[str, bool]:
    return {
        "bas_or_aggie_excess_result_claimed": False,
        "champion_or_production_promotion": False,
        "historical_population_ready": False,
        "pregame_availability_inferred": False,
        "protected_evaluation_admitted": False,
        "protected_lane_opened": False,
        "protected_performance_claimed": False,
        "tamu_specialization_lift_claimed": False,
        "trained_production_champion": False,
        "unranked_encoded_as_26": False,
    }


def expected_issue_completion() -> dict[str, Any]:
    return {
        "evidence_state": "VERIFIED",
        "issue_complete": True,
        "jira_key": "BAT-569",
        "logical_state": "DONE",
        "maturity": "IMPLEMENTED",
        "promotion_authority": False,
        "protected_lane_opened": False,
        "workflow_state": "DONE",
    }


def expected_parent_identities(contract: Mapping[str, Any]) -> dict[str, str]:
    ids = contract["expected_identities"]
    return {
        "BAT-527_rankings_feature": ids["bat527_rankings_feature_identity"],
        "BAT-527_rankings_run": ids["bat527_rankings_run_identity"],
        "BAT-527_rankings_state": ids["bat527_rankings_state_identity"],
        "BAT-565_label_dataset": ids["bat565_label_dataset_identity"],
        "BAT-566_gate": ids["bat566_gate_identity"],
        "BAT-566_matrix": ids["bat566_matrix_identity"],
        "BAT-566_replay": ids["bat566_replay_identity"],
        "BAT-568_gate": ids["bat568_gate_identity"],
        "BAT-568_joined_matrix": ids["bat568_joined_matrix_identity"],
        "BAT-568_run": ids["bat568_run_identity"],
        "protected_split_registry": ids["protected_split_registry_sha256"],
    }


def _metric_slice(block: Mapping[str, Any]) -> dict[str, Any]:
    return {field: block[field] for field in SHARED_METRIC_FIELDS}


def _require_identities(
    *,
    contract: Mapping[str, Any],
    outcome_gate: Mapping[str, Any],
    replay_gate: Mapping[str, Any],
    rankings_gate: Mapping[str, Any],
    registry_sha256: str,
) -> dict[str, str]:
    expected = contract["expected_identities"]
    observed = {
        "bat565_label_dataset_identity": outcome_gate.get("dataset_identity"),
        "bat566_matrix_identity": replay_gate.get("matrix_identity"),
        "bat566_replay_identity": replay_gate.get("replay_identity") or replay_gate.get("artifact_identity"),
        "bat566_gate_identity": replay_gate.get("gate_identity"),
        "bat568_joined_matrix_identity": rankings_gate.get("joined_matrix_identity"),
        "bat568_run_identity": rankings_gate.get("run_identity"),
        "bat568_gate_identity": rankings_gate.get("gate_identity"),
        "bat527_rankings_run_identity": rankings_gate.get("input_identities", {}).get(
            "bat527_rankings_run_identity"
        ),
        "bat527_rankings_state_identity": rankings_gate.get("input_identities", {}).get(
            "bat527_rankings_state_identity"
        ),
        "bat527_rankings_feature_identity": rankings_gate.get("input_identities", {}).get(
            "bat527_rankings_feature_identity"
        ),
        "protected_split_registry_sha256": registry_sha256,
    }
    mismatches = [
        key for key, value in expected.items() if observed.get(key) != value
    ]
    if mismatches:
        raise LedgerValidationDenied(
            "source identity drift: " + ", ".join(mismatches)
        )
    if replay_gate.get("input_identities", {}).get("bat565_label_dataset_identity") != expected[
        "bat565_label_dataset_identity"
    ]:
        raise LedgerValidationDenied("BAT-566 still does not consume the corrected BAT-565 identity")
    if rankings_gate.get("parent_identities", {}).get("BAT-565_label_dataset") != expected[
        "bat565_label_dataset_identity"
    ]:
        raise LedgerValidationDenied("BAT-568 is not bound to the corrected BAT-565 identity")
    return observed


def _cross_check_shared_metrics(
    replay_gate: Mapping[str, Any],
    rankings_gate: Mapping[str, Any],
) -> None:
    replay_metrics = replay_gate.get("metrics") or {}
    rankings_metrics = rankings_gate.get("metrics") or {}
    for name in SHARED_METRIC_CANDIDATES:
        if _metric_slice(replay_metrics.get(name) or {}) != _metric_slice(rankings_metrics.get(name) or {}):
            raise LedgerValidationDenied(
                f"shared candidate metrics drifted between BAT-566 and BAT-568: {name}"
            )
    unique_prior = "unique_game_prior_only"
    if _metric_slice(replay_metrics.get(unique_prior) or {}) != _metric_slice(
        rankings_metrics.get(unique_prior) or {}
    ):
        raise LedgerValidationDenied("unique-game prior_only metrics drifted between BAT-566 and BAT-568")
    replay_delta = (replay_gate.get("incremental_play_drive_result") or {}).get(
        "brier_delta_plus_minus_prior"
    )
    rankings_delta = (rankings_gate.get("comparisons") or {}).get("brier_delta_vs_prior_only", {}).get(
        "prior_plus_play_drive"
    )
    if replay_delta != rankings_delta:
        raise LedgerValidationDenied("play/drive incremental Brier delta drifted between BAT-566 and BAT-568")


def _build_entries(rankings_gate: Mapping[str, Any]) -> list[dict[str, Any]]:
    metrics = rankings_gate["metrics"]
    decisions = rankings_gate["candidate_decisions"]["decisions"]
    deltas = rankings_gate["comparisons"]["brier_delta_vs_prior_only"]
    entries: list[dict[str, Any]] = []
    for name in CANDIDATES:
        block = metrics[name]
        unique = metrics[f"unique_game_{name}"]
        decision = decisions[name]
        state = decision["state"]
        reason = decision["reason"]
        if state not in ALLOWED_STATES:
            raise LedgerValidationDenied(f"forbidden or unknown candidate state: {name}={state}")
        if state in FORBIDDEN_STATES:
            raise LedgerValidationDenied(f"production or protected authority leaked into {name}")
        if not reason:
            raise LedgerValidationDenied(f"candidate decision is missing a reason: {name}")
        brier_delta = 0.0 if name == "prior_only" else float(deltas[name])
        entries.append(
            {
                "candidate": name,
                "state": state,
                "reason": reason,
                "team_row_metrics": {
                    "abstained_folds": block["abstained_folds"],
                    "accuracy": block["accuracy"],
                    "brier": block["brier"],
                    "evaluated_folds": block["evaluated_folds"],
                    "evaluated_rows": block["evaluated_rows"],
                    "log_loss": block["log_loss"],
                    "margin_mae": block["margin_mae"],
                },
                "unique_game_metrics": {
                    "abstained_folds": unique["abstained_folds"],
                    "accuracy": unique["accuracy"],
                    "brier": unique["brier"],
                    "evaluated_folds": unique["evaluated_folds"],
                    "evaluated_rows": unique["evaluated_rows"],
                    "log_loss": unique["log_loss"],
                    "margin_mae": unique["margin_mae"],
                },
                "brier_delta_vs_prior_only": brier_delta,
                "negative_result_preserved": name == "prior_only" or brier_delta > 0,
            }
        )
    if rankings_gate["candidate_decisions"].get("any_candidate_improved_brier_vs_prior_only") is not False:
        raise LedgerValidationDenied("ledger cannot hide that no candidate beat prior_only")
    if any(entry["state"] == "CORE_REFERENCE" for entry in entries[1:]):
        raise LedgerValidationDenied("only prior_only may be the core reference")
    if entries[0]["state"] != "CORE_REFERENCE":
        raise LedgerValidationDenied("prior_only must remain CORE_REFERENCE")
    return entries


def expected_supersession(contract: Mapping[str, Any]) -> dict[str, Any]:
    superseded = contract["superseded_identities"]
    return {
        "ledger_generation": 1,
        "prior_ledger_identity": superseded.get("prior_ledger_identity"),
        "supersession_kind": "FIRST_LEDGER_VERSION",
        "reason": "NO_PRIOR_IDENTITY_BOUND_DEVELOPMENT_CANDIDATE_LEDGER",
        "parent_experiment_history": {
            "kickoff_time_bat565_label_dataset": superseded["kickoff_time_bat565_label_dataset"],
            "kickoff_time_bat566_matrix": superseded["kickoff_time_bat566_matrix"],
            "kickoff_time_bat566_replay": superseded["kickoff_time_bat566_replay"],
            "active_use_forbidden": True,
        },
    }


def rebuild_expected(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    contract = load_contract(repo_root)
    sources = contract["source_artifacts"]
    outcome_gate = load_json(repo_root / sources["bat565_outcome_gate"])
    replay_gate = load_json(repo_root / sources["bat566_replay_gate"])
    rankings_gate = load_json(repo_root / sources["bat568_rankings_gate"])
    registry_sha256 = sha256_file(repo_root / sources["protected_split_registry"])
    observed = _require_identities(
        contract=contract,
        outcome_gate=outcome_gate,
        replay_gate=replay_gate,
        rankings_gate=rankings_gate,
        registry_sha256=registry_sha256,
    )
    _cross_check_shared_metrics(replay_gate, rankings_gate)
    fold_definition_identity = compute_fold_definition_identity(replay_gate["folds"])
    entries = _build_entries(rankings_gate)
    coverage = dict(rankings_gate["coverage"])
    if coverage.get("unresolved_identity_rows") != 0:
        raise LedgerValidationDenied("unresolved rankings identity rows are not permitted in this ledger")
    cohort = {
        "fold_count": 16,
        "fold_definition_identity": fold_definition_identity,
        "protected_seasons_excluded": list(PROTECTED_SEASONS),
        "season": DEVELOPMENT_SEASON,
        "team_rows": 1820,
        "unique_games": 910,
    }
    if rankings_gate.get("cohort") != {
        "fold_count": 16,
        "protected_seasons_excluded": list(PROTECTED_SEASONS),
        "season": DEVELOPMENT_SEASON,
        "team_rows": 1820,
        "unique_games": 910,
    }:
        raise LedgerValidationDenied("BAT-568 cohort drifted from the required 2023 development cohort")
    return {
        "contract": contract,
        "parent_identities": expected_parent_identities(contract),
        "bound_identities": {
            **observed,
            "bat566_gate_identity": replay_gate.get("gate_identity"),
            "bat568_code_identity": rankings_gate.get("code_identity"),
            "fold_definition_identity": fold_definition_identity,
        },
        "fold_definition_identity": fold_definition_identity,
        "cohort": cohort,
        "coverage": coverage,
        "candidates": list(CANDIDATES),
        "entries": entries,
        "comparison_count": 4,
        "supersession": expected_supersession(contract),
        "code_identity": sha256_file(Path(__file__)),
        "any_candidate_improved_brier_vs_prior_only": False,
        "uncertainty_reason": rankings_gate["candidate_decisions"]["uncertainty_reason"],
    }


def expected_ledger_document(expected: Mapping[str, Any]) -> dict[str, Any]:
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "DEVELOPMENT_CANDIDATE_EVIDENCE_LEDGER",
        "result": PASS_RESULT,
        "classification": PASS_CLASSIFICATION,
        "contract_id": expected["contract"]["contract_id"],
        "decision_unit": expected["contract"]["decision_unit"],
        "jira_key": expected["contract"]["jira_key"],
        "parent_identities": expected["parent_identities"],
        "bound_identities": expected["bound_identities"],
        "fold_definition_identity": expected["fold_definition_identity"],
        "cohort": expected["cohort"],
        "coverage": expected["coverage"],
        "candidates": expected["candidates"],
        "entries": expected["entries"],
        "comparison_count": expected["comparison_count"],
        "supersession": expected["supersession"],
        "authority": expected_authority(),
        "scientific_nonclaims": expected_scientific_nonclaims(),
        "issue_completion": expected_issue_completion(),
        "protected_period_exclusions": list(PROTECTED_SEASONS),
        "any_candidate_improved_brier_vs_prior_only": expected[
            "any_candidate_improved_brier_vs_prior_only"
        ],
        "uncertainty_reason": expected["uncertainty_reason"],
        "code_identity": expected["code_identity"],
    }
    ledger["ledger_identity"] = compute_ledger_identity(ledger)
    return ledger


def materialize(repo_root: Path) -> dict[str, Any]:
    expected = rebuild_expected(repo_root)
    ledger = expected_ledger_document(expected)
    path = repo_root / LEDGER_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(ledger) + b"\n")
    return {
        "ledger_identity": ledger["ledger_identity"],
        "fold_definition_identity": ledger["fold_definition_identity"],
        "comparison_count": ledger["comparison_count"],
        "path": str(path),
    }


def validate_artifact(
    *,
    repo_root: Path,
    ledger: Mapping[str, Any] | None = None,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    loaded = dict(ledger) if ledger is not None else load_json(repo_root / LEDGER_RELATIVE)
    rebuilt = expected or rebuild_expected(repo_root)
    expected_ledger = expected_ledger_document(rebuilt)
    errors: list[str] = []
    if loaded.get("parent_identities") != expected_parent_identities(rebuilt["contract"]):
        errors.append("parent identities were not derived from the authoritative contract")
    if loaded.get("candidates") != list(CANDIDATES):
        errors.append("hidden candidate or candidate omission")
    if loaded.get("comparison_count") != 4:
        errors.append("altered comparison count")
    if loaded.get("entries") != rebuilt["entries"]:
        errors.append("changed metrics or omitted negative result")
    if loaded.get("cohort") != expected_ledger["cohort"]:
        errors.append("changed cohort")
    if loaded.get("fold_definition_identity") != rebuilt["fold_definition_identity"]:
        errors.append("fold definition identity drift")
    if loaded.get("supersession") != expected_supersession(rebuilt["contract"]):
        errors.append("missing or altered supersession record")
    if loaded.get("supersession", {}).get("ledger_generation") != 1:
        errors.append("missing supersession record")
    if loaded.get("authority") != expected_authority():
        errors.append("authority fields were accepted from the ledger instead of derived")
    if loaded.get("scientific_nonclaims") != expected_scientific_nonclaims():
        errors.append("scientific nonclaims drifted")
    if loaded.get("issue_completion") != expected_issue_completion():
        errors.append("issue completion state drifted")
    if loaded.get("result") != PASS_RESULT or loaded.get("classification") != PASS_CLASSIFICATION:
        errors.append("altered result/classification")
    if loaded.get("authority", {}).get("champion_or_production_promotion") is not False:
        errors.append("production or protected authority")
    if loaded.get("authority", {}).get("protected_evaluation_admission") is not False:
        errors.append("production or protected authority")
    encoded_states = [entry.get("state") for entry in loaded.get("entries") or []]
    if any(state in FORBIDDEN_STATES for state in encoded_states):
        errors.append("production or protected authority")
    for entry, expected_entry in zip(loaded.get("entries") or [], rebuilt["entries"]):
        if entry.get("state") != expected_entry["state"] and not entry.get("reason"):
            errors.append("changed decision without reason")
        if entry.get("state") != expected_entry["state"]:
            errors.append("changed decision without independent source reason")
        if entry.get("reason") != expected_entry["reason"]:
            errors.append("changed decision without reason")
        if expected_entry["negative_result_preserved"] and not entry.get("negative_result_preserved"):
            errors.append("omitted negative result")
        if expected_entry["brier_delta_vs_prior_only"] > 0 and entry.get("brier_delta_vs_prior_only", 0) <= 0:
            errors.append("omitted negative result")
    for key in LEDGER_IDENTITY_FIELDS:
        if loaded.get(key) != expected_ledger.get(key):
            errors.append(f"ledger.{key} is not independently reconstructed")
    recomputed = compute_ledger_identity(
        {key: loaded[key] for key in LEDGER_IDENTITY_FIELDS if key in loaded}
    )
    if loaded.get("ledger_identity") != expected_ledger["ledger_identity"]:
        errors.append("ledger identity does not match independently reconstructed authority")
    if recomputed == expected_ledger["ledger_identity"] and loaded.get("result") != PASS_RESULT:
        errors.append("forged ledger completion survived outer identity recomputation")
    if loaded.get("issue_completion", {}).get("issue_complete") is True and loaded.get("result") != PASS_RESULT:
        errors.append("forged ledger completion after identity recomputation")
    if errors:
        raise LedgerValidationDenied(
            "independent development candidate ledger validation failed: " + "; ".join(errors[:16])
        )
    return {
        "result": "PASS",
        "mode": "independent_rebuild",
        "ledger_identity": expected_ledger["ledger_identity"],
        "fold_definition_identity": rebuilt["fold_definition_identity"],
        "comparison_count": 4,
    }
