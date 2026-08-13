from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.contracts import canonical_json_bytes  # noqa: E402
from aggie_analytics.assistive_plane.cpu_worker_backend import MAX_RECORDS  # noqa: E402
from aggie_analytics.assistive_plane.inventory_runtime import CPU_EXACT_ROUTES  # noqa: E402


DEFAULT_QUEUE = Path(r"C:\BatteredAggieSyndrome.data\assistive\provider_work\requests")


def queue_packet(source: Path, queue_root: Path) -> tuple[Path, str]:
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("PROVIDER_WORK_PACKET_INVALID")
    if value.get("provider") not in {"openai_direct", "ollama_local", "remote_cpu_worker"}:
        raise ValueError("PROVIDER_WORK_PROVIDER_NOT_ADMITTED")
    if value.get("authority") != "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES":
        raise ValueError("PROVIDER_WORK_AUTHORITY_INVALID")
    if value.get("provider") == "remote_cpu_worker":
        def valid_hash(item: object) -> bool:
            return isinstance(item, str) and len(item) == 64 and all(
                character in "0123456789abcdef" for character in item
            )

        payload = value.get("payload")
        task = value.get("task")
        route = CPU_EXACT_ROUTES.get(str(task))
        payload_valid = (
            task == "CANONICAL_JSON"
            and isinstance(payload, dict)
            and set(payload) == {"value"}
        ) or (
            task == "LINE_HASH_MANIFEST"
            and isinstance(payload, dict)
            and set(payload) == {"lines"}
            and isinstance(payload["lines"], list)
            and bool(payload["lines"])
            and len(payload["lines"]) <= MAX_RECORDS
            and all(isinstance(item, str) for item in payload["lines"])
        ) or (
            task == "EXACT_TEXT_DEDUP"
            and isinstance(payload, dict)
            and set(payload) == {"records"}
            and isinstance(payload["records"], list)
            and bool(payload["records"])
            and len(payload["records"]) <= MAX_RECORDS
            and all(
                isinstance(item, dict)
                and set(item) == {"id", "text"}
                and isinstance(item["id"], str)
                and bool(item["id"])
                and isinstance(item["text"], str)
                for item in payload["records"]
            )
            and len({item["id"] for item in payload["records"]}) == len(payload["records"])
        )
        if (
            route is None
            or value.get("task_format") != route[0]
            or value.get("jira_unit") != "BAT-563"
            or value.get("schema_sha256") != route[1]
            or not payload_valid
            or not isinstance(value.get("source_hashes"), list)
            or not value["source_hashes"]
            or not all(valid_hash(item) for item in value["source_hashes"])
            or value.get("pre_routing_effort_points") not in {1, 2, 3, 5, 8}
        ):
            raise ValueError("PROVIDER_WORK_CPU_PACKET_INVALID")
    data = canonical_json_bytes(value) + b"\n"
    digest = hashlib.sha256(data).hexdigest()
    destination = queue_root / "sha256" / digest[:2] / f"{digest}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() != data:
            raise RuntimeError("PROVIDER_WORK_CONTENT_ADDRESS_COLLISION")
        return destination, digest
    descriptor, temporary_name = tempfile.mkstemp(prefix=".provider-work-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return destination, digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE)
    args = parser.parse_args()
    destination, digest = queue_packet(args.packet, args.queue_root)
    print(json.dumps({"result": "PASS", "packet_path": str(destination), "packet_sha256": digest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
