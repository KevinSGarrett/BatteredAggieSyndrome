from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.cpu_worker_backend import CpuWorkerIdentity
from aggie_analytics.assistive_plane.orchestration import write_content_addressed_json


def run(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def main() -> int:
    tailscale = json.loads(run(["tailscale", "status", "--json"]))
    peers: list[dict[str, Any]] = []
    for peer in tailscale.get("Peer", {}).values():
        peers.append({
            "hostname": peer.get("HostName"),
            "dns_name": peer.get("DNSName"),
            "online": bool(peer.get("Online")),
            "os": peer.get("OS"),
            "tailscale_ips": peer.get("TailscaleIPs", []),
        })
    cpu = [peer for peer in peers if str(peer.get("dns_name", "")).rstrip(".").lower() == "comfy-v4-cpu-01.tail9b05ab.ts.net"]
    if len(cpu) != 1:
        raise RuntimeError("CPU_WORKER_NOT_UNIQUE_IN_TAILSCALE_STATUS")
    CpuWorkerIdentity(cpu[0]["dns_name"], cpu[0]["os"], cpu[0]["online"]).validate()
    models = run(["ollama", "list"])
    running = run(["ollama", "ps"])
    payload = {
        "schema_version": 1,
        "controller": {
            "hostname": platform.node(),
            "os": platform.system(),
            "tailscale_dns_name": tailscale.get("Self", {}).get("DNSName"),
            "online": bool(tailscale.get("Self", {}).get("Online")),
        },
        "peers": sorted(peers, key=lambda item: str(item.get("dns_name"))),
        "cpu_worker_identity_valid": True,
        "ollama": {
            "version": run(["ollama", "--version"]),
            "models_text": models,
            "running_text": running,
            "policy": {"loopback_only": True, "max_loaded_models": 1, "parallel_requests": 1, "initial_context_tokens": 4096},
        },
        "gpu": run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"]),
        "credential_material_recorded": False,
    }
    root = Path(r"C:\BatteredAggieSyndrome.data\assistive\runtime")
    path, digest = write_content_addressed_json(root, "capability", payload)
    print(json.dumps({
        "status": "PASS",
        "controller": payload["controller"]["hostname"],
        "peer_count": len(peers),
        "cpu_worker_online": True,
        "runtime_sha256": digest,
        "runtime_path": str(path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
