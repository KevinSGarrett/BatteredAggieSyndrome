"""Write Cycle #25.5 routing manifests from the current worktree change set."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "516b7aeefaaf2dad4f4ef7aeba08e05497bc65f2"
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
WORK_UNITS = {
    "BAT-688": "POST-TASK-ALL-CYCLE-SCIENTIFIC-CLAIM-REGISTRY-001",
    "BAT-689": "POST-TASK-PR-REVIEW-DEFENSE-INFRASTRUCTURE-001",
    "BAT-690": "POST-TASK-NATIONAL-FOUNDATION-SCIENTIFIC-SUCCESSOR-001",
    "BAT-691": "POST-TASK-NATIONAL-MODEL-LINEAGE-CORRECTION-001",
    "BAT-692": "POST-TASK-TAMU-CORPUS-DERIVATIVE-INTEGRITY-001",
    "BAT-693": "POST-TASK-WEEK1-FORECAST-BINDING-AND-COHERENCE-SUCCESSOR-001",
    "BAT-694": "POST-TASK-MARKET-BENCHMARK-INTEGRITY-SUCCESSOR-001",
    "BAT-695": "POST-TASK-PROTECTED-EVALUATION-REPLACEMENT-PROTOCOL-001",
    "BAT-696": "POST-TASK-SCIENTIFIC-VALIDATION-INDEPENDENCE-GATE-001",
}
SCOPES = {
    "BAT-688": (
        "Cycle #25.5 operator hold, all-cycle inventory skeleton, and claim registry"
    ),
    "BAT-689": (
        "Cycle #25.5 review-infrastructure tranche stacked on hold and inventory"
    ),
    "BAT-690": (
        "Cycle #25.5 scientific correction successors stacked after review infrastructure"
    ),
}


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")


def _sha(payload: dict, omit: str) -> str:
    reduced = {key: value for key, value in payload.items() if key != omit}
    return hashlib.sha256(
        json.dumps(reduced, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def owner_for(path: str) -> str:
    if path == "AGENTS.md" or path.startswith("jira/index/SOURCE_"):
        return "BAT-689"
    if path.startswith("jira/sources/") or path.startswith("jira/validation/SOURCE_"):
        return "BAT-689"
    if path in {
        "jira/validation/JIRA_FILE_MANIFEST.csv",
        "jira/validation/JIRA_FILE_HASHES.sha256",
    }:
        return "BAT-689"
    if path.startswith(".github/") or path == ".cursor/BUGBOT.md":
        return "BAT-689"
    if path.endswith("/.cursor/BUGBOT.md") and "scientific_reference" not in path:
        return "BAT-689"
    if path in {
        "codecov.yml",
        "schemas/scientific_review/codex_scientific_review.schema.json",
        "tools/validate_codex_scientific_review.py",
        "tools/validate_pr_review_finding_ledger.py",
        "artifacts/scientific_integrity/PR_REVIEW_FINDING_LEDGER.json",
        "artifacts/scientific_integrity/USER_ADMIN_ACTION_REQUIRED.json",
        "tests/test_pr_review_defense_infrastructure.py",
    }:
        return "BAT-689"
    if path.endswith("national_foundation_status_successor.py"):
        return "BAT-690"
    if path.endswith("authority_clean_model_lineage.py"):
        return "BAT-691"
    if path.endswith("tamu_corpus_derivative_integrity_successor.py"):
        return "BAT-692"
    if path.endswith("week1_2026_current_contest_binding_successor.py"):
        return "BAT-693"
    if path.endswith("week1_2026_game_grain_distribution_successor.py"):
        return "BAT-693"
    if path.endswith("week1_2026_market_integrity_successor.py"):
        return "BAT-694"
    if "protected_evaluation_replacement" in path:
        return "BAT-695"
    if path.startswith("src/aggie_analytics/scientific_reference/"):
        return "BAT-696"
    if path in {
        "tools/validate_independent_scientific_reference.py",
        "tools/validate_cross_output_coherence.py",
        "tools/validate_raw_to_forecast_trace.py",
        "tools/validate_protected_replacement_protocol.py",
        "tests/test_independent_scientific_reference.py",
        "artifacts/scientific_integrity/INDEPENDENT_VALIDATOR_CLASSIFICATION.json",
        "artifacts/scientific_integrity/DEPRECATION_SUCCESSOR_MAP.json",
    }:
        return "BAT-696"
    return "BAT-688"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jira", default="BAT-688")
    args = parser.parse_args()
    jira = args.jira
    work_unit = WORK_UNITS[jira]
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
            owner = owner_for(path)
        assignments.append({"kind": kind, "owner": owner, "path": path})
    registry = {
        "artifact_type": "CYCLE25_5_MATERIAL_OWNERSHIP_REGISTRY",
        "assignments": assignments,
        "owners": list(WORK_UNITS),
        "schema_version": 1,
        "work_unit_id": work_unit,
    }
    (ROOT / "configs/cycle25_5_material_ownership_registry.json").write_bytes(
        (json.dumps(registry, indent=2) + "\n").encode("utf-8")
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
        "work_unit_id": work_unit,
    }
    binding = {
        "allowed_paths": paths,
        "artifact_type": "MATERIAL_CHANGE_PRE_ROUTING_BINDING",
        "canonical_or_protected_authority": False,
        "class": "PROJECT_WORK",
        "disposition": "USER_EXPLICITLY_RESERVED_FOR_CODEX",
        "downstream_consumer": "tools/validate_artifact_bindings.py",
        "jira_identity": jira,
        "ordinary_project_work_authorized": False,
        "reason_code": "USER_EXPLICIT_CURSOR_AUTHORIZATION_CYCLE_25_5",
        "repository_identity": "KevinSGarrett/BatteredAggieSyndrome",
        "schema_version": 1,
        "scope": SCOPES[jira],
        "source_commit": BASE,
        "user_explicit_waiver": waiver,
        "work_unit_id": work_unit,
    }
    binding["decision_sha256"] = _sha(binding, "decision_sha256")
    (ROOT / "configs/unified_assistive_change_routing_binding.json").write_bytes(
        (json.dumps(binding, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    manifest = {
        "artifact_type": "CODEX_USAGE_INTERLOCK_CHANGE_MANIFEST",
        "base_commit": BASE,
        "changed_paths": paths,
        "jira_identity": jira,
        "ordinary_project_work_authorized": False,
        "pre_routing_decision_sha256": binding["decision_sha256"],
        "schema_version": 1,
        "work_class": "PROJECT_WORK",
        "work_unit_id": work_unit,
    }
    manifest["manifest_identity"] = _sha(manifest, "manifest_identity")
    (ROOT / "configs/codex_usage_interlock_change_manifest.json").write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(json.dumps({"path_count": len(paths), "jira": jira, "decision": binding["decision_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
