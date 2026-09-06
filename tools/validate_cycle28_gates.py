"""Validate Cycle #28 required gates from materialized artifacts."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle28.assurance import ASSURANCE_LAYERS, BLOCKED_ZERO_PIT
from aggie_analytics.cycle28.coverage import REQUIRED_DOMAINS
from aggie_analytics.cycle28.decommission import validate_retired_assistive_decommission
from aggie_analytics.cycle28.topology import TRANSFER_PREPARED

ART = Path("artifacts") / "scientific_integrity" / "cycle28"
REQUIRED_FILES = (
    "WEEK1_REMAINING_GAME_CALENDAR_RECONCILIATION.json",
    "WEEK1_REMAINING_CHECKPOINT_LEDGER.json",
    "WEEK1_REMAINING_SCHEDULE_CONFLICT_FINDINGS.json",
    "WEEK1_REMAINING_OUTCOME_ACCESS_LEDGER.json",
    "CYCLE27_PREDECESSOR_RECEIPT_AUDIT.json",
    "CYCLE28_WEEK1_CONTEST_FINAL_STATES.json",
    "CYCLE28_WEEK1_SCORING_SUCCESSOR.json",
    "SCIENTIFIC_CLAIM_AND_EVIDENCE_GRAPH.json",
    "ACTIVE_PATH_DEPENDENCY_AND_INVALIDATION_GRAPH.json",
    "SCIENTIFIC_ASSURANCE_LAYER_RESULTS.json",
    "VALIDATOR_INDEPENDENCE_AUDIT.json",
    "CROSS_OUTPUT_COHERENCE_GATE.json",
    "ACTIVE_PATH_STRUCTURAL_TRUST_GATE.json",
    "SCIENTIFIC_ASSURANCE_CONTROL_PLANE_GATE.json",
    "NATIONAL_POPULATION_MANIFEST.json",
    "NATIONAL_DOMAIN_COVERAGE_GATE.json",
    "BAS_CAPABILITY_COMPLETENESS_REGISTRY.json",
    "NATIONAL_DATA_DOMAIN_SOURCE_POLICY_REGISTRY.json",
    "NATIONAL_SOURCE_ADAPTER_INVENTORY.json",
    "MODEL_REQUIRED_FIELD_COVERAGE_GATE.json",
    "NATIONAL_COACHING_COVERAGE.json",
    "NATIONAL_AVAILABILITY_SOURCE_POLICY_MATRIX.json",
    "ALL22_SNAPSHOT_INVENTORY.json",
    "GRIDIRON_CORTEX_RELEASE_BOM.json",
    "ALL22_BAS_COMPATIBILITY_MATRIX.json",
    "ALL22_CHANGE_INTAKE_AND_INVALIDATION_GATE.json",
    "BAS_REPOSITORY_TOPOLOGY_RECEIPT.json",
    "BAS_GITHUB_TRANSFER_READINESS_GATE.json",
    "CYCLE27_FINDING_ADJUDICATION_SUCCESSOR.json",
    "BAS_CFIP_CROSS_SYSTEM_JIRA_LINK_LEDGER.json",
    "CFBPROGRAMSPECIFICATIONS_BAS_GAP_AUDIT.json",
    "CFBPROGRAMSPECIFICATIONS_PLAN_UPDATE_READINESS_GATE.json",
    "BAS_CROSS_REPOSITORY_ACCEPTANCE_DAG.json",
    "PAID_REVIEW_COST_LEDGER.json",
)


def load(root: Path, name: str) -> dict:
    path = root / ART / name
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path) -> list[str]:
    findings: list[str] = []
    for name in REQUIRED_FILES:
        path = root / ART / name
        if not path.is_file():
            findings.append(f"missing {path.as_posix()}")
    if findings:
        return findings + validate_retired_assistive_decommission(root)

    calendar = load(root, "WEEK1_REMAINING_GAME_CALENDAR_RECONCILIATION.json")
    if len(calendar.get("contests") or []) != 4:
        findings.append("remaining calendar must cover exactly four Sunday/Monday contests")
    conflict = load(root, "WEEK1_REMAINING_SCHEDULE_CONFLICT_FINDINGS.json")
    wsu = (conflict.get("findings") or [{}])[0]
    if wsu.get("relabeled_early_as_t90m"):
        findings.append("early capture relabeled as T-90M")
    if wsu.get("predecessor_preserved") is not True:
        findings.append("WSU predecessor not preserved")

    pred = load(root, "CYCLE27_PREDECESSOR_RECEIPT_AUDIT.json")
    if pred.get("predecessor_deleted"):
        findings.append("predecessor receipts deleted")
    if int(pred.get("shared_materialization_timestamp_count") or 0) < 1:
        findings.append("predecessor shared timestamp count missing")

    finals = load(root, "CYCLE28_WEEK1_CONTEST_FINAL_STATES.json")
    if int(finals.get("contest_count") or 0) != 91:
        findings.append(f"Week 1 contest count {finals.get('contest_count')} != 91")
    if finals.get("tuning_from_week1_outcomes") or finals.get("backfill"):
        findings.append("Week 1 outcomes used to tune or backfill")

    scoring = load(root, "CYCLE28_WEEK1_SCORING_SUCCESSOR.json")
    if scoring.get("a_and_m_hardcoded"):
        findings.append("A&M result hardcoded")
    if scoring.get("oriented_rows_counted_as_games"):
        findings.append("oriented rows counted as games")
    if scoring.get("independent_predicted_score") is not None:
        findings.append("independent_predicted_score must remain null")

    graph = load(root, "SCIENTIFIC_CLAIM_AND_EVIDENCE_GRAPH.json")
    if int(graph.get("unmapped_authority_bearing_claims") or 0) != 0:
        findings.append("unmapped authority-bearing claims")
    layers = load(root, "SCIENTIFIC_ASSURANCE_LAYER_RESULTS.json")
    missing_layers = [layer for layer in ASSURANCE_LAYERS if layer not in (layers.get("layers") or {})]
    if missing_layers:
        findings.append(f"assurance layers omitted: {missing_layers}")

    trust = load(root, "ACTIVE_PATH_STRUCTURAL_TRUST_GATE.json")
    if trust.get("scientific_trust_recovered"):
        findings.append("scientific_trust_recovered set true")
    if trust.get("r26_22") != BLOCKED_ZERO_PIT and int(trust.get("proven_pit_training_rows") or 0) == 0:
        findings.append("empty PIT matrix not blocked")

    indep = load(root, "VALIDATOR_INDEPENDENCE_AUDIT.json")
    if indep.get("imports_producer_scoring_helpers"):
        findings.append("independent reference imports producer scoring helpers")
    reference = root / "src" / "aggie_analytics" / "scientific_reference" / "cycle28_scoring.py"
    tree = ast.parse(reference.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    if any(name.startswith("aggie_analytics.cycle28.scoring") for name in imported):
        findings.append("cycle28_scoring imports producer scoring module")

    cap = load(root, "BAS_CAPABILITY_COMPLETENESS_REGISTRY.json")
    present = {row["domain"] for row in cap.get("domains") or []}
    omitted = [domain for domain in REQUIRED_DOMAINS if domain not in present]
    if omitted:
        findings.append(f"capability domain omitted: {omitted}")

    coaching = load(root, "NATIONAL_COACHING_COVERAGE.json")
    if coaching.get("play_caller_inferred_from_coordinator"):
        findings.append("play caller inferred from coordinator")
    if coaching.get("am_only_labeled_national"):
        findings.append("A&M-only staff labeled national")
    if coaching.get("model_consumption") != "CANDIDATE_ONLY_NOT_CONSUMED":
        findings.append("coaching consumed without admission")

    avail = load(root, "NATIONAL_AVAILABILITY_SOURCE_POLICY_MATRIX.json")
    if avail.get("absence_means_healthy"):
        findings.append("absence represented as healthy")

    snap = load(root, "ALL22_SNAPSHOT_INVENTORY.json")
    if snap.get("disposition") not in {"DRIFTED_NOT_CONSUMABLE", "COMMISSIONED_CLEAN"}:
        findings.append("All-22 snapshot disposition missing")

    compat = load(root, "ALL22_BAS_COMPATIBILITY_MATRIX.json")
    if "GRIDIRON_CORTEX_INTEGRATED" in (compat.get("allowed_claim") or ""):
        findings.append("forbidden Gridiron integrated claim")

    topo = load(root, "BAS_REPOSITORY_TOPOLOGY_RECEIPT.json")
    if topo.get("physical_move") or topo.get("transfer_executed"):
        findings.append("unauthorized move or transfer")
    gate = load(root, "BAS_GITHUB_TRANSFER_READINESS_GATE.json")
    if gate.get("disposition") != TRANSFER_PREPARED:
        findings.append("transfer readiness disposition incorrect")
    if gate.get("transfer_authorized"):
        findings.append("transfer marked authorized")

    findings.extend(validate_retired_assistive_decommission(root))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    findings = validate(args.repo_root.resolve())
    payload = {"result": "PASS" if not findings else "FAIL", "findings": findings}
    print(json.dumps(payload, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
