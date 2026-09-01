"""Write Cycle #25.5 routing manifests from the current worktree change set."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "c1c310da6bcae25641977fe409e3034b8c08010a"
INSTRUCTION_TEXT = (
    "USER_EXPLICIT_CURSOR_AUTHORIZATION_CYCLE_25_5\n"
    "Execute all Cycle #25.5 Scientific Trust Recovery Program work in this one "
    "Cursor session without assistive workers; retired assistive pipeline remains inactive."
)
PROCESS_JIRA = {
    "jira/project/JIRA_TARGET_PROFILE.yaml",
    "jira/reconciliation/BAT_AUXILIARY_ISSUE_REGISTRY.json",
    "jira/reconciliation/BAT_LIVE_IMPORT_LEDGER.json",
    "jira/validation/BAT_LIVE_IMPORT_VERIFICATION.json",
}
PROCESS_PROVENANCE = {
    "provenance/CURRENT_TREE.txt",
    "provenance/PROJECT_FILE_HASHES.sha256",
    "provenance/PROJECT_FILE_MANIFEST.csv",
}
PROCESS_ROUTING = {
    "configs/codex_usage_interlock_change_manifest.json",
    "configs/unified_assistive_change_routing_binding.json",
    "configs/cycle25_5_material_ownership_registry.json",
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")


def _sha(payload: dict, omit: str) -> str:
    reduced = {key: value for key, value in payload.items() if key != omit}
    return hashlib.sha256(
        json.dumps(reduced, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main() -> int:
    tracked = [
        line.strip().replace("\\", "/")
        for line in _git("diff", "--name-only", "--diff-filter=ACMRD", BASE).splitlines()
        if line.strip()
    ]
    untracked = [
        line.strip().replace("\\", "/")
        for line in _git("ls-files", "--others", "--exclude-standard").splitlines()
        if line.strip()
    ]
    extra = [
        "configs/cycle25_5_material_ownership_registry.json",
        "configs/codex_usage_interlock_change_manifest.json",
        "configs/unified_assistive_change_routing_binding.json",
        "provenance/CURRENT_TREE.txt",
        "provenance/PROJECT_FILE_HASHES.sha256",
        "provenance/PROJECT_FILE_MANIFEST.csv",
        "tools/write_cycle25_5_routing_manifests.py",
    ]
    paths = sorted(set(tracked) | set(untracked) | set(extra))
    assignments = []
    for path in paths:
        if path in PROCESS_JIRA:
            kind = "PROCESS_ONLY_JIRA_CONTROL_PLANE"
            owner = None
        elif path in PROCESS_PROVENANCE:
            kind = "PROCESS_ONLY_GENERATED_PROVENANCE"
            owner = None
        elif path in PROCESS_ROUTING:
            kind = "PROCESS_ONLY_ROUTING_INTERLOCK"
            owner = None
        else:
            kind = "MATERIAL"
            owner = "BAT-688"
        assignments.append({"kind": kind, "owner": owner, "path": path})
    registry = {
        "artifact_type": "CYCLE25_5_MATERIAL_OWNERSHIP_REGISTRY",
        "assignments": assignments,
        "owners": [
            "BAT-688",
            "BAT-689",
            "BAT-690",
            "BAT-691",
            "BAT-692",
            "BAT-693",
            "BAT-694",
            "BAT-695",
            "BAT-696",
        ],
        "schema_version": 1,
        "work_unit_id": "POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001",
    }
    (ROOT / "configs/cycle25_5_material_ownership_registry.json").write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )
    waiver = {
        "accepted_risk": (
            "Retired assistive pipeline remains inactive; protected lanes and production "
            "claims remain closed; scientific-correction merges remain forbidden while the "
            "operator hold is active; only governed project work in scoped paths is authorized."
        ),
        "duration": "UNTIL_USER_REVOKES_OR_SUPERSEDES",
        "instruction_sha256": hashlib.sha256(INSTRUCTION_TEXT.encode("utf-8")).hexdigest(),
        "instruction_text": INSTRUCTION_TEXT,
        "scope": "ALL_BATTERED_AGGIE_SYNDROME_PROJECT_WORK",
        "work_unit_id": "POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001",
    }
    binding = {
        "allowed_paths": paths,
        "artifact_type": "MATERIAL_CHANGE_PRE_ROUTING_BINDING",
        "canonical_or_protected_authority": False,
        "class": "PROJECT_WORK",
        "disposition": "USER_EXPLICITLY_RESERVED_FOR_CODEX",
        "downstream_consumer": "tools/validate_artifact_bindings.py",
        "jira_identity": "BAT-688",
        "ordinary_project_work_authorized": False,
        "reason_code": "USER_EXPLICIT_CURSOR_AUTHORIZATION_CYCLE_25_5",
        "repository_identity": "KevinSGarrett/BatteredAggieSyndrome",
        "schema_version": 1,
        "scope": (
            "Cycle #25.5 scientific-trust recovery hold, all-cycle inventory, review "
            "infrastructure, independent scientific reference, and unmerged successor modules"
        ),
        "source_commit": BASE,
        "user_explicit_waiver": waiver,
        "work_unit_id": "POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001",
    }
    binding["decision_sha256"] = _sha(binding, "decision_sha256")
    (ROOT / "configs/unified_assistive_change_routing_binding.json").write_text(
        json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "artifact_type": "CODEX_USAGE_INTERLOCK_CHANGE_MANIFEST",
        "base_commit": BASE,
        "changed_paths": paths,
        "jira_identity": "BAT-688",
        "ordinary_project_work_authorized": False,
        "pre_routing_decision_sha256": binding["decision_sha256"],
        "schema_version": 1,
        "work_class": "PROJECT_WORK",
        "work_unit_id": "POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001",
    }
    manifest["manifest_identity"] = _sha(manifest, "manifest_identity")
    (ROOT / "configs/codex_usage_interlock_change_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"path_count": len(paths), "decision": binding["decision_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
