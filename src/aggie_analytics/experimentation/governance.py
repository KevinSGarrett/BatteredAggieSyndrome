from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import csv, json


def verify_judging_rule_seal(repo_root: Path) -> list[str]:
    seal_path=repo_root/"governance/PROTECTED_JUDGING_RULE_SEAL.csv"
    findings=[]
    with seal_path.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            p=repo_root/row["path"]
            if not p.exists(): findings.append(f"missing:{row['path']}"); continue
            actual=sha256(p.read_bytes()).hexdigest()
            if actual != row["sha256"]: findings.append(f"changed:{row['path']}")
    return findings

def advanced_challenger_admission(*, candidate_class:str, baseline_empirical_evidence:bool, protocol_sealed:bool, resource_budget_declared:bool) -> str:
    if not protocol_sealed: return "BLOCKED_PROTOCOL_UNSEALED"
    if not resource_budget_declared: return "BLOCKED_RESOURCE_BUDGET_MISSING"
    if candidate_class in {"SMALL_NEURAL_TABULAR","SEQUENCE_TRANSFORMER","GRAPH_NEURAL_NETWORK"} and not baseline_empirical_evidence:
        return "BLOCKED_BASELINE_EMPIRICAL_EVIDENCE_MISSING"
    return "ADMITTED_RESEARCH_ONLY"

def hpo_objective_allowed(split_name: str) -> bool:
    return split_name in {"SPLIT-DEV-HIST","SPLIT-DEV-SEL"}
