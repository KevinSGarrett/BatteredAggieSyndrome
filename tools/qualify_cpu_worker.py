from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.cpu_worker_backend import (
    CpuWorkerClient,
    CpuWorkerEndpoint,
    CpuWorkerIdentity,
    CpuWorkerJob,
)
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualification_run_id(config_sha256: str, started_at: datetime) -> str:
    identity = f"{config_sha256}:{started_at.astimezone(timezone.utc).isoformat()}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/cpu_worker_qualification.json")
    parser.add_argument("--signing-key-file", type=Path, required=True)
    parser.add_argument("--identity-evidence", type=Path, required=True)
    parser.add_argument("--restart-evidence", type=Path, required=True)
    parser.add_argument("--controller-restart-evidence", type=Path, required=True)
    parser.add_argument("--security-evidence", type=Path, required=True)
    parser.add_argument("--cleanup-evidence", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    captured_at = datetime.now(timezone.utc)
    config_sha256 = sha256(args.config)
    run_id = qualification_run_id(config_sha256, captured_at)
    identity = json.loads(args.identity_evidence.read_text(encoding="utf-8"))
    CpuWorkerIdentity(
        identity["tailscale_dns_name"],
        identity["os"],
        identity["online"],
        windows_hostname=identity["windows_hostname"],
        node_id=identity["tailscale_node_id"],
    ).validate()
    endpoint = CpuWorkerEndpoint(config["private_endpoint"])
    endpoint.validate()
    signing_key = args.signing_key_file.read_bytes()
    if len(signing_key) < 32:
        raise RuntimeError("CPU_WORKER_SIGNING_KEY_TOO_SHORT")
    storage = Path(config["storage_root"])
    with urlopen(f"{config['private_endpoint']}/health", timeout=10) as response:
        health = json.loads(response.read().decode("utf-8"))
    if health.get("status") != "READY_FOR_LIVE_QUALIFICATION" or health.get("transport") != "TAILSCALE_SERVE_PRIVATE_HTTPS":
        raise RuntimeError("CPU_WORKER_HEALTH_IDENTITY_INVALID")
    client = CpuWorkerClient(endpoint, storage, signing_key)
    tranches = []
    for sequence, task in enumerate(config["tasks"], start=1):
        job = CpuWorkerJob(task["task"], task["payload"], config["jira_unit"])
        envelope = job.request(signing_key, nonce=f"qualification-{run_id[:24]}-{sequence:02d}")
        first, first_path = client.submit(job, envelope)
        second, second_path = client.submit(job, envelope)
        tranches.append({
            "sequence": sequence,
            "task": job.task,
            "job_id": job.identity(),
            "first_artifact": str(first_path),
            "first_sha256": sha256(first_path),
            "second_artifact": str(second_path),
            "second_sha256": sha256(second_path),
            "byte_identical_replay": first == second and first_path == second_path,
            "result_sha256": first["result_sha256"],
        })
    restart = json.loads(args.restart_evidence.read_text(encoding="utf-8"))
    controller_restart = json.loads(args.controller_restart_evidence.read_text(encoding="utf-8"))
    security = json.loads(args.security_evidence.read_text(encoding="utf-8"))
    cleanup = json.loads(args.cleanup_evidence.read_text(encoding="utf-8"))
    required_security = {
        "unauthorized_node_rejected", "expired_packet_rejected", "invalid_signature_rejected",
        "corrupt_packet_rejected", "disk_admission_passed", "result_hash_verified",
        "interrupted_job_recovered", "funnel_disabled", "restricted_service_identity",
    }
    passed = (
        len(tranches) >= config["required_deterministic_tranches"]
        and sum(item["task"] == "EXACT_TEXT_DEDUP" for item in tranches) >= config["required_dedup_pilots"]
        and all(item["byte_identical_replay"] for item in tranches)
        and restart.get("restart_recovery") == "PASS"
        and controller_restart.get("reconciliation") == "PASS"
        and all(security.get(field) is True for field in required_security)
        and cleanup.get("status") == "PASS"
    )
    record = {
        "schema_version": 2,
        "qualification_id": config["qualification_id"],
        "jira_unit": config["jira_unit"],
        "captured_at_utc": captured_at.isoformat().replace("+00:00", "Z"),
        "qualification_run_id": run_id,
        "config_sha256": config_sha256,
        "worker_identity": {
            "dns_name": identity["tailscale_dns_name"],
            "node_id": identity["tailscale_node_id"],
            "windows_hostname": identity["windows_hostname"],
            "os": identity["os"],
            "public_funnel": False,
            "durable_ip_identity": False,
        },
        "authority": config["authority"],
        "health": health,
        "tranches": tranches,
        "restart_evidence_sha256": sha256(args.restart_evidence),
        "controller_restart_evidence_sha256": sha256(args.controller_restart_evidence),
        "security_evidence_sha256": sha256(args.security_evidence),
        "cleanup_evidence_sha256": sha256(args.cleanup_evidence),
        "signing_key_recorded": False,
        "canonical_writes": 0,
        "protected_decisions": 0,
        "qualification_disposition": "PASS" if passed else "BLOCKED_CORRECTED_LIVE_GATES_INCOMPLETE",
    }
    path, digest = write_content_addressed_json(storage, "qualifications", record)
    print(json.dumps({"status": record["qualification_disposition"], "path": str(path), "sha256": digest}, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
