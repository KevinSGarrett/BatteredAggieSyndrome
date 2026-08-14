from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.operations.drift_alerts import (  # noqa: E402
    DRIFT_CLASSES,
    canonical_sha256,
    validate_alert_snapshot,
    validate_drift_evaluation,
)
from tools.build_drift_alert_validation import sha256_file  # noqa: E402


def consume_for_post_subtask_129(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != "1.0.0":
        raise ValueError("drift validation schema mismatch")
    if payload.get("artifact_type") != "DRIFT_ALERT_VALIDATION":
        raise ValueError("drift validation artifact type mismatch")
    if payload.get("issue_identity") != {
        "local_id": "POST-SUBTASK-128",
        "jira_key": "BAT-478",
    }:
        raise ValueError("drift validation issue identity mismatch")
    if payload.get("downstream_consumer") != "POST-SUBTASK-129":
        raise ValueError("drift validation downstream consumer mismatch")
    canonical = dict(payload)
    claimed = canonical.pop("artifact_identity", None)
    if claimed != canonical_sha256(canonical):
        raise ValueError("drift validation artifact identity mismatch")
    return {
        "artifact_identity": claimed,
        "eligibility": payload["eligibility"],
        "implemented_classes": payload["detector_contract"]["implemented_classes"],
        "baseline_sha256": payload["baseline_self_check"]["baseline_sha256"],
    }


def validate(root: Path, artifact_path: Path) -> list[str]:
    findings: list[str] = []
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        consumed = consume_for_post_subtask_129(payload)
    except Exception as exc:
        return [f"ARTIFACT_REJECTED:{type(exc).__name__}:{exc}"]

    for item in payload.get("inputs", []):
        path = root / item.get("path", "")
        if not path.is_file():
            findings.append(f"INPUT_MISSING:{item.get('path')}")
        elif sha256_file(path) != item.get("sha256"):
            findings.append(f"INPUT_HASH_MISMATCH:{item.get('path')}")
    classes = payload["detector_contract"]["implemented_classes"]
    if classes != sorted(DRIFT_CLASSES):
        findings.append("DRIFT_CLASS_COVERAGE_MISMATCH")
    results = payload["detector_contract"]["class_results"]
    if [item.get("drift_class") for item in results] != sorted(DRIFT_CLASSES):
        findings.append("DRIFT_CLASS_RESULT_POPULATION_MISMATCH")
    for item in results:
        try:
            validate_drift_evaluation(item["evaluation"])
        except Exception as exc:
            findings.append(f"DRIFT_EVALUATION_INVALID:{item.get('drift_class')}:{exc}")
            continue
        if item["evaluation"]["status"] != "DRIFT":
            findings.append(f"DRIFT_FIXTURE_NOT_DETECTED:{item.get('drift_class')}")
        if (
            item["drift_class"] == "TERMS_METADATA"
            and item["evaluation"]["blocking_effect"] != "METADATA_ONLY_NONBLOCKING"
        ):
            findings.append("TERMS_METADATA_REINTRODUCES_PRIVATE_RESEARCH_GATE")

    try:
        validate_drift_evaluation(
            payload["detector_contract"]["freshness_threshold"]["evaluation"]
        )
    except Exception as exc:
        findings.append(f"FRESHNESS_EVALUATION_INVALID:{exc}")
    if payload["detector_contract"]["freshness_threshold"].get(
        "source_sha256"
    ) != sha256_file(root / "src/aggie_analytics/operations/observability.py"):
        findings.append("FRESHNESS_THRESHOLD_SOURCE_MISMATCH")
    try:
        snapshot = payload["lifecycle_contract"]["ledger_snapshot"]
        validate_alert_snapshot(snapshot)
    except Exception as exc:
        findings.append(f"LIFECYCLE_SNAPSHOT_INVALID:{exc}")
    else:
        transitions = [
            item["transition_type"] for item in snapshot["records"][0]["transitions"]
        ]
        if transitions != payload["lifecycle_contract"]["required_transitions"]:
            findings.append("LIFECYCLE_TRANSITION_SEQUENCE_MISMATCH")
        if snapshot["records"][0]["status"] != "RESOLVED":
            findings.append("LIFECYCLE_RESOLUTION_MISSING")

    baseline_path = root / payload["baseline_self_check"]["active_baseline_path"]
    if sha256_file(baseline_path) != payload["baseline_self_check"]["baseline_sha256"]:
        findings.append("ACTIVE_BASELINE_HASH_MISMATCH")
    if payload["baseline_self_check"].get("private_research_terms_blockers") != 0:
        findings.append("PRIVATE_RESEARCH_TERMS_BLOCKER_REINTRODUCED")
    if (
        payload["scope_and_policy"].get("unrelated_domains_globally_blocked")
        is not False
    ):
        findings.append("UNRELATED_DOMAIN_GLOBAL_BLOCK_REINTRODUCED")
    boundary = payload["scientific_and_security_boundary"]
    if boundary.get("credential_values_included") is not False:
        findings.append("CREDENTIAL_VALUE_EVIDENCE_FORBIDDEN")
    if boundary.get("production_readiness_claimed") is not False:
        findings.append("PRODUCTION_READINESS_OVERCLAIM")
    if (
        consumed["eligibility"]
        != "IMPLEMENTED_VALIDATED_CONTROL_CANDIDATE_NOT_SUSTAINED_OPERATION"
    ):
        findings.append("ELIGIBILITY_OVERCLAIM")

    mutation = copy.deepcopy(payload)
    mutation["scope_and_policy"]["unrelated_domains_globally_blocked"] = True
    try:
        consume_for_post_subtask_129(mutation)
    except ValueError:
        pass
    else:
        findings.append("ARTIFACT_IDENTITY_MUTATION_NOT_REJECTED")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("artifacts/operations/drift_alert_validation.json"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    artifact = args.artifact if args.artifact.is_absolute() else root / args.artifact
    findings = validate(root, artifact)
    if findings:
        print(f"FAIL: {len(findings)} drift-alert finding(s)")
        for finding in findings:
            print(f"- {finding}")
        return 1
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    print(
        f"PASS: BAT-478 drift-alert contract identity={payload['artifact_identity']} classes={len(DRIFT_CLASSES)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
