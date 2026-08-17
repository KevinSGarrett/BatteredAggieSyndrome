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
        "UNPROTECTED",
        "PRELIMINARY_UNPROTECTED",
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


def compute_artifact_identity(payload: Mapping[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("artifact_identity", None)
    return stable_hash(canonical)


def load_protected_split_registry(repo_root: Path) -> list[dict[str, str]]:
    path = repo_root / REGISTRY_RELATIVE
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("protected split registry is empty")
    return rows


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


def validate_current_contract(repo_root: Path, contract: Mapping[str, Any]) -> list[str]:
    if is_historical_contaminated_contract(contract):
        contamination = contract["contamination"]
        missing = [item for item in AUTHORITY_DENIALS if item not in set(contamination.get("authority_revoked_for", []))]
        errors = [f"contaminated contract missing authority revocation: {item}" for item in missing]
        if contamination.get("preserved_as") != "HISTORICAL_CONTAMINATED_EVIDENCE":
            errors.append("contaminated contract must remain preserved as historical evidence")
        return errors
    split_policy = contract.get("split_policy")
    if not isinstance(split_policy, Mapping):
        return ["current contract is missing split_policy"]
    return validate_current_split_policy(repo_root, split_policy, historical_contaminated=False)


def assert_current_contract_respects_protected_splits(repo_root: Path, contract: Mapping[str, Any]) -> None:
    errors = validate_current_contract(repo_root, contract)
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
