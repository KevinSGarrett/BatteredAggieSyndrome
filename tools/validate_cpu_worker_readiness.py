from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "artifacts/assistive/cpu_worker_readiness.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    findings: list[str] = []
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    external = Path(summary["external_readiness_path"])
    if not external.is_file() or sha256(external) != summary["external_readiness_sha256"]:
        findings.append("CPU_WORKER_EXTERNAL_READINESS_IDENTITY_INVALID")
    else:
        evidence = json.loads(external.read_text(encoding="utf-8"))
        if evidence["peer"]["dns_name"] != summary["exact_identity"]["worker_dns_name"]:
            findings.append("CPU_WORKER_DNS_IDENTITY_MISMATCH")
        if evidence["peer"].get("node_id") is None:
            findings.append("CPU_WORKER_NODE_IDENTITY_MISSING")
        if evidence["canonical_writes"] or evidence["protected_decisions"]:
            findings.append("CPU_WORKER_AUTHORITY_BOUNDARY_VIOLATION")
    implemented = summary["implemented_candidate"]
    if implemented["deployment_state"] != "PROTOTYPE_DISABLED_PENDING_CORRECTED_ARCHITECTURE":
        findings.append("CPU_WORKER_PROTOTYPE_NOT_RETIRED")
    if summary["readiness_disposition"] != "BLOCKED_CORRECTED_ARCHITECTURE_REQUIRED":
        findings.append("CPU_WORKER_PREMATURE_OPERATIONAL_CLAIM")
    if implemented["arbitrary_path_or_shell_execution"] or implemented["public_exposure"]:
        findings.append("CPU_WORKER_SECURITY_POLICY_INVALID")
    qualification = Path(summary["external_qualification_path"])
    if not qualification.is_file() or sha256(qualification) != summary["external_qualification_sha256"]:
        findings.append("CPU_WORKER_EXTERNAL_QUALIFICATION_IDENTITY_INVALID")
    else:
        result = json.loads(qualification.read_text(encoding="utf-8"))
        if result["qualification_disposition"] != "PASS":
            findings.append("CPU_WORKER_HISTORICAL_PROTOTYPE_EVIDENCE_INVALID")
        if not all(item["byte_identical_replay"] for item in result["tranches"]):
            findings.append("CPU_WORKER_REPLAY_NOT_BYTE_IDENTICAL")
        if result["restart_evidence"]["restart_recovery"] != "PASS":
            findings.append("CPU_WORKER_RESTART_RECOVERY_NOT_PASS")
        if result["canonical_writes"] or result["protected_decisions"]:
            findings.append("CPU_WORKER_QUALIFICATION_AUTHORITY_VIOLATION")
    if findings:
        print(json.dumps({"status": "FAIL", "findings": findings}, indent=2))
        return 1
    print(json.dumps({
        "status": "PASS",
        "worker_online": True,
        "operational_state": "BLOCKED_PARTIAL",
        "prototype_disabled": True,
        "historical_prototype_mechanics": "PASS_PRESERVED_NOT_CURRENT_QUALIFICATION",
        "canonical_writes": 0,
        "protected_decisions": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
