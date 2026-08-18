from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .protected import classify_season

CONTAMINATION_STATUS = "HISTORICAL_PROTECTED_RESULT_EXPOSED_NO_SELECTION_OR_PROMOTION_AUTHORITY"
FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES = frozenset(
    {
        "DEVELOPMENT",
        "DEVELOPMENT_FIT",
        "DEVELOPMENT_TUNE",
        "DEVELOPMENT_SELECTION",
        "DEVELOPMENT_FIT_SELECTION_CALIBRATION",
        "DEVELOPMENT_EVALUATION_UNPROTECTED",
        "DEVELOPMENT_EVALUATION",
        "DEVELOPMENT_ONLY",
        "DEVELOPMENT_ONLY_HISTORICAL_KNOWN_AT_PIT_AGGREGATE",
        "UNPROTECTED",
        "PRELIMINARY_UNPROTECTED",
        "PRELIMINARY_UNPROTECTED_TRAINING_CANDIDATE",
        "FIT_ONLY_2023_OUTCOMES",
        "FIT_ONLY_2023_AND_2024_OUTCOMES",
        "FIT_ONLY_2023_A_AND_M_OUTCOMES",
        "FIT_ONLY_2023_AND_2024_A_AND_M_OUTCOMES",
    }
)
ALLOWED_PROTECTED_LABELS = frozenset(
    {
        "PROTECTED_TEST",
        "PROTECTED_TEST_INACCESSIBLE",
        "PROTECTED_FEATURE_ONLY",
        "SEALED_UNTIL_PROTOCOL_AND_ARTIFACT_READY",
    }
)
AUTHORITY_DENIALS = (
    "model_selection",
    "feature_selection",
    "calibration_selection",
    "threshold_setting",
    "champion_selection",
    "promotion",
    "protected_performance_claims",
)
REGISTRY_RELATIVE = "governance/PROTECTED_SPLIT_REGISTRY.csv"
SUCCESSOR_CONTRACT_RELATIVE = "configs/preliminary_development_safe_baseline_contract.json"
PROTECTED_SEASONS = frozenset({2024, 2025})
DEVELOPMENT_AUTHORITY_FLAGS = (
    "development_feature_admission",
    "preliminary_unprotected_training_candidate",
    "development_training",
    "development_tuning",
    "development_selection",
    "calibration_selection",
    "threshold_setting",
    "champion_selection",
    "promotion",
)

