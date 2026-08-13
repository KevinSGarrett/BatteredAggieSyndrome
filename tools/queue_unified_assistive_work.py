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

from aggie_analytics.assistive_plane.contracts import canonical_json_bytes, sha256_value  # noqa: E402
from aggie_analytics.assistive_plane.cpu_worker_backend import MAX_RECORDS  # noqa: E402
from aggie_analytics.assistive_plane.inventory_runtime import (  # noqa: E402
    CPU_EXACT_ROUTES,
    OPENROUTER_TASK_FORMAT,
)


DEFAULT_QUEUE = Path(r"C:\BatteredAggieSyndrome.data\assistive\provider_work\requests")


def queue_packet(source: Path, queue_root: Path) -> tuple[Path, str]:
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("PROVIDER_WORK_PACKET_INVALID")
    if value.get("provider") not in {"openai_direct", "openrouter", "ollama_local", "remote_cpu_worker"}:
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
    if value.get("provider") == "openrouter":
        def valid_hash(item: object) -> bool:
            return isinstance(item, str) and len(item) == 64 and all(
                character in "0123456789abcdef" for character in item
            )

        task_id = value.get("task_id")
        task_format = value.get("task_format")
        jira_unit = value.get("jira_unit")
        authority = value.get("authority")
        schema_sha256 = value.get("schema_sha256")
        request_schema_version = value.get("request_schema_version")
        provider_policy_version = value.get("provider_policy_version")
        model = value.get("model")
        reasoning_effort = value.get("reasoning_effort")
        max_output_tokens = value.get("max_output_tokens")
        base_commit = value.get("base_commit")
        source_hashes = value.get("source_hashes")
        evidence_excerpts = value.get("evidence_excerpts")
        identity_hashes = value.get("identity_hashes")
        if (
            task_format != OPENROUTER_TASK_FORMAT
            or not isinstance(task_id, str)
            or not task_id
            or not isinstance(jira_unit, str)
            or not jira_unit
            or not isinstance(schema_sha256, str)
            or not valid_hash(schema_sha256)
            or not isinstance(request_schema_version, str)
            or not request_schema_version
            or not isinstance(provider_policy_version, str)
            or not provider_policy_version
            or not isinstance(model, str)
            or not model
            or not isinstance(reasoning_effort, str)
            or not reasoning_effort
            or not isinstance(max_output_tokens, int)
            or max_output_tokens <= 0
            or not isinstance(base_commit, str)
            or len(base_commit) != 40
            or any(character not in "0123456789abcdef" for character in base_commit)
            or not isinstance(source_hashes, list)
            or not source_hashes
            or not all(valid_hash(item) for item in source_hashes)
            or not isinstance(evidence_excerpts, list)
            or not evidence_excerpts
            or any(not isinstance(item, str) or not item for item in evidence_excerpts)
            or not isinstance(identity_hashes, dict)
            or authority != "CANDIDATE_ONLY_NO_CANONICAL_OR_PROTECTED_WRITES"
        ):
            raise ValueError("PROVIDER_WORK_OPENROUTER_PACKET_INVALID")
        expected_hashes = {
            "task_sha256": sha256_value(
                {"task_id": task_id, "jira_unit": jira_unit, "authority": authority}
            ),
            "schema_sha256": sha256_value(
                {"schema_version": request_schema_version, "schema_sha256": schema_sha256}
            ),
            "policy_sha256": sha256_value(
                {"provider_policy_version": provider_policy_version, "task_format": task_format}
            ),
            "model_sha256": sha256_value({"model": model}),
            "reasoning_sha256": sha256_value(
                {"reasoning_effort": reasoning_effort, "max_output_tokens": max_output_tokens}
            ),
            "source_sha256": sha256_value(tuple(source_hashes)),
        }
        if identity_hashes != expected_hashes:
            raise ValueError("PROVIDER_WORK_OPENROUTER_HASH_IDENTITY_INVALID")
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
