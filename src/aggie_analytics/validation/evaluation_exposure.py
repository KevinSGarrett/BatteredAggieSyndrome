from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


EXPOSED_SEASONS = {2024, 2025}
FORBIDDEN_EXPOSED_STATUSES = {
    "UNTOUCHED_PROTECTED",
    "SPLIT_PROTECTED",
    "PROTECTED_PROMOTION_ELIGIBLE",
}
EXPOSED_STATUS = "DEVELOPMENT_UNPROTECTED_EXPOSED"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _season_mentions(value: Any) -> set[int]:
    found: set[int] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.update(_season_mentions(str(key)))
            found.update(_season_mentions(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_season_mentions(item))
    elif isinstance(value, int) and value in EXPOSED_SEASONS:
        found.add(value)
    elif isinstance(value, str):
        for season in EXPOSED_SEASONS:
            if str(season) in value:
                found.add(season)
    return found


def _model_identities(manifest: dict[str, Any]) -> list[str]:
    identities = {
        str(row["model_identity"])
        for row in manifest.get("models", [])
        if isinstance(row, dict) and row.get("model_identity")
    }
    value = manifest.get("model_identities")
    if isinstance(value, dict):
        identities.update(str(item) for item in value.values() if isinstance(item, str))
    elif isinstance(value, list):
        identities.update(str(item) for item in value if isinstance(item, str))
    return sorted(identities)


def _decision_families(path: Path, manifest: dict[str, Any]) -> list[str]:
    lane = path.parent.parent.parent.name.upper()
    lane_families = {
        "PRELIMINARY_UNPROTECTED": {
            "DF-NATIONAL-BASELINE-LADDER",
            "DF-ELO-RATING-AND-CALIBRATION",
            "DF-TEAM-OUTCOME-PRIOR-FEATURES",
            "DF-TREE-ADMISSION",
            "DF-CALIBRATION-METHODS",
            "DF-METRIC-AND-SLICE-SELECTION",
        },
        "PRELIMINARY_EVENT_CHRONOLOGY": {
            "DF-NATIONAL-BASELINE-LADDER",
            "DF-ELO-RATING-AND-CALIBRATION",
            "DF-EVENT-CHRONOLOGY-AND-SPLITS",
            "DF-CALIBRATION-METHODS",
            "DF-METRIC-AND-SLICE-SELECTION",
        },
        "PRELIMINARY_PLAY_DRIVE_AUGMENTED": {
            "DF-PLAY-DRIVE-STACKERS",
            "DF-TREE-ADMISSION",
            "DF-METRIC-AND-SLICE-SELECTION",
        },
        "PRELIMINARY_DENSE_PLAY_DRIVE_REPLAY": {
            "DF-DENSE-PLAY-DRIVE",
            "DF-PLAY-DRIVE-STACKERS",
            "DF-METRIC-AND-SLICE-SELECTION",
        },
        "PRELIMINARY_PLAY_ENRICHMENT_REPLAY": {
            "DF-PLAY-ENRICHMENT",
            "DF-PLAY-DRIVE-STACKERS",
            "DF-METRIC-AND-SLICE-SELECTION",
        },
        "PRELIMINARY_WMT_TAMU_SHADOW": {
            "DF-A_AND_M-WMT-SPECIALIZATION",
            "DF-A_AND_M-NO-ADJUSTMENT",
            "DF-METRIC-AND-SLICE-SELECTION",
        },
    }
    families = {lane, "PRELIMINARY_MODEL_DEVELOPMENT", *lane_families.get(lane, set())}
    families.update(
        str(row.get("family"))
        for row in manifest.get("models", [])
        if isinstance(row, dict) and row.get("family")
    )
    if lane == "PRELIMINARY_UNPROTECTED" and "rankings" in str(manifest.get("run_version", "")).lower():
        families.add("DF-AP-RANKINGS-FEATURES")
    if any("elo" in family.lower() for family in families):
        families.add("ELO_REFERENCE_AND_CHALLENGER_STRATEGY")
    return sorted(families)


def discover_exposed_runs(data_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    manifests_root = data_root / "manifests"
    for path in sorted(manifests_root.glob("preliminary_*/sha256/*/run_manifest.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        classification = str(manifest.get("classification", ""))
        if not classification.startswith("PRELIMINARY_UNPROTECTED"):
            continue
        exposed = sorted(_season_mentions({"metrics": manifest.get("metrics"), "population": manifest.get("population")}))
        if not exposed:
            continue
        records.append(
            {
                "source_manifest_path": str(path.resolve()),
                "source_manifest_sha256": sha256_file(path),
                "run_identity": manifest.get("run_identity"),
                "dataset_identity": manifest.get("dataset_identity"),
                "feature_identity": manifest.get("feature_identity"),
                "target_identity": manifest.get("target_identity"),
                "split_identity": manifest.get("split_identity"),
                "forecast_identity": manifest.get("forecast_identity"),
                "model_identities": _model_identities(manifest),
                "exposed_seasons": exposed,
                "decision_families": _decision_families(path, manifest),
                "feedback_channels": [
                    "OUTCOME_METRIC_INSPECTION",
                    "MODEL_COMPARISON",
                    "ADOPTION_OR_REJECTION_FEEDBACK",
                ],
                "prompt_identities": [],
                "prompt_disposition": "NOT_APPLICABLE_DETERMINISTIC_PRELIMINARY_RUN",
                "eligibility": EXPOSED_STATUS,
            }
        )
    return records


def build_ledger(data_root: Path) -> dict[str, Any]:
    records = discover_exposed_runs(data_root)
    payload = {
        "schema_version": "1.0.0",
        "artifact_type": "EVALUATION_CONTAMINATION_EXPOSURE_LEDGER",
        "classification": "SCIENTIFIC_GOVERNANCE",
        "exposed_seasons": sorted(EXPOSED_SEASONS),
        "records": records,
        "record_count": len(records),
        "decision_level_isolation": "REQUIRED",
        "original_protected_seals": "PRESERVED_UNCHANGED_AS_HISTORICAL_GOVERNANCE_EVIDENCE",
        "next_untouched_population": {
            "population": "FORECAST_FIRST_2026_PLUS",
            "status": "PENDING_FUTURE_OUTCOME_ACCRUAL_AND_IMMUTABLE_PREFLIGHT_SEAL",
        },
        "eligibility_decision": {
            "2024_2025": EXPOSED_STATUS,
            "limited_uses": [
                "pipeline integration",
                "chronological replay",
                "development diagnostics",
                "preliminary unprotected comparison",
            ],
            "protected_performance_claim": "PROHIBITED",
        },
    }
    payload["ledger_identity"] = hashlib.sha256(canonical_json(payload)).hexdigest()
    return payload


def validate_ledger(ledger: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    identity = ledger.get("ledger_identity")
    body = dict(ledger)
    body.pop("ledger_identity", None)
    if identity != hashlib.sha256(canonical_json(body)).hexdigest():
        failures.append("ledger_identity")
    if not ledger.get("records"):
        failures.append("records_empty")
    seen: set[str] = set()
    for index, record in enumerate(ledger.get("records", [])):
        prefix = f"record[{index}]"
        run_identity = record.get("run_identity")
        if not run_identity or run_identity in seen:
            failures.append(f"{prefix}:run_identity")
        seen.add(str(run_identity))
        path = Path(str(record.get("source_manifest_path", "")))
        if not path.is_file() or sha256_file(path) != record.get("source_manifest_sha256"):
            failures.append(f"{prefix}:source_manifest")
        if not set(record.get("exposed_seasons", [])).issubset(EXPOSED_SEASONS):
            failures.append(f"{prefix}:exposed_seasons")
        if record.get("eligibility") != EXPOSED_STATUS:
            failures.append(f"{prefix}:eligibility")
    return failures


def validate_claims(claims: Iterable[dict[str, Any]], ledger: dict[str, Any]) -> list[str]:
    exposed_artifacts: set[str] = set()
    exposed_families: set[str] = set()
    for record in ledger.get("records", []):
        for field in (
            "run_identity",
            "dataset_identity",
            "feature_identity",
            "target_identity",
            "split_identity",
            "forecast_identity",
        ):
            if record.get(field):
                exposed_artifacts.add(str(record[field]))
        exposed_artifacts.update(str(item) for item in record.get("model_identities", []))
        exposed_families.update(str(item) for item in record.get("decision_families", []))
    failures: list[str] = []
    for index, claim in enumerate(claims):
        inherited = {str(item) for item in claim.get("derived_from", [])}
        affected = (
            str(claim.get("artifact_identity", "")) in exposed_artifacts
            or str(claim.get("decision_family", "")) in exposed_families
            or bool(inherited & exposed_artifacts)
            or bool(set(claim.get("inspected_seasons", [])) & EXPOSED_SEASONS)
        )
        if affected and claim.get("evaluation_status") in FORBIDDEN_EXPOSED_STATUSES:
            failures.append(f"claim[{index}]:exposed_as_untouched_protected")
    return failures