# Path-bound historical exemption. A contract cannot enter this set by
# self-labeling contamination.status. Identities are the committed file
# bytes that must remain preserved.
HISTORICAL_CONTRACT_ALLOWLIST: tuple[dict[str, str], ...] = (
    {
        "path": "configs/preliminary_unprotected_baseline_contract.json",
        "contract_id": "preliminary-unprotected-baselines-bat398-scoped-team-outcome-v1",
        "decision_unit": "POST-TASK-PRELIMINARY-BASELINES-001",
        "expected_sha256": "2ca2b5318a6a7e929a3d19e3b47c1cdd5c1ee3d9ebe56121087c735ffbcb9673",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "successor_contract_id": "preliminary-development-safe-baselines-bat398-scoped-team-outcome-v2",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/historical_play_drive_pit_aggregate_contract.json",
        "contract_id": "POST176-HISTORICAL-PLAY-DRIVE-PIT-AGGREGATE-V1",
        "decision_unit": "POST-SUBTASK-176",
        "expected_sha256": "d9578046c6fe8d076b06d771568b6aa92f0e37bf8b5908642b1f7c669620df37",
        "successor_path": "configs/historical_play_drive_pit_aggregate_development_safe_contract.json",
        "successor_contract_id": "POST176-HISTORICAL-PLAY-DRIVE-PIT-AGGREGATE-DEVELOPMENT-SAFE-V2",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/historical_play_drive_pit_extension_contract.json",
        "contract_id": "POST183-HISTORICAL-PLAY-DRIVE-PIT-EXTENSION-V1",
        "decision_unit": "POST-SUBTASK-183",
        "expected_sha256": "f1c1ec431023955cd45d23d93e0f7a41ecc07dbce5ba918825c5621d3b373591",
        "successor_path": "configs/historical_play_drive_pit_extension_development_safe_contract.json",
        "successor_contract_id": "POST183-HISTORICAL-PLAY-DRIVE-PIT-EXTENSION-DEVELOPMENT-SAFE-V2",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
)

_HISTORICAL_PRELIMINARY_SURFACES: tuple[dict[str, str], ...] = (
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-169.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-171.json",
        "decision_unit": "POST-SUBTASK-171",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-172.json",
        "decision_unit": "POST-SUBTASK-172",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_rankings_augmented_contract.json",
        "decision_unit": "POST-SUBTASK-171",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/expanded_event_chronology_preliminary_contract.json",
        "decision_unit": "POST-SUBTASK-172",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_play_drive_augmented_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_play_enrichment_replay_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_dense_play_drive_replay_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_possession_pace_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_possession_pace_ablation_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_sustainability_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_sustainability_ablation_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_schedule_stress_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_schedule_stress_ablation_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_wmt_tamu_shadow_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/preliminary_postgame_collapse_taxonomy_contract.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-176.json",
        "decision_unit": "POST-SUBTASK-176",
        "successor_path": "configs/historical_play_drive_pit_aggregate_development_safe_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-183.json",
        "decision_unit": "POST-SUBTASK-183",
        "successor_path": "configs/historical_play_drive_pit_extension_development_safe_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/pit/historical_play_drive_pit_aggregate_gate.json",
        "decision_unit": "POST-SUBTASK-183",
        "successor_path": "configs/historical_play_drive_pit_extension_development_safe_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/historical_play_enrichment_pit_contract.json",
        "decision_unit": "POST-SUBTASK-186",
        "successor_path": "configs/historical_play_drive_pit_extension_development_safe_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/historical_player_event_metric_pit_contract.json",
        "decision_unit": "POST-SUBTASK-185",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/historical_roster_membership_pit_contract.json",
        "decision_unit": "POST-SUBTASK-189",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/historical_team_membership_pit_contract.json",
        "decision_unit": "POST-SUBTASK-190",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/historical_venue_assignment_pit_contract.json",
        "decision_unit": "POST-SUBTASK-188",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "configs/wmt_provider_timestamp_pit_contract.json",
        "decision_unit": "POST-SUBTASK-178",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-178.json",
        "decision_unit": "POST-SUBTASK-178",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-184.json",
        "decision_unit": "POST-SUBTASK-184",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-185.json",
        "decision_unit": "POST-SUBTASK-185",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-186.json",
        "decision_unit": "POST-SUBTASK-186",
        "successor_path": "configs/historical_play_drive_pit_extension_development_safe_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/jira_evidence/POST-SUBTASK-187.json",
        "decision_unit": "POST-SUBTASK-187",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/pit/historical_play_enrichment_pit_gate.json",
        "decision_unit": "POST-SUBTASK-186",
        "successor_path": "configs/historical_play_drive_pit_extension_development_safe_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/pit/historical_roster_membership_pit_gate.json",
        "decision_unit": "POST-SUBTASK-189",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/pit/historical_venue_assignment_pit_gate.json",
        "decision_unit": "POST-SUBTASK-188",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/pit/preliminary_dense_play_drive_replay_gate.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
    {
        "path": "artifacts/pit/preliminary_play_enrichment_replay_gate.json",
        "decision_unit": "POST-SUBTASK-169",
        "successor_path": "configs/preliminary_development_safe_baseline_contract.json",
        "preserved_as": "HISTORICAL_CONTAMINATED_EVIDENCE",
    },
)
HISTORICAL_SURFACE_ALLOWLIST: tuple[dict[str, str], ...] = (
    HISTORICAL_CONTRACT_ALLOWLIST + _HISTORICAL_PRELIMINARY_SURFACES
)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compute_artifact_identity(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("artifact_identity", None)
    return stable_hash(canonical)


AUDIT_AUTHORITY_BEARING_FIELDS = (
    "schema_version",
    "artifact_type",
    "decision_unit",
    "jira_key",
    "registry_path",
    "registry_sha256",
    "registry_unaltered",
    "classification",
    "relevant_inventory",
    "surfaces",
    "surface_count",
    "relevant_surface_count",
    "contradiction_count",
    "exposed_result_count",
    "exposed_results",
    "authority_revoked_for",
    "successor_contract",
    "successor_contract_sha256",
    "historical_contracts_preserved",
    "historical_allowlist",
    "protected_nonclaims",
    "acceptance",
    "scan_policy",
    "scan_roots",
    "scan_suffixes",
    "scanner_code_identity",
    "supersedes_artifact_identity",
    "superseded_identities",
)


def compute_audit_identity(payload: Mapping[str, Any]) -> str:
    return stable_hash({field: payload.get(field) for field in AUDIT_AUTHORITY_BEARING_FIELDS})


def load_protected_split_registry(repo_root: Path) -> list[dict[str, str]]:
    path = repo_root / REGISTRY_RELATIVE
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("protected split registry is empty")
    return rows


def registry_sha256(repo_root: Path) -> str:
    return sha256_file(repo_root / REGISTRY_RELATIVE)


def _season_bound(value: str) -> int | None:
    if value in {"EARLIEST_QUALIFYING", "OPEN"}:
        return None
    return int(value)


def registry_role_for_season(repo_root: Path, season: int) -> dict[str, Any]:
    season = int(season)
    for row in load_protected_split_registry(repo_root):
        start = _season_bound(row["season_start"])
        end = _season_bound(row["season_end"])
        if start is not None and season < start:
            continue
        if end is not None and season > end:
            continue
        return {
            "season": season,
            "split_id": row["split_id"],
            "name": row["name"],
            "role": row["role"],
            "tuning_allowed": row["tuning_allowed"] == "true",
            "threshold_setting_allowed": row["threshold_setting_allowed"] == "true",
            "protected_result_access": row["protected_result_access"],
        }
    raise ValueError(f"season {season} is not covered by the protected split registry")


def is_protected_canonical_season(repo_root: Path, season: int) -> bool:
    return registry_role_for_season(repo_root, season)["role"] == "PROTECTED_TEST"


def protected_role_ignoring_label(repo_root: Path, season: int, _label: object) -> str:
    """Artifact labels cannot override sealed canonical-game membership."""
    return registry_role_for_season(repo_root, season)["role"]


def iter_season_assignments(split_policy: Mapping[str, Any]) -> list[tuple[int, str]]:
    assignments: list[tuple[int, str]] = []
    for key, value in split_policy.items():
        if not str(key).isdigit():
            continue
        if not isinstance(value, str):
            raise ValueError(f"split assignment for {key} must be a string")
        assignments.append((int(key), value))
    return sorted(assignments)


def is_historical_contaminated_contract(contract: Mapping[str, Any]) -> bool:
    contamination = contract.get("contamination")
    if not isinstance(contamination, Mapping):
        return False
    return contamination.get("status") == CONTAMINATION_STATUS


def required_authority_denials() -> tuple[str, ...]:
    return AUTHORITY_DENIALS


def allowlist_entry_for_path(relative_path: str | None) -> dict[str, str] | None:
    if not relative_path:
        return None
    normalized = relative_path.replace("\\", "/")
    for entry in HISTORICAL_CONTRACT_ALLOWLIST:
        if entry["path"] == normalized:
            return dict(entry)
    return None


def historical_surface_entry(relative_path: str | None) -> dict[str, str] | None:
    if not relative_path:
        return None
    normalized = relative_path.replace("\\", "/")
    for entry in HISTORICAL_SURFACE_ALLOWLIST:
        if entry["path"] == normalized:
            return dict(entry)
    return None


def _truthy_authority_flag(value: object) -> bool:
    return value is True or value == "true" or value == 1


def contract_implies_protected_development(contract: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    target_seasons = set()
    source_contract = contract.get("source_contract")
    if isinstance(source_contract, Mapping):
        for season in source_contract.get("target_seasons") or []:
            target_seasons.add(int(season))
    authorized = contract.get("authorized_inputs")
    if isinstance(authorized, Mapping):
        for season in authorized.get("target_seasons") or []:
            target_seasons.add(int(season))
        for season in authorized.get("protected_seasons") or []:
            target_seasons.add(int(season))
    classification = str(contract.get("classification") or "")
    authority = contract.get("authority")
    authority_map = authority if isinstance(authority, Mapping) else {}
    season_authority = contract.get("season_authority")
    if isinstance(season_authority, Mapping):
        for raw_season, payload in season_authority.items():
            if not str(raw_season).isdigit():
                continue
            season = int(raw_season)
            if season not in PROTECTED_SEASONS or not isinstance(payload, Mapping):
                continue
            role = str(payload.get("role") or payload.get("assignment") or "")
            outcomes = payload.get("outcomes_included")
            metrics = payload.get("metrics_included")
            if outcomes is True or metrics is True:
                errors.append(
                    f"season {season} protected feature surface cannot include outcomes or metrics"
                )
            if role in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES or role not in ALLOWED_PROTECTED_LABELS:
                if any(_truthy_authority_flag(payload.get(flag)) for flag in DEVELOPMENT_AUTHORITY_FLAGS):
                    errors.append(f"season {season} retains development authority via {role}")
            for flag in DEVELOPMENT_AUTHORITY_FLAGS:
                if _truthy_authority_flag(payload.get(flag)):
                    errors.append(f"season {season} forbids {flag}")
    protected_targets = target_seasons & PROTECTED_SEASONS
    if protected_targets:
        if classification in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES or classification.startswith(
            "DEVELOPMENT_ONLY"
        ):
            if not isinstance(season_authority, Mapping):
                errors.append(
                    f"classification {classification} cannot cover protected seasons {sorted(protected_targets)}"
                )
        for flag in (
            "development_feature_admission",
            "preliminary_unprotected_training_candidate",
        ):
            value = authority_map.get(flag)
            if _truthy_authority_flag(value) and not isinstance(season_authority, Mapping):
                errors.append(f"{flag} cannot remain true for protected target seasons")
            if value is True and not isinstance(season_authority, Mapping):
                errors.append(f"{flag}=true is a development role for {sorted(protected_targets)}")
    return errors


def validate_current_split_policy(
    repo_root: Path,
    split_policy: Mapping[str, Any],
    *,
    historical_contaminated: bool = False,
) -> list[str]:
    errors: list[str] = []
    if historical_contaminated:
        return errors
    for season, assignment in iter_season_assignments(split_policy):
        registry = registry_role_for_season(repo_root, season)
        if registry["role"] != "PROTECTED_TEST":
            continue
        if assignment in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES or assignment not in ALLOWED_PROTECTED_LABELS:
            errors.append(
                f"season {season} is {registry['split_id']} {registry['role']} and cannot be labeled {assignment}"
            )
        if registry["tuning_allowed"] is False and "TUNE" in assignment:
            errors.append(f"season {season} forbids tuning; assignment {assignment} is invalid")
        if "EVALUATION" in assignment and "PROTECTED" not in assignment:
            errors.append(
                f"season {season} cannot be treated as an evaluation/development role via {assignment}"
            )
    return errors


def _validate_allowlisted_historical(
    repo_root: Path,
    contract: Mapping[str, Any],
    relative_path: str,
    entry: Mapping[str, str],
) -> list[str]:
    errors: list[str] = []
    path = repo_root / relative_path
    if not path.is_file():
        return [f"allowlisted historical contract is missing: {relative_path}"]
    digest = sha256_file(path)
    if digest != entry["expected_sha256"]:
        errors.append(
            f"allowlisted historical contract {relative_path} identity drifted: {digest} != {entry['expected_sha256']}"
        )
    if contract.get("contract_id") != entry["contract_id"]:
        errors.append(
            f"allowlisted historical contract_id {contract.get('contract_id')} does not match {entry['contract_id']}"
        )
    file_contract = json.loads(path.read_text(encoding="utf-8"))
    if stable_hash(file_contract) != stable_hash(contract):
        errors.append("in-memory contract does not match the allowlisted repository file")
    successor = repo_root / entry["successor_path"]
    if not successor.is_file():
        errors.append(f"successor contract missing: {entry['successor_path']}")
    else:
        successor_payload = json.loads(successor.read_text(encoding="utf-8"))
        if successor_payload.get("contract_id") != entry["successor_contract_id"]:
            errors.append("successor contract identity does not match the allowlist")
    contamination = contract.get("contamination")
    if isinstance(contamination, Mapping):
        missing = [item for item in AUTHORITY_DENIALS if item not in set(contamination.get("authority_revoked_for", []))]
        errors.extend(f"contaminated contract missing authority revocation: {item}" for item in missing)
        if contamination.get("preserved_as") != entry["preserved_as"]:
            errors.append("contaminated contract must remain preserved as historical evidence")
        if contamination.get("superseded_by") != entry["successor_path"]:
            errors.append("contaminated contract successor binding is not allowlisted")
    return errors


def validate_current_contract(
    repo_root: Path,
    contract: Mapping[str, Any],
    *,
    relative_path: str | None = None,
) -> list[str]:
    entry = allowlist_entry_for_path(relative_path)
    if entry is not None:
        return _validate_allowlisted_historical(repo_root, contract, relative_path or entry["path"], entry)
    if is_historical_contaminated_contract(contract):
        return [
            "contract cannot self-exempt via contamination.status; historical exemption requires an allowlisted repository path and identity"
        ]
    errors: list[str] = []
    split_policy = contract.get("split_policy")
    if isinstance(split_policy, Mapping):
        errors.extend(validate_current_split_policy(repo_root, split_policy, historical_contaminated=False))
    elif contract.get("season_authority") is None and contract.get("source_contract") is None:
        errors.append("current contract is missing split_policy")
    errors.extend(contract_implies_protected_development(contract))
    return errors


def assert_current_contract_respects_protected_splits(
    repo_root: Path,
    contract: Mapping[str, Any],
    *,
    relative_path: str | None = None,
) -> None:
    errors = validate_current_contract(repo_root, contract, relative_path=relative_path)
    if errors:
        raise ValueError("; ".join(errors))


def assert_labels_cannot_override_protected_membership(
    repo_root: Path, season: int, label: str
) -> str:
    role = protected_role_ignoring_label(repo_root, season, label)
    hardcoded = classify_season(season)
    if role != hardcoded:
        raise ValueError(f"registry role {role} drifted from classify_season {hardcoded}")
    if role == "PROTECTED_TEST" and label in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES:
        return role
    if role == "PROTECTED_TEST":
        return role
    return role


def assert_protected_feature_surface_denies_outcomes(payload: Mapping[str, Any]) -> None:
    season_authority = payload.get("season_authority")
    if not isinstance(season_authority, Mapping):
        return
    for raw_season, item in season_authority.items():
        if not str(raw_season).isdigit() or int(raw_season) not in PROTECTED_SEASONS:
            continue
        if not isinstance(item, Mapping):
            raise ValueError(f"season {raw_season} authority must be an object")
        if item.get("outcomes_included") is not False or item.get("metrics_included") is not False:
            raise ValueError(f"season {raw_season} protected feature surface gained outcome or metric access")
