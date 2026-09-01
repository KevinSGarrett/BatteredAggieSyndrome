"""Append Cycle #25.5 auxiliary owners to the local Jira control-plane files."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-09-01T18:30:00+00:00"
OWNERS = [
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "GOVERNANCE",
        "issue_type": "Task",
        "jira_key": "BAT-688",
        "local_id": "POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001",
        "logical_state": "IN_PROGRESS",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-1",
        "status": "In Progress",
        "summary": (
            "[POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001] Install the Cycle "
            "#25.5 operator hold and all-cycle scientific claim/artifact inventory skeleton"
        ),
    },
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "GOVERNANCE",
        "issue_type": "Task",
        "jira_key": "BAT-689",
        "local_id": "POST-TASK-PR-REVIEW-DEFENSE-INFRASTRUCTURE-001",
        "logical_state": "READY",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-1",
        "status": "To Do",
        "summary": (
            "[POST-TASK-PR-REVIEW-DEFENSE-INFRASTRUCTURE-001] Install Codex, Bugbot, "
            "Codecov, and branch-protection scientific review defenses"
        ),
    },
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "DATA_MATERIALIZATION",
        "issue_type": "Task",
        "jira_key": "BAT-690",
        "local_id": "POST-TASK-NATIONAL-FOUNDATION-SCIENTIFIC-SUCCESSOR-001",
        "logical_state": "READY",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-3",
        "status": "To Do",
        "summary": (
            "[POST-TASK-NATIONAL-FOUNDATION-SCIENTIFIC-SUCCESSOR-001] Build the "
            "national foundation scientific successor and correct the false 2011 quarantine"
        ),
    },
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "SCIENTIFIC",
        "issue_type": "Task",
        "jira_key": "BAT-691",
        "local_id": "POST-TASK-NATIONAL-MODEL-LINEAGE-CORRECTION-001",
        "logical_state": "READY",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-3",
        "status": "To Do",
        "summary": (
            "[POST-TASK-NATIONAL-MODEL-LINEAGE-CORRECTION-001] Rebuild authority-clean "
            "historical model lineage without unproven ranking or venue admission"
        ),
    },
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "DATA_MATERIALIZATION",
        "issue_type": "Task",
        "jira_key": "BAT-692",
        "local_id": "POST-TASK-TAMU-CORPUS-DERIVATIVE-INTEGRITY-001",
        "logical_state": "READY",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-3",
        "status": "To Do",
        "summary": (
            "[POST-TASK-TAMU-CORPUS-DERIVATIVE-INTEGRITY-001] Build A&M structured-corpus "
            "derivative integrity successors"
        ),
    },
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "SHARED_CONTRACT",
        "issue_type": "Task",
        "jira_key": "BAT-693",
        "local_id": "POST-TASK-WEEK1-FORECAST-BINDING-AND-COHERENCE-SUCCESSOR-001",
        "logical_state": "READY",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-3",
        "status": "To Do",
        "summary": (
            "[POST-TASK-WEEK1-FORECAST-BINDING-AND-COHERENCE-SUCCESSOR-001] Rebuild "
            "current-contest feature binding and coherent game-level forecast distributions"
        ),
    },
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "SHARED_CONTRACT",
        "issue_type": "Task",
        "jira_key": "BAT-694",
        "local_id": "POST-TASK-MARKET-BENCHMARK-INTEGRITY-SUCCESSOR-001",
        "logical_state": "READY",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-3",
        "status": "To Do",
        "summary": (
            "[POST-TASK-MARKET-BENCHMARK-INTEGRITY-SUCCESSOR-001] Rebuild market receipt, "
            "crosswalk, alias, median, and overround integrity"
        ),
    },
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "PROTECTED_GATE",
        "issue_type": "Task",
        "jira_key": "BAT-695",
        "local_id": "POST-TASK-PROTECTED-EVALUATION-REPLACEMENT-PROTOCOL-001",
        "logical_state": "READY",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-3",
        "status": "To Do",
        "summary": (
            "[POST-TASK-PROTECTED-EVALUATION-REPLACEMENT-PROTOCOL-001] Design an inactive "
            "prospective protected-evaluation replacement while retaining the blocked lane"
        ),
    },
    {
        "classification": "AUTHORIZED_AUXILIARY_LIVE_UNIT",
        "critical_path": True,
        "evidence_state": "PLANNED",
        "execution_lane": "SCIENTIFIC",
        "issue_type": "Task",
        "jira_key": "BAT-696",
        "local_id": "POST-TASK-SCIENTIFIC-VALIDATION-INDEPENDENCE-GATE-001",
        "logical_state": "READY",
        "maturity": "CONTRACT_DEFINED",
        "owner_wave": "POST_W25",
        "phase": "PHASE-3",
        "status": "To Do",
        "summary": (
            "[POST-TASK-SCIENTIFIC-VALIDATION-INDEPENDENCE-GATE-001] Install independent "
            "scientific-reference validators and adversarial mutation coverage"
        ),
    },
]


def _dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    registry_path = ROOT / "jira/reconciliation/BAT_AUXILIARY_ISSUE_REGISTRY.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    existing = {item["jira_key"] for item in registry["issues"]}
    for owner in OWNERS:
        if owner["jira_key"] not in existing:
            registry["issues"].append(owner)
    _dump(registry_path, registry)

    verification_path = ROOT / "jira/validation/BAT_LIVE_IMPORT_VERIFICATION.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    verification["auxiliary_actual_count"] = 133
    verification["auxiliary_expected_count"] = 133
    verification["auxiliary_issue_type_counts"] = {"Task": 133}
    verification["auxiliary_status_counts"] = {
        "Done": 123,
        "In Progress": 2,
        "To Do": 8,
    }
    verification["issue_count"] = 627
    verification["issue_type_counts"]["Task"] = 334
    verification["status_counts"] = {"Done": 209, "In Progress": 2, "To Do": 416}
    verification["total_actual_issue_count"] = 627
    verification["total_expected_issue_count"] = 627
    verification["total_issue_type_counts"]["Task"] = 334
    verification["total_status_counts"] = {
        "Done": 209,
        "In Progress": 2,
        "To Do": 416,
    }
    verification["verified_at"] = NOW
    _dump(verification_path, verification)

    ledger_path = ROOT / "jira/reconciliation/BAT_LIVE_IMPORT_LEDGER.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    have = {item["jira_key"] for item in ledger["auxiliary_issue_reconciliation"]}
    for owner in OWNERS:
        if owner["jira_key"] not in have:
            ledger["auxiliary_issue_reconciliation"].append(
                {
                    "jira_key": owner["jira_key"],
                    "local_id": owner["local_id"],
                    "updated_fields": ["created_live_cycle25_5"],
                    "verified_at": NOW,
                }
            )
    ledger["updated_at"] = NOW
    ledger["verification"] = verification
    _dump(ledger_path, ledger)

    profile_path = ROOT / "jira/project/JIRA_TARGET_PROFILE.yaml"
    text = profile_path.read_text(encoding="utf-8")
    text = text.replace('"issues": 618,', '"issues": 627,')
    text = text.replace(
        '"last_live_verification": "2026-09-01T05:51:13.172233+00:00"',
        f'"last_live_verification": "{NOW}"',
    )
    text = text.replace(
        '"last_successful_sync": "2026-09-01T05:51:13.172233+00:00"',
        f'"last_successful_sync": "{NOW}"',
    )
    profile_path.write_text(text, encoding="utf-8")
    print(json.dumps({"auxiliary": len(registry["issues"]), "issues": 627}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
