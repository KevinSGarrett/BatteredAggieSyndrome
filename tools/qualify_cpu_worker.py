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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/cpu_worker_qualification.json")
    parser.add_argument("--restart-evidence", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    CpuWorkerIdentity(config["worker_dns_name"], config["worker_os"], True).validate()
    endpoint = CpuWorkerEndpoint(config["endpoint"], allowed_port=config["service_port"])
    endpoint.validate()
    storage = Path(config["storage_root"])
    with urlopen(f"{config['endpoint']}/health", timeout=10) as response:
        health = json.loads(response.read().decode("utf-8"))
    if health != {
        "status": "READY",
        "schema_version": 1,
        "authority": config["authority"],
        "public_exposure": False,
        "allowed_controller_ip": config["controller_tailscale_ipv4"],
    }:
        raise RuntimeError("CPU_WORKER_HEALTH_IDENTITY_INVALID")
    client = CpuWorkerClient(endpoint, storage)
    tranches = []
    for sequence, task in enumerate(config["tasks"], start=1):
        job = CpuWorkerJob(task["task"], task["payload"], config["jira_unit"])
        first, first_path = client.submit(job)
        second, second_path = client.submit(job)
        tranches.append({
            "sequence": sequence,
            "task": job.task,
            "request_id": job.identity(),
            "first_artifact": str(first_path),
            "first_sha256": sha256(first_path),
            "second_artifact": str(second_path),
            "second_sha256": sha256(second_path),
            "byte_identical_replay": first == second and first_path == second_path,
            "result_sha256": first["result_sha256"],
        })
    restart = None
    if args.restart_evidence:
        restart = json.loads(args.restart_evidence.read_text(encoding="utf-8"))
    passed = (
        len(tranches) >= config["required_deterministic_tranches"]
        and sum(item["task"] == "EXACT_TEXT_DEDUP" for item in tranches) >= config["required_dedup_pilots"]
        and all(item["byte_identical_replay"] for item in tranches)
        and restart is not None
        and restart.get("restart_recovery") == "PASS"
    )
    record = {
        "schema_version": 1,
        "qualification_id": config["qualification_id"],
        "jira_unit": config["jira_unit"],
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "config_sha256": sha256(args.config),
        "worker_identity": {
            "dns_name": config["worker_dns_name"],
            "os": config["worker_os"],
            "tailscale_ipv4": config["worker_tailscale_ipv4"],
            "public_exposure": False,
        },
        "authority": config["authority"],
        "health": health,
        "tranches": tranches,
        "restart_evidence": restart,
        "canonical_writes": 0,
        "protected_decisions": 0,
        "qualification_disposition": "PASS" if passed else "BLOCKED_RESTART_EVIDENCE_REQUIRED",
    }
    path, digest = write_content_addressed_json(storage, "qualifications", record)
    print(json.dumps({"status": record["qualification_disposition"], "path": str(path), "sha256": digest}, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
