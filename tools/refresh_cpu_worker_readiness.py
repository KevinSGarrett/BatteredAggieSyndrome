from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.cpu_worker_backend import CpuWorkerIdentity
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/cpu_worker_qualification.json")
    parser.add_argument("--deployment-evidence", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    completed = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError("TAILSCALE_STATUS_FAILED")
    status = json.loads(completed.stdout)
    peers = [peer for peer in status.get("Peer", {}).values() if peer.get("DNSName", "").rstrip(".").lower() == config["worker_dns_name"].lower()]
    if len(peers) != 1:
        raise RuntimeError("CPU_WORKER_PEER_NOT_UNIQUE")
    peer = peers[0]
    CpuWorkerIdentity(
        peer["DNSName"],
        peer["OS"],
        bool(peer["Online"]),
        windows_hostname=config["worker_windows_hostname"],
        node_id=peer["ID"],
        allowed_dns_name=config["worker_dns_name"],
        allowed_node_id=config["worker_node_id"],
    ).validate()
    deployment = None
    if args.deployment_evidence:
        deployment = json.loads(args.deployment_evidence.read_text(encoding="utf-8"))
    required_gates = {
        "private_https",
        "coordinator_grant",
        "signed_envelope",
        "restricted_service_identity",
        "minimal_bundle_hash_match",
        "live_replay",
        "restart_recovery",
        "cleanup",
    }
    passed_gates = set(deployment.get("passed_gates", [])) if deployment else set()
    corrected_ready = required_gates <= passed_gates
    record = {
        "schema_version": 1,
        "qualification_id": config["qualification_id"],
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "peer": {
            "dns_name": peer["DNSName"].rstrip("."),
            "os": peer["OS"],
            "online": bool(peer["Online"]),
            "observed_tailscale_ips": peer["TailscaleIPs"],
            "node_id": peer["ID"],
            "windows_hostname": config["worker_windows_hostname"],
            "durable_ip_identity": False,
        },
        "controller": {
            "dns_name": config["controller_dns_name"],
            "node_id": config["controller_node_id"],
        },
        "required_transport": config["transport"],
        "required_authentication": config["authentication"],
        "required_privilege": config["privilege"],
        "required_bundle": config["bundle"],
        "public_funnel_configured_by_project": False,
        "prototype_direct_http_disabled": True,
        "corrected_deployment_evidence_path": str(args.deployment_evidence) if args.deployment_evidence else None,
        "passed_gates": sorted(passed_gates),
        "readiness_disposition": "READY_FOR_LIVE_QUALIFICATION" if corrected_ready else "BLOCKED_CORRECTED_ARCHITECTURE_REQUIRED",
        "blockers": sorted(required_gates - passed_gates),
        "canonical_writes": 0,
        "protected_decisions": 0,
    }
    storage = Path(config["storage_root"])
    path, digest = write_content_addressed_json(storage, "readiness", record)
    print(json.dumps({"status": record["readiness_disposition"], "path": str(path), "sha256": digest}, sort_keys=True))
    return 0 if corrected_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
