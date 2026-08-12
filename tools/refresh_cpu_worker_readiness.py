from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.cpu_worker_backend import CpuWorkerIdentity
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json


def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/cpu_worker_qualification.json")
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
    CpuWorkerIdentity(peer["DNSName"], peer["OS"], bool(peer["Online"])).validate()
    ports = {str(port): port_open(config["worker_dns_name"], port) for port in [22, 3389, 5985, 5986, config["service_port"]]}
    unattended = ports["22"] or ports["5985"] or ports["5986"]
    service_ready = ports[str(config["service_port"])]
    record = {
        "schema_version": 1,
        "qualification_id": config["qualification_id"],
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "peer": {
            "dns_name": peer["DNSName"].rstrip("."),
            "os": peer["OS"],
            "online": bool(peer["Online"]),
            "tailscale_ips": peer["TailscaleIPs"],
            "node_id": peer["ID"],
        },
        "controller": {
            "dns_name": config["controller_dns_name"],
            "tailscale_ipv4": config["controller_tailscale_ipv4"],
        },
        "ports": ports,
        "public_funnel_configured_by_project": False,
        "unattended_management_channel_ready": unattended,
        "worker_service_ready": service_ready,
        "readiness_disposition": "READY_FOR_QUALIFICATION" if unattended and service_ready else "BLOCKED_REMOTE_SETUP_OR_SERVICE_REQUIRED",
        "blockers": [
            value
            for value, present in [
                ("NO_AUTHENTICATED_UNATTENDED_REMOTE_MANAGEMENT_CHANNEL", unattended),
                ("CPU_WORKER_SERVICE_NOT_LISTENING", service_ready),
            ]
            if not present
        ],
        "canonical_writes": 0,
        "protected_decisions": 0,
    }
    storage = Path(config["storage_root"])
    path, digest = write_content_addressed_json(storage, "readiness", record)
    print(json.dumps({"status": record["readiness_disposition"], "path": str(path), "sha256": digest}, sort_keys=True))
    return 0 if record["readiness_disposition"] == "READY_FOR_QUALIFICATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
