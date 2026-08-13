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

from aggie_analytics.assistive_plane.cpu_worker_backend import (  # noqa: E402
    MAX_RECORDS,
    MAX_TEXT_BYTES,
)
from aggie_analytics.assistive_plane.inventory_runtime import (  # noqa: E402
    CPU_LINE_HASH_SCHEMA_SHA256,
    CPU_LINE_HASH_TASK_FORMAT,
    CPU_TEXT_DEDUP_SCHEMA_SHA256,
    CPU_TEXT_DEDUP_TASK_FORMAT,
    MAX_DISCOVERED_MANIFEST_BYTES,
)
from tools.queue_unified_assistive_work import DEFAULT_QUEUE, queue_packet  # noqa: E402


DEFAULT_MANIFEST_ROOT = Path(r"C:\BatteredAggieSyndrome.data\manifests")


def _resolve_source(source: Path, manifest_root: Path) -> tuple[Path, Path, bytes]:
    root = manifest_root.resolve(strict=True)
    resolved = source.resolve(strict=True)
    if root not in resolved.parents:
        raise ValueError("CPU_CAMPAIGN_TEXT_SOURCE_OUTSIDE_ALLOWLIST")
    raw = resolved.read_bytes()
    if not raw or len(raw) > MAX_DISCOVERED_MANIFEST_BYTES:
        raise ValueError("CPU_CAMPAIGN_TEXT_SOURCE_SIZE_INVALID")
    return root, resolved, raw


def _json_pointer(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def _string_leaves(value: Any, pointer: str = "") -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    if isinstance(value, str):
        records.append({"id": pointer or "/", "text": value})
    elif isinstance(value, list):
        for index, item in enumerate(value):
            records.extend(_string_leaves(item, f"{pointer}/{index}"))
    elif isinstance(value, dict):
        for key in sorted(value):
            records.extend(_string_leaves(value[key], f"{pointer}/{_json_pointer(str(key))}"))
    return records


def build_packet(source: Path, manifest_root: Path, mode: str) -> dict[str, Any]:
    root, resolved, raw = _resolve_source(source, manifest_root)
    relative = resolved.relative_to(root).as_posix()
    source_sha256 = hashlib.sha256(raw).hexdigest()
    if mode == "line-hash":
        lines = raw.decode("utf-8").splitlines()
        task = "LINE_HASH_MANIFEST"
        task_format = CPU_LINE_HASH_TASK_FORMAT
        schema_sha256 = CPU_LINE_HASH_SCHEMA_SHA256
        payload: dict[str, Any] = {"lines": lines}
        purpose = "Line-level integrity manifest"
    elif mode == "exact-text-dedup":
        value = json.loads(raw)
        records = _string_leaves(value)
        if not records:
            raise ValueError("CPU_CAMPAIGN_TEXT_NO_STRING_RECORDS")
        task = "EXACT_TEXT_DEDUP"
        task_format = CPU_TEXT_DEDUP_TASK_FORMAT
        schema_sha256 = CPU_TEXT_DEDUP_SCHEMA_SHA256
        payload = {"records": records}
        purpose = "Exact normalized string deduplication candidate analysis"
    else:
        raise ValueError("CPU_CAMPAIGN_TEXT_MODE_INVALID")
    if len(next(iter(payload.values()))) > MAX_RECORDS:
        raise ValueError("CPU_CAMPAIGN_TEXT_RECORD_LIMIT")
    encoded_payload = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(encoded_payload) > MAX_TEXT_BYTES:
        raise ValueError("CPU_CAMPAIGN_TEXT_PAYLOAD_SIZE_INVALID")
    return {
        "schema_version": 1,
        "provider": "remote_cpu_worker",
        "task": task,
        "task_format": task_format,
        "jira_unit": "BAT-563",
        "schema_sha256": schema_sha256,
        "source_hashes": [source_sha256],
        "dependencies": [],
        "pre_routing_effort_points": 1,
        "scope": f"{purpose} for selected external manifest {relative}",
        "payload": payload,
        "authority": "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Queue one allowlisted external manifest for an exact qualified CPU text route"
    )
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--mode", choices=("line-hash", "exact-text-dedup"), required=True)
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_ROOT)
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE)
    args = parser.parse_args()
    packet = build_packet(args.source_manifest, args.manifest_root, args.mode)
    temporary_packet = args.queue_root.parent / "runtime" / (
        ".cpu-text-packet-" + packet["source_hashes"][0] + "-" + packet["task"] + ".json"
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
                "task": packet["task"],
                "live_remote_calls": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
