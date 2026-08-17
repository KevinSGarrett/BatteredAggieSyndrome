from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DEFAULT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DEFAULT / "src"))

from aggie_analytics.validation.protected_split_authority import (  # noqa: E402
    AUTHORITY_DENIALS,
    CONTAMINATION_STATUS,
    FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES,
    compute_artifact_identity,
    is_protected_canonical_season,
    iter_season_assignments,
    registry_role_for_season,
)

SCHEMA_VERSION = "aggie.governance.protected_split_exposure_audit.v1"
AUDIT_PATH = Path("artifacts/governance/protected_split_exposure_audit.json")
SURFACES = (
    "configs/preliminary_unprotected_baseline_contract.json",
    "artifacts/jira_evidence/POST-SUBTASK-169.json",
    "configs/preliminary_rankings_augmented_contract.json",
    "artifacts/jira_evidence/POST-SUBTASK-171.json",
    "configs/expanded_event_chronology_preliminary_contract.json",
    "artifacts/jira_evidence/POST-SUBTASK-172.json",
    "configs/preliminary_play_drive_augmented_contract.json",
    "configs/preliminary_play_enrichment_replay_contract.json",
    "configs/preliminary_dense_play_drive_replay_contract.json",
    "configs/preliminary_possession_pace_contract.json",
    "configs/preliminary_possession_pace_ablation_contract.json",
    "configs/preliminary_sustainability_contract.json",
    "configs/preliminary_sustainability_ablation_contract.json",
    "configs/preliminary_schedule_stress_contract.json",
    "configs/preliminary_schedule_stress_ablation_contract.json",
    "configs/preliminary_wmt_tamu_shadow_contract.json",
    "configs/preliminary_postgame_collapse_taxonomy_contract.json",
    "src/aggie_analytics/modeling/preliminary.py",
    "tools/validate_preliminary_unprotected_baselines.py",
    "tools/validate_preliminary_elo_uncertainty.py",
    "tools/validate_preliminary_elo_offense_defense.py",
    "tools/validate_expanded_event_chronology_preliminary.py",
    "tools/run_expanded_event_chronology_preliminary.py",
)
LIST_SPLIT_KEYS = {
    "development_tune": "DEVELOPMENT_TUNE",
    "development_evaluation_unprotected": "DEVELOPMENT_EVALUATION_UNPROTECTED",
    "development_fit": "DEVELOPMENT_FIT",
    "development_fit_selection_calibration": "DEVELOPMENT_FIT_SELECTION_CALIBRATION",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _literal_assignments(source: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES or node.value.startswith("DEVELOPMENT_"):
                found.append({"kind": "literal", "value": node.value, "lineno": node.lineno})
        if isinstance(node, ast.Tuple) and len(node.elts) == 2:
            season_node, role_node = node.elts
            if (
                isinstance(season_node, ast.Constant)
                and isinstance(season_node.value, int)
                and isinstance(role_node, ast.Constant)
                and isinstance(role_node.value, str)
            ):
                found.append(
                    {
                        "kind": "season_assignment",
                        "season": season_node.value,
                        "assignment": role_node.value,
                        "lineno": node.lineno,
                    }
                )
    return found


def _season_assignments_from_policy(split_policy: dict[str, Any]) -> list[tuple[int, str]]:
    assignments = list(iter_season_assignments(split_policy))
    if assignments:
        return assignments
    collected: list[tuple[int, str]] = []
    for key, assignment in LIST_SPLIT_KEYS.items():
        seasons = split_policy.get(key)
        if not isinstance(seasons, list):
            continue
        for season in seasons:
            collected.append((int(season), assignment))
    return sorted(collected)


def _collect_metrics(payload: dict[str, Any], path: str) -> list[dict[str, Any]]:
    exposed: list[dict[str, Any]] = []
    selected = payload.get("selected_preliminary_metrics")
    if isinstance(selected, dict):
        for bucket, models in selected.items():
            if not isinstance(models, dict):
                continue
            for family, metrics in models.items():
                exposed.append(
                    {
                        "source_path": path,
                        "bucket": bucket,
                        "family": family,
                        "metrics": metrics,
                        "seasons_implied": [2024, 2025] if "2025" in bucket or "2024" in bucket else [],
                    }
                )
    selected_2025 = payload.get("selected_2025_metrics")
    if isinstance(selected_2025, dict):
        for family, metrics in selected_2025.items():
            exposed.append(
                {
                    "source_path": path,
                    "bucket": "selected_2025_metrics",
                    "family": family,
                    "season": 2025,
                    "metrics": metrics,
                }
            )
    paired_2025 = payload.get("paired_2025_findings")
    if isinstance(paired_2025, dict):
        exposed.append(
            {
                "source_path": path,
                "bucket": "paired_2025_findings",
                "family": None,
                "season": 2025,
                "metrics": paired_2025,
            }
        )
    metrics_all = payload.get("metrics_all_games")
    if isinstance(metrics_all, dict):
        for family, by_season in metrics_all.items():
            if not isinstance(by_season, dict):
                continue
            for season, metrics in by_season.items():
                if str(season) in {"2024", "2025"}:
                    exposed.append(
                        {
                            "source_path": path,
                            "bucket": "metrics_all_games",
                            "family": family,
                            "season": int(season),
                            "metrics": metrics,
                        }
                    )
    slice_2025 = payload.get("relevant_slice_2025_texas_am")
    if isinstance(slice_2025, dict):
        exposed.append(
            {
                "source_path": path,
                "bucket": "relevant_slice_2025_texas_am",
                "family": slice_2025.get("best_observed_brier_family"),
                "metrics": {
                    "best_observed_brier": slice_2025.get("best_observed_brier"),
                    "best_observed_calibrated_brier": slice_2025.get("best_observed_calibrated_brier"),
                    "rows_per_model": slice_2025.get("rows_per_model"),
                },
                "season": 2025,
            }
        )
    return exposed


def audit_surface(repo_root: Path, relative: str) -> dict[str, Any]:
    path = repo_root / relative
    record: dict[str, Any] = {
        "path": relative,
        "exists": path.is_file(),
        "contradictions": [],
        "assignments": [],
        "exposed_results": [],
    }
    if not path.is_file():
        record["disposition"] = "ABSENT"
        return record
    if path.suffix == ".json":
        payload = _load_json(path)
        split_policy = (
            payload.get("split_policy")
            or payload.get("chronology_policy")
            or payload.get("population", {}).get("split_assignments")
        )
        if isinstance(split_policy, dict):
            for season, assignment in _season_assignments_from_policy(split_policy):
                registry = registry_role_for_season(repo_root, season)
                contradiction = is_protected_canonical_season(repo_root, season) and (
                    assignment in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES
                    or (
                        assignment not in {"PROTECTED_TEST", "PROTECTED_TEST_INACCESSIBLE"}
                        and "PROTECTED" not in assignment
                    )
                )
                item = {
                    "season": season,
                    "artifact_assignment": assignment,
                    "registry_split_id": registry["split_id"],
                    "registry_role": registry["role"],
                    "contradiction": contradiction,
                }
                record["assignments"].append(item)
                if contradiction:
                    record["contradictions"].append(item)
        record["exposed_results"] = _collect_metrics(payload, relative)
        contamination = payload.get("contamination")
        record["contamination_status"] = (
            contamination.get("status") if isinstance(contamination, dict) else None
        )
    else:
        literals = _literal_assignments(path.read_text(encoding="utf-8"))
        record["literals"] = literals
        for item in literals:
            if item.get("kind") == "season_assignment":
                season = int(item["season"])
                assignment = str(item["assignment"])
                registry = registry_role_for_season(repo_root, season)
                contradiction = is_protected_canonical_season(repo_root, season) and (
                    assignment in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES
                )
                assignment_row = {
                    "season": season,
                    "artifact_assignment": assignment,
                    "registry_split_id": registry["split_id"],
                    "registry_role": registry["role"],
                    "contradiction": contradiction,
                    "lineno": item["lineno"],
                }
                record["assignments"].append(assignment_row)
                if contradiction:
                    record["contradictions"].append(assignment_row)
    record["disposition"] = (
        CONTAMINATION_STATUS if record["contradictions"] or record["exposed_results"] else "NO_PROTECTED_EXPOSURE"
    )
    return record


def build_audit(repo_root: Path) -> dict[str, Any]:
    surfaces = [audit_surface(repo_root, relative) for relative in SURFACES]
    exposed_results = [item for surface in surfaces for item in surface.get("exposed_results", [])]
    contradictions = [item for surface in surfaces for item in surface.get("contradictions", [])]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "PROTECTED_SPLIT_EXPOSURE_AUDIT",
        "decision_unit": "POST-SUBTASK-169",
        "jira_key": "BAT-526",
        "registry_path": "governance/PROTECTED_SPLIT_REGISTRY.csv",
        "registry_unaltered": True,
        "classification": CONTAMINATION_STATUS,
        "surfaces": surfaces,
        "contradiction_count": len(contradictions),
        "exposed_result_count": len(exposed_results),
        "exposed_results": exposed_results,
        "authority_revoked_for": list(AUTHORITY_DENIALS),
        "successor_contract": "configs/preliminary_development_safe_baseline_contract.json",
        "historical_contracts_preserved": [
            "configs/preliminary_unprotected_baseline_contract.json",
            "artifacts/jira_evidence/POST-SUBTASK-169.json",
        ],
        "protected_nonclaims": {
            "replacement_protected_period_defined": False,
            "protected_split_registry_altered": False,
            "historical_metrics_deleted": False,
            "selection_or_promotion_authority_granted": False,
        },
        "acceptance": {
            "contradiction_contained": True,
            "historical_evidence_retained": True,
            "successor_contract_authoritative": True,
        },
    }
    payload["artifact_identity"] = compute_artifact_identity(payload)
    return payload


def validate_audit(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected protected-split audit schema")
    if payload.get("classification") != CONTAMINATION_STATUS:
        raise ValueError("audit classification must remain the exposure disposition")
    if payload.get("artifact_identity") != compute_artifact_identity(payload):
        raise ValueError("protected-split audit identity mismatch")
    if payload.get("registry_unaltered") is not True:
        raise ValueError("audit must not claim a registry rewrite")
    if payload.get("protected_nonclaims", {}).get("replacement_protected_period_defined"):
        raise ValueError("audit must not invent a replacement protected period")
    missing = [item for item in AUTHORITY_DENIALS if item not in set(payload.get("authority_revoked_for", []))]
    if missing:
        raise ValueError(f"audit missing authority denials: {missing}")
    if int(payload.get("contradiction_count") or 0) < 1:
        raise ValueError("audit must record the known protected-split contradiction")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    path = repo_root / AUDIT_PATH
    if args.validate:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_audit(payload)
        print(json.dumps({"result": "PASS", "path": str(path), "artifact_identity": payload["artifact_identity"]}))
        return 0
    payload = build_audit(repo_root)
    validate_audit(payload)
    if args.write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"result": "PASS", "path": str(path), "artifact_identity": payload["artifact_identity"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
