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
        if evidence["peer"]["tailscale_ips"][0] != summary["exact_identity"]["worker_tailscale_ipv4"]:
            findings.append("CPU_WORKER_IP_IDENTITY_MISMATCH")
        if evidence["readiness_disposition"] != summary["readiness_disposition"]:
            findings.append("CPU_WORKER_READINESS_DISPOSITION_MISMATCH")
        if evidence["canonical_writes"] or evidence["protected_decisions"]:
            findings.append("CPU_WORKER_AUTHORITY_BOUNDARY_VIOLATION")
    implemented = summary["implemented_candidate"]
    if implemented["deployment_state"] != "NOT_DEPLOYED" or summary["readiness_disposition"] != "BLOCKED_REMOTE_SETUP_OR_SERVICE_REQUIRED":
        findings.append("CPU_WORKER_PREMATURE_READINESS_CLAIM")
    if implemented["arbitrary_path_or_shell_execution"] or implemented["public_exposure"]:
        findings.append("CPU_WORKER_SECURITY_POLICY_INVALID")
    if findings:
        print(json.dumps({"status": "FAIL", "findings": findings}, indent=2))
        return 1
    print(json.dumps({
        "status": "PASS",
        "worker_online": True,
        "remote_setup_blocked": True,
        "service_ready": False,
        "canonical_writes": 0,
        "protected_decisions": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
