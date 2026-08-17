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
    ALLOWED_PROTECTED_LABELS,
    AUTHORITY_DENIALS,
    CONTAMINATION_STATUS,
    FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES,
    HISTORICAL_CONTRACT_ALLOWLIST,
    HISTORICAL_SURFACE_ALLOWLIST,
    PROTECTED_SEASONS,
    SUCCESSOR_CONTRACT_RELATIVE,
    compute_artifact_identity,
    historical_surface_entry,
    is_protected_canonical_season,
    iter_season_assignments,
    registry_role_for_season,
    registry_sha256,
    sha256_file,
    validate_current_contract,
)

SCHEMA_VERSION = "aggie.governance.protected_split_exposure_audit.v2"
AUDIT_PATH = Path("artifacts/governance/protected_split_exposure_audit.json")
SCAN_ROOTS = (
    "configs",
    "artifacts/governance",
    "artifacts/jira_evidence",
    "artifacts/pit",
    "src/aggie_analytics",
    "tools",
)
SCAN_SUFFIXES = {".json", ".py"}
LIST_SPLIT_KEYS = {
    "development_tune": "DEVELOPMENT_TUNE",
    "development_evaluation_unprotected": "DEVELOPMENT_EVALUATION_UNPROTECTED",
    "development_fit": "DEVELOPMENT_FIT",
    "development_fit_selection_calibration": "DEVELOPMENT_FIT_SELECTION_CALIBRATION",
}
AUTHORITY_BEARING_FIELDS = (
    "schema_version",
    "artifact_type",
    "decision_unit",
    "jira_key",
    "registry_path",
    "registry_sha256",
    "registry_unaltered",
    "classification",
    "discovered_inventory",
    "surfaces",
    "surface_count",
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
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _posix(relative: Path) -> str:
    return relative.as_posix()


def discover_candidate_paths(repo_root: Path) -> list[str]:
    found: list[str] = []
    for root_name in SCAN_ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            if path.name == AUDIT_PATH.name and path.parent.name == "governance":
                continue
            found.append(_posix(path.relative_to(repo_root)))
    return sorted(set(found))


def _literal_assignments(source: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
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
        if isinstance(node, ast.Dict):
            seasons: dict[int, str] = {}
            for key_node, value_node in zip(node.keys, node.values):
                if isinstance(key_node, ast.Constant) and isinstance(value_node, ast.Constant):
                    if (
                        isinstance(key_node.value, str)
                        and key_node.value.isdigit()
                        and isinstance(value_node.value, str)
                    ):
                        seasons[int(key_node.value)] = value_node.value
            for season, assignment in sorted(seasons.items()):
                found.append(
                    {
                        "kind": "season_assignment",
                        "season": season,
                        "assignment": assignment,
                        "lineno": getattr(node, "lineno", 0),
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
    coverage = payload.get("coverage_by_target_season")
    if isinstance(coverage, dict):
        for season, metrics in coverage.items():
            if str(season) in {"2024", "2025"} and isinstance(metrics, dict):
                exposed.append(
                    {
                        "source_path": path,
                        "bucket": "coverage_by_target_season",
                        "family": None,
                        "season": int(season),
                        "metrics": metrics,
                    }
                )
    labeled = payload.get("population", {})
    if isinstance(labeled, dict):
        by_season = labeled.get("labeled_by_season")
        if isinstance(by_season, dict):
            for season, count in by_season.items():
                if str(season) in {"2024", "2025"}:
                    exposed.append(
                        {
                            "source_path": path,
                            "bucket": "labeled_by_season",
                            "family": None,
                            "season": int(season),
                            "metrics": {"labeled_games": count},
                        }
                    )
    return exposed


def _boolish(value: object) -> bool:
    return value is True or value == "true"


def _assignment_row(
    repo_root: Path,
    season: int,
    assignment: str,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry_role_for_season(repo_root, season)
    protected = is_protected_canonical_season(repo_root, season)
    contradiction = protected and (
        assignment in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES
        or (
            assignment not in ALLOWED_PROTECTED_LABELS
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
    if extra:
        item.update(extra)
    return item


def _json_authority_signals(payload: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    target_seasons: list[int] = []
    for container_key in ("source_contract", "authorized_inputs", "admitted_layer", "admitted_aggregate", "population"):
        container = payload.get(container_key)
        if isinstance(container, dict):
            for season in container.get("target_seasons") or []:
                target_seasons.append(int(season))
    if isinstance(payload.get("target_seasons"), list):
        target_seasons.extend(int(item) for item in payload["target_seasons"])
    classification = str(payload.get("classification") or "")
    authority = payload.get("authority") if isinstance(payload.get("authority"), dict) else {}
    season_authority = payload.get("season_authority") if isinstance(payload.get("season_authority"), dict) else {}
    for season in sorted(set(target_seasons) & PROTECTED_SEASONS):
        per_season = season_authority.get(str(season)) if isinstance(season_authority.get(str(season)), dict) else {}
        outcomes = per_season.get("outcomes_included")
        metrics = per_season.get("metrics_included")
        role = str(per_season.get("role") or "")
        development_flags = {
            key: value
            for key, value in {
                "development_feature_admission": authority.get("development_feature_admission"),
                "preliminary_unprotected_training_candidate": authority.get(
                    "preliminary_unprotected_training_candidate"
                ),
                "development_training": per_season.get("development_training"),
                "development_tuning": per_season.get("development_tuning"),
            }.items()
            if _boolish(value)
        }
        if role in ALLOWED_PROTECTED_LABELS and outcomes is False and metrics is False and not development_flags:
            signals.append(
                {
                    "season": season,
                    "assignment": role,
                    "kind": "PROTECTED_FEATURE_ONLY",
                    "outcomes_included": False,
                    "metrics_included": False,
                }
            )
            continue
        if classification.startswith("DEVELOPMENT_ONLY") or classification in FORBIDDEN_PROTECTED_DEVELOPMENT_ROLES:
            signals.append(
                {
                    "season": season,
                    "assignment": classification or "DEVELOPMENT_ONLY",
                    "kind": "CLASSIFICATION",
                    "outcomes_included": outcomes,
                    "metrics_included": metrics,
                }
            )
        if development_flags:
            for flag in development_flags:
                signals.append(
                    {
                        "season": season,
                        "assignment": flag,
                        "kind": "AUTHORITY_FLAG",
                        "outcomes_included": outcomes,
                        "metrics_included": metrics,
                    }
                )
        if outcomes is True or metrics is True:
            signals.append(
                {
                    "season": season,
                    "assignment": "PROTECTED_FEATURE_OUTCOME_OR_METRIC_ACCESS",
                    "kind": "PROTECTED_FEATURE_TAMPER",
                    "outcomes_included": outcomes,
                    "metrics_included": metrics,
                }
            )
    return signals


def audit_surface(repo_root: Path, relative: str) -> dict[str, Any]:
    path = repo_root / relative
    record: dict[str, Any] = {
        "path": relative,
        "exists": path.is_file(),
        "sha256": sha256_file(path) if path.is_file() else None,
        "contradictions": [],
        "assignments": [],
        "exposed_results": [],
        "authority_signals": [],
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
                item = _assignment_row(repo_root, season, assignment)
                record["assignments"].append(item)
                if item["contradiction"]:
                    record["contradictions"].append(item)
        record["authority_signals"] = _json_authority_signals(payload)
        for signal in record["authority_signals"]:
            item = _assignment_row(
                repo_root,
                int(signal["season"]),
                str(signal["assignment"]),
                extra={"signal_kind": signal["kind"]},
            )
            if signal["kind"] == "PROTECTED_FEATURE_ONLY":
                item["contradiction"] = False
            if signal["kind"] == "PROTECTED_FEATURE_TAMPER":
                item["contradiction"] = True
            record["assignments"].append(item)
            if item["contradiction"]:
                record["contradictions"].append(item)
        record["exposed_results"] = _collect_metrics(payload, relative)
        contamination = payload.get("contamination") or payload.get("protected_split_containment")
        record["contamination_status"] = (
            contamination.get("status") if isinstance(contamination, dict) else None
        )
        record["outcomes_included"] = payload.get("outcomes_included")
        record["metrics_included"] = payload.get("metrics_included")
        if isinstance(payload.get("season_authority"), dict):
            for season, item in payload["season_authority"].items():
                if str(season) in {"2024", "2025"} and isinstance(item, dict):
                    if item.get("outcomes_included") is True or item.get("metrics_included") is True:
                        record["contradictions"].append(
                            _assignment_row(
                                repo_root,
                                int(season),
                                "PROTECTED_FEATURE_OUTCOME_OR_METRIC_ACCESS",
                                extra={"signal_kind": "PROTECTED_FEATURE_TAMPER"},
                            )
                        )
    else:
        literals = _literal_assignments(path.read_text(encoding="utf-8"))
        record["literals"] = literals
        for item in literals:
            if item.get("kind") != "season_assignment":
                continue
            assignment_row = _assignment_row(
                repo_root,
                int(item["season"]),
                str(item["assignment"]),
                extra={"lineno": item["lineno"]},
            )
            record["assignments"].append(assignment_row)
            if assignment_row["contradiction"]:
                record["contradictions"].append(assignment_row)
    historical = historical_surface_entry(relative)
    if path.suffix == ".py" and (record["contradictions"] or record["exposed_results"]):
        record["disposition"] = "CODE_RECORDS_PROTECTED_DEVELOPMENT_ASSIGNMENT"
    elif record["contradictions"] or record["exposed_results"]:
        record["disposition"] = (
            CONTAMINATION_STATUS if historical else "CURRENT_PROTECTED_DEVELOPMENT_EXPOSURE"
        )
    elif any(signal.get("kind") == "PROTECTED_FEATURE_ONLY" for signal in record.get("authority_signals", [])):
        record["disposition"] = "PROTECTED_FEATURE_ONLY_NO_OUTCOMES_OR_METRICS"
    elif historical:
        record["disposition"] = "HISTORICAL_SURFACE_NO_CURRENT_CONTRADICTION"
    else:
        record["disposition"] = "NO_PROTECTED_EXPOSURE"
    if historical:
        record["historical_allowlist"] = {
            "path": historical["path"],
            "decision_unit": historical.get("decision_unit"),
            "successor_path": historical.get("successor_path"),
            "preserved_as": historical.get("preserved_as"),
        }
    return record


def _surface_is_relevant(record: dict[str, Any]) -> bool:
    return bool(
        record.get("contradictions")
        or record.get("exposed_results")
        or record.get("authority_signals")
        or historical_surface_entry(record.get("path"))
        or any(
            item.get("season") in PROTECTED_SEASONS
            for item in record.get("assignments", [])
        )
    )


def build_audit(repo_root: Path) -> dict[str, Any]:
    inventory = discover_candidate_paths(repo_root)
    scanned = [audit_surface(repo_root, relative) for relative in inventory]
    surfaces = [record for record in scanned if _surface_is_relevant(record)]
    exposed_results = [item for surface in surfaces for item in surface.get("exposed_results", [])]
    contradictions = [item for surface in surfaces for item in surface.get("contradictions", [])]
    successor_paths = (
        SUCCESSOR_CONTRACT_RELATIVE,
        "configs/historical_play_drive_pit_aggregate_development_safe_contract.json",
        "configs/historical_play_drive_pit_extension_development_safe_contract.json",
    )
    for successor_relative in successor_paths:
        successor = repo_root / successor_relative
        successor_payload = _load_json(successor)
        successor_errors = validate_current_contract(
            repo_root,
            successor_payload,
            relative_path=successor_relative,
        )
        if successor_errors:
            raise ValueError(f"successor contract {successor_relative} is not current-safe: {successor_errors}")
    historical_allowlist = []
    for entry in HISTORICAL_SURFACE_ALLOWLIST:
        item = dict(entry)
        path = repo_root / entry["path"]
        item["current_sha256"] = sha256_file(path) if path.is_file() else None
        if entry in HISTORICAL_CONTRACT_ALLOWLIST or entry["path"] in {
            row["path"] for row in HISTORICAL_CONTRACT_ALLOWLIST
        }:
            contract_entry = next(
                (row for row in HISTORICAL_CONTRACT_ALLOWLIST if row["path"] == entry["path"]),
                None,
            )
            if contract_entry is not None:
                item["expected_sha256"] = contract_entry["expected_sha256"]
                item["identity_match"] = item["current_sha256"] == contract_entry["expected_sha256"]
        historical_allowlist.append(item)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "PROTECTED_SPLIT_EXPOSURE_AUDIT",
        "decision_unit": "POST-SUBTASK-169",
        "jira_key": "BAT-526",
        "registry_path": "governance/PROTECTED_SPLIT_REGISTRY.csv",
        "registry_sha256": registry_sha256(repo_root),
        "registry_unaltered": True,
        "classification": CONTAMINATION_STATUS,
        "discovered_inventory": inventory,
        "surfaces": surfaces,
        "surface_count": len(surfaces),
        "contradiction_count": len(contradictions),
        "exposed_result_count": len(exposed_results),
        "exposed_results": exposed_results,
        "authority_revoked_for": list(AUTHORITY_DENIALS),
        "successor_contract": SUCCESSOR_CONTRACT_RELATIVE,
        "successor_contract_sha256": sha256_file(successor),
        "historical_contracts_preserved": [entry["path"] for entry in HISTORICAL_CONTRACT_ALLOWLIST],
        "historical_allowlist": historical_allowlist,
        "protected_nonclaims": {
            "replacement_protected_period_defined": False,
            "protected_split_registry_altered": False,
            "historical_metrics_deleted": False,
            "selection_or_promotion_authority_granted": False,
            "protected_outcomes_used_for_development": False,
        },
        "acceptance": {
            "contradiction_contained": True,
            "historical_evidence_retained": True,
            "successor_contract_authoritative": True,
            "independent_reconstruction_required": True,
            "self_exemption_rejected": True,
        },
    }
    payload["artifact_identity"] = compute_artifact_identity(payload)
    return payload


def _compare_field(expected: Any, actual: Any, field: str, errors: list[str]) -> None:
    if expected != actual:
        errors.append(f"audit field {field} does not match independent reconstruction")


def validate_audit(
    payload: dict[str, Any],
    repo_root: Path | None = None,
    *,
    expected: dict[str, Any] | None = None,
) -> None:
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
    if int(payload.get("exposed_result_count") or 0) < 1:
        raise ValueError("audit must record exposed historical protected results")
    if int(payload.get("surface_count") or 0) != len(payload.get("surfaces") or []):
        raise ValueError("surface_count must be derived from surfaces")
    if int(payload.get("contradiction_count") or 0) != sum(
        len(surface.get("contradictions") or []) for surface in payload.get("surfaces") or []
    ):
        raise ValueError("contradiction_count must be derived from surface contradictions")
    if int(payload.get("exposed_result_count") or 0) != len(payload.get("exposed_results") or []):
        raise ValueError("exposed_result_count must be derived from exposed_results")
    if not payload.get("surfaces"):
        raise ValueError("audit surfaces cannot be empty")
    if not payload.get("exposed_results"):
        raise ValueError("audit exposed_results cannot be empty")
    omitted = [
        entry["path"]
        for entry in HISTORICAL_SURFACE_ALLOWLIST
        if entry["path"] not in {surface.get("path") for surface in payload.get("surfaces") or []}
    ]
    if omitted:
        raise ValueError(f"audit omitted required historical surfaces: {omitted}")
    if repo_root is None and expected is None:
        return
    if expected is None:
        if repo_root is None:
            raise ValueError("independent reconstruction requires repo_root")
        expected = build_audit(repo_root)
    errors: list[str] = []
    for field in AUTHORITY_BEARING_FIELDS:
        _compare_field(expected.get(field), payload.get(field), field, errors)
    if expected.get("artifact_identity") != payload.get("artifact_identity"):
        errors.append("recomputed artifact_identity does not match independently rebuilt audit")
    current_exposures = {
        surface["path"]
        for surface in expected["surfaces"]
        if surface.get("disposition") == "CURRENT_PROTECTED_DEVELOPMENT_EXPOSURE"
        and (
            surface["path"].startswith("configs/")
            or surface["path"].startswith("artifacts/")
        )
    }
    if current_exposures:
        errors.append(f"current contracts retain protected development authority: {sorted(current_exposures)}")
    if errors:
        raise ValueError("; ".join(errors))


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
        validate_audit(payload, repo_root)
        print(json.dumps({"result": "PASS", "path": str(path), "artifact_identity": payload["artifact_identity"]}))
        return 0
    payload = build_audit(repo_root)
    validate_audit(payload, repo_root)
    if args.write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"result": "PASS", "path": str(path), "artifact_identity": payload["artifact_identity"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
