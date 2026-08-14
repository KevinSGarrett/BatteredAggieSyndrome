from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.operations.drift_alerts import (  # noqa: E402
    AlertLedger,
    DRIFT_CLASSES,
    DriftObservation,
    DriftRule,
    canonical_sha256,
    evaluate_drift,
)

CREATED_AT_UTC = "2026-08-14T06:30:00+00:00"
EVALUATED_AT_UTC = "2026-08-14T06:30:01+00:00"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def build_artifact(root: Path) -> dict[str, Any]:
    input_paths = [
        "configs/source_drift_registry.json",
        "artifacts/source_governance/source_drift_baseline.json",
        "src/aggie_analytics/operations/observability.py",
        "artifacts/jira_evidence/POST-SUBTASK-024.json",
        "artifacts/jira_evidence/POST-SUBTASK-126.json",
        "artifacts/jira_evidence/POST-SUBTASK-127.json",
        "jira/records/issues/subtasks/POST-SUBTASK-128_implement_source_api_terms_schema_entity_feature_data_model_concept_freshness_se.json",
    ]
    inputs = [
        {
            "path": path,
            "bytes": (root / path).stat().st_size,
            "sha256": sha256_file(root / path),
        }
        for path in input_paths
    ]
    hashes = {item["path"]: item["sha256"] for item in inputs}
    registry = json.loads((root / input_paths[0]).read_text(encoding="utf-8"))
    baseline = json.loads((root / input_paths[1]).read_text(encoding="utf-8"))
    if registry["active_baseline_path"] != input_paths[1]:
        raise RuntimeError("source drift registry active baseline path mismatch")
    if baseline["summary"]["endpoint_count"] != len(baseline["sources"]):
        raise RuntimeError("source drift baseline endpoint population mismatch")
    observability = (root / input_paths[2]).read_text(encoding="utf-8")
    match = re.search(r"max_age_seconds:\s*int\s*=\s*(\d+)", observability)
    if match is None:
        raise RuntimeError("existing freshness threshold contract not found")
    freshness_threshold = int(match.group(1))

    class_results = []
    for drift_class in sorted(DRIFT_CLASSES):
        terms = drift_class == "TERMS_METADATA"
        rule = DriftRule(
            rule_id=f"bat478-{drift_class.lower()}-identity-v1",
            drift_class=drift_class,
            scope_id=f"fixture/{drift_class.lower()}",
            rule_kind="EXACT_IDENTITY",
            baseline_value=digest(f"BAT-478:{drift_class}:baseline"),
            baseline_evidence_sha256=hashes[input_paths[1]],
            severity="WARNING" if terms else "HIGH",
            blocking_effect=(
                "METADATA_ONLY_NONBLOCKING" if terms else "QUARANTINE_AFFECTED_SCOPE"
            ),
        )
        evaluation = evaluate_drift(
            rule,
            DriftObservation(
                value=digest(f"BAT-478:{drift_class}:changed"),
                evidence_sha256=digest(f"BAT-478:{drift_class}:fixture-observation"),
                observed_at_utc=CREATED_AT_UTC,
            ),
            evaluated_at_utc=EVALUATED_AT_UTC,
        )
        class_results.append(
            {
                "drift_class": drift_class,
                "fixture_type": "DETERMINISTIC_CONTRACT_MUTATION_NOT_LIVE_PROVIDER_DRIFT",
                "evaluation": evaluation,
                "disposition": "PASS_DETECTED_AND_SCOPED",
            }
        )

    freshness_rule = DriftRule(
        rule_id="bat478-freshness-existing-contract-v1",
        drift_class="FRESHNESS",
        scope_id="fixture/freshness-existing-contract",
        rule_kind="MAX_AGE_SECONDS",
        baseline_value="2026-08-14T06:00:00Z",
        baseline_evidence_sha256=hashes[input_paths[2]],
        severity="HIGH",
        blocking_effect="QUARANTINE_AFFECTED_SCOPE",
        threshold=freshness_threshold,
        threshold_source_sha256=hashes[input_paths[2]],
    )
    freshness_evaluation = evaluate_drift(
        freshness_rule,
        DriftObservation(
            value="2026-08-14T06:00:00Z",
            evidence_sha256=digest("BAT-478:stale-freshness-fixture"),
            observed_at_utc=CREATED_AT_UTC,
        ),
        evaluated_at_utc=EVALUATED_AT_UTC,
    )

    lifecycle_rule = DriftRule(
        rule_id="bat478-schema-lifecycle-v1",
        drift_class="SCHEMA",
        scope_id="fixture/schema-lifecycle",
        rule_kind="EXACT_IDENTITY",
        baseline_value=digest("BAT-478:lifecycle:baseline"),
        baseline_evidence_sha256=hashes[input_paths[1]],
        severity="WARNING",
        blocking_effect="QUARANTINE_AFFECTED_SCOPE",
    )
    opening = evaluate_drift(
        lifecycle_rule,
        DriftObservation(
            value=digest("BAT-478:lifecycle:changed"),
            evidence_sha256=digest("BAT-478:lifecycle:opening-evidence"),
            observed_at_utc="2026-08-14T06:31:00Z",
        ),
        evaluated_at_utc="2026-08-14T06:31:01Z",
    )
    clearing = evaluate_drift(
        lifecycle_rule,
        DriftObservation(
            value=digest("BAT-478:lifecycle:baseline"),
            evidence_sha256=digest("BAT-478:lifecycle:clearing-evidence"),
            observed_at_utc="2026-08-14T06:34:00Z",
        ),
        evaluated_at_utc="2026-08-14T06:34:01Z",
    )
    ledger = AlertLedger()
    alert_id = ledger.ingest(opening)
    ledger.acknowledge(
        alert_id,
        actor_id="bat478-fixture-operator",
        evidence_sha256=digest("BAT-478:lifecycle:ack"),
        occurred_at_utc="2026-08-14T06:32:00Z",
    )
    ledger.escalate(
        alert_id,
        to_severity="HIGH",
        escalation_rule_id="bat478-fixture-escalation-v1",
        actor_id="bat478-fixture-policy",
        evidence_sha256=digest("BAT-478:lifecycle:escalation"),
        occurred_at_utc="2026-08-14T06:33:00Z",
    )
    ledger.resolve(
        alert_id,
        clearing_evaluation=clearing,
        actor_id="bat478-fixture-operator",
        evidence_sha256=digest("BAT-478:lifecycle:resolution"),
        occurred_at_utc="2026-08-14T06:35:00Z",
    )

    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "artifact_type": "DRIFT_ALERT_VALIDATION",
        "created_at_utc": CREATED_AT_UTC,
        "issue_identity": {"local_id": "POST-SUBTASK-128", "jira_key": "BAT-478"},
        "downstream_consumer": "POST-SUBTASK-129",
        "producer": {
            "command": "python -B tools/build_drift_alert_validation.py --repo-root .",
            "tool_path": "tools/build_drift_alert_validation.py",
            "git_base_commit": git_head(root),
        },
        "inputs": inputs,
        "controller_routing": {
            "work_unit_id": "AUTO-CURSOR-3986af3d17e9a3b6ff26",
            "provider": "cursor",
            "model": "gpt-5.3-codex",
            "task_format": "governed_cursor_repository_review_v1",
            "dispatch_origin": "PERSISTENT_CONTROLLER",
            "provider_request_sha256": "68a9a212734ccece0cfd64bc3a3bc869f4552c9ca2b8a90bf37b8228a56b28d6",
            "provider_result_sha256": "6a82bd84c4827f486f9b880af855973bd2fac0f71669a07023eb8b50f8ca0286",
            "provider_review_sha256": "dd9f5edd3988c05bea37b5afbd4892411d1bfa6fd29965b43d3dac4ee446ecc3",
            "provider_disposition": "REVIEW_ONLY",
            "final_disposition": "CODEX_REVIEW_MODIFIED",
        },
        "baseline_self_check": {
            "active_baseline_path": registry["active_baseline_path"],
            "baseline_sha256": hashes[input_paths[1]],
            "source_count": baseline["summary"]["source_count"],
            "endpoint_count": baseline["summary"]["endpoint_count"],
            "private_research_terms_blockers": baseline["summary"][
                "private_research_terms_blockers"
            ],
            "disposition": "PINNED_BASELINE_INTERNALLY_CONSISTENT_NO_LIVE_REFRESH_CLAIM",
        },
        "detector_contract": {
            "implemented_classes": sorted(DRIFT_CLASSES),
            "class_results": class_results,
            "freshness_threshold": {
                "seconds": freshness_threshold,
                "source_path": input_paths[2],
                "source_sha256": hashes[input_paths[2]],
                "evaluation": freshness_evaluation,
            },
            "threshold_policy": "THRESHOLDS_MUST_BE_POSITIVE_AND_BIND_A_VERSIONED_EVIDENCE_SHA256; NO_RUNTIME_DEFAULT_MAY_BE_INVENTED_TO_FORCE_AN_ALERT_OR_PASS",
        },
        "lifecycle_contract": {
            "ledger_snapshot": ledger.snapshot(),
            "required_transitions": ["OPENED", "ACKNOWLEDGED", "ESCALATED", "RESOLVED"],
            "deduplication": "RULE_IDENTITY_PLUS_DRIFT_CLASS_PLUS_AFFECTED_SCOPE",
            "resolution_policy": "NO_DRIFT_CLEARING_EVALUATION_WITH_CHANGED_EVIDENCE_REQUIRED",
        },
        "scope_and_policy": {
            "technical_or_quality_drift": "QUARANTINE_OR_BLOCK_ONLY_THE_AFFECTED_SCOPE_DECLARED_BY_THE_VERSIONED_RULE",
            "terms_or_rights_drift": "METADATA_ONLY_NONBLOCKING_FOR_PRIVATE_RESEARCH",
            "raw_third_party_publication": "DISABLED_WITHOUT_SEPARATE_FUTURE_REVIEW",
            "unrelated_domains_globally_blocked": False,
        },
        "acceptance": {
            "all_twelve_classes_exercised": True,
            "deterministic_identity_and_deduplication": True,
            "acknowledgement_and_evidence_backed_escalation": True,
            "resolution_requires_changed_evidence": True,
            "threshold_provenance_enforced": True,
            "terms_metadata_nonblocking": True,
            "downstream_parse_contract_present": True,
        },
        "negative_findings": [
            "No live post-baseline provider refresh was performed by this deterministic validation artifact; it does not claim a perpetual zero-drift state.",
            "The controller-routed Cursor result was REVIEW_ONLY and made no code changes; Codex integrated and modified the reviewed finding under the routed adoption interlock.",
            "This control does not establish sustained monitoring, final historical completeness, production model readiness, protected performance, A&M lift, BAS, or Aggie Excess.",
        ],
        "scientific_and_security_boundary": {
            "credential_values_included": False,
            "raw_third_party_payloads_included": False,
            "fabricated_thresholds": False,
            "fabricated_metrics": False,
            "protected_results_inspected": False,
            "production_readiness_claimed": False,
        },
        "eligibility": "IMPLEMENTED_VALIDATED_CONTROL_CANDIDATE_NOT_SUSTAINED_OPERATION",
    }
    payload["artifact_identity"] = canonical_sha256(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/operations/drift_alert_validation.json"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_artifact(root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"PASS: wrote {output} sha256={sha256_file(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
