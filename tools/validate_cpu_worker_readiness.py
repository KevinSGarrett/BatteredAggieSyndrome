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
    readiness = Path(summary["external_readiness_path"])
    qualification = Path(summary["external_qualification_path"])
    if not readiness.is_file() or sha256(readiness) != summary["external_readiness_sha256"]:
        findings.append("CPU_WORKER_EXTERNAL_READINESS_IDENTITY_INVALID")
    if not qualification.is_file() or sha256(qualification) != summary["external_qualification_sha256"]:
        findings.append("CPU_WORKER_EXTERNAL_QUALIFICATION_IDENTITY_INVALID")
        result = None
    else:
        result = json.loads(qualification.read_text(encoding="utf-8"))
    if summary["readiness_disposition"] != "QUALIFIED_CANDIDATE_DETERMINISTIC_ONLY":
        findings.append("CPU_WORKER_QUALIFIED_CANDIDATE_STATE_MISSING")
    deployment = summary["deployment"]
    if not deployment["loopback_only"] or deployment["public_funnel"]:
        findings.append("CPU_WORKER_PRIVATE_TRANSPORT_INVALID")
    if deployment["service_identity"] != "NT AUTHORITY\\LOCAL SERVICE" or deployment["run_level"] != "Limited":
        findings.append("CPU_WORKER_PRIVILEGE_INVALID")
    if deployment["arbitrary_path_url_module_command_or_shell"]:
        findings.append("CPU_WORKER_ARBITRARY_EXECUTION_AUTHORITY_PRESENT")
    gates = summary["qualification"]
    required_true = [
        "completed_job_replay_after_worker_and_controller_restart",
        "interrupted_job_recovery",
        "unauthorized_request_rejection",
        "expired_packet_rejection",
        "invalid_signature_rejection",
        "corrupt_packet_rejection",
        "disk_admission",
        "result_hash_verification",
        "cleanup",
    ]
    if gates["deterministic_tranches"] < 3 or gates["byte_identical_replays"] < 3 or gates["exact_dedup_pilots"] < 1:
        findings.append("CPU_WORKER_LIVE_WORKLOAD_GATES_INCOMPLETE")
    if not all(gates[field] is True for field in required_true):
        findings.append("CPU_WORKER_LIVE_SECURITY_OR_RECOVERY_GATE_INCOMPLETE")
    if gates["canonical_writes"] or gates["protected_decisions"]:
        findings.append("CPU_WORKER_AUTHORITY_BOUNDARY_VIOLATION")
    if result is not None:
        if result["qualification_disposition"] != "PASS":
            findings.append("CPU_WORKER_QUALIFICATION_NOT_PASS")
        if len(result["tranches"]) < 3 or not all(item["byte_identical_replay"] for item in result["tranches"]):
            findings.append("CPU_WORKER_EXTERNAL_REPLAY_INVALID")
        if result["canonical_writes"] or result["protected_decisions"]:
            findings.append("CPU_WORKER_EXTERNAL_AUTHORITY_VIOLATION")
    if findings:
        print(json.dumps({"status": "FAIL", "findings": findings}, indent=2))
        return 1
    print(json.dumps({
        "status": "PASS",
        "worker_online": True,
        "operational_state": "QUALIFIED_CANDIDATE_DETERMINISTIC_ONLY",
        "fully_operational_claimed": False,
        "canonical_writes": 0,
        "protected_decisions": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
