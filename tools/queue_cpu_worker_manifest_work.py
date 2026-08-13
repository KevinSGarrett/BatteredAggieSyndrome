from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.inventory_runtime import (  # noqa: E402
    CPU_MANIFEST_SCHEMA_SHA256,
    CPU_MANIFEST_TASK_FORMAT,
    MAX_DISCOVERED_MANIFEST_BYTES,
)
from tools.queue_unified_assistive_work import DEFAULT_QUEUE, queue_packet  # noqa: E402


DEFAULT_MANIFEST_ROOT = Path(r"C:\BatteredAggieSyndrome.data\manifests")


def build_packet(source: Path, manifest_root: Path) -> dict[str, Any]:
    root = manifest_root.resolve(strict=True)
    resolved = source.resolve(strict=True)
    if root not in resolved.parents:
        raise ValueError("CPU_CAMPAIGN_MANIFEST_OUTSIDE_ALLOWLIST")
    size = resolved.stat().st_size
    if size <= 0 or size > MAX_DISCOVERED_MANIFEST_BYTES:
        raise ValueError("CPU_CAMPAIGN_MANIFEST_SIZE_INVALID")
    raw = resolved.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("CPU_CAMPAIGN_MANIFEST_NOT_OBJECT")
    relative = resolved.relative_to(root).as_posix()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    return {
        "schema_version": 1,
        "provider": "remote_cpu_worker",
        "task": "CANONICAL_JSON",
        "task_format": CPU_MANIFEST_TASK_FORMAT,
        "jira_unit": "BAT-563",
        "schema_sha256": CPU_MANIFEST_SCHEMA_SHA256,
        "source_hashes": [source_sha256],
        "dependencies": [],
        "pre_routing_effort_points": 1,
        "scope": f"Exact canonicalization and provenance QA for selected external manifest {relative}",
        "payload": {"value": value},
        "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Queue one allowlisted external manifest for the qualified deterministic CPU worker"
    )
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE)
    args = parser.parse_args()
    packet = build_packet(args.source_manifest, args.manifest_root)
    temporary_packet = args.queue_root.parent / "runtime" / (
        ".cpu-manifest-packet-" + packet["source_hashes"][0] + ".json"
    )
    temporary_packet.parent.mkdir(parents=True, exist_ok=True)
    try:
        temporary_packet.write_text(
            json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        destination, digest = queue_packet(temporary_packet, args.queue_root)
    finally:
        temporary_packet.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "result": "PASS",
                "packet_path": str(destination),
                "packet_sha256": digest,
                "source_sha256": packet["source_hashes"][0],
                "live_remote_calls": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
