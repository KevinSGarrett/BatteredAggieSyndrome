from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.assistive_plane.orchestration import ReadyWorkInventory, ReadyWorkUnit, RouteDecision, RoutingDisposition, write_content_addressed_json


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_for(local_id: str) -> tuple[Path, dict[str, Any]]:
    matches = list((ROOT / "jira/records/issues").rglob(f"{local_id}_*.json"))
    if len(matches) != 1:
        raise RuntimeError(f"JIRA_RECORD_NOT_UNIQUE:{local_id}:{len(matches)}")
    return matches[0], json.loads(matches[0].read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=ROOT / "configs/unified_assistive_ready_work.json")
    parser.add_argument("--storage-root", type=Path, default=Path(r"C:\BatteredAggieSyndrome.data\assistive\inventory"))
    args = parser.parse_args()
    seed = json.loads(args.seed.read_text(encoding="utf-8"))
    units: list[ReadyWorkUnit] = []
    pending: list[dict[str, Any]] = []
    source_records: list[dict[str, str]] = []
    for item in seed["work_units"]:
        record_path, record = record_for(item["local_id"])
        schema_path = ROOT / item["schema_path"]
        unit = ReadyWorkUnit(
            work_unit_id=item["local_id"],
            jira_unit=record["jira_key"],
            task_format=item["task_format"],
            schema_sha256=sha256(schema_path),
            authority=item["authority"],
            source_hashes=(sha256(record_path),),
            dependencies=tuple(record.get("dependencies", [])),
            pre_routing_effort_points=item["pre_routing_effort_points"],
            scope=item["scope"],
        )
        units.append(unit)
        pending.append(item)
        source_records.append({"local_id": item["local_id"], "jira_key": record["jira_key"], "record_sha256": sha256(record_path)})
    decisions = [
        RouteDecision(
            work_unit_id=unit.work_unit_id,
            work_unit_identity=unit.identity(),
            disposition=RoutingDisposition(item["disposition"]),
            provider=item["provider"],
            model=item["model"],
            reason=item["reason"],
            decided_at=seed["decided_at"],
        )
        for unit, item in zip(units, pending, strict=True)
    ]
    report = ReadyWorkInventory(units, decisions).validate()
    snapshot = {
        "schema_version": 1,
        "inventory_seed_id": seed["inventory_seed_id"],
        "seed_sha256": sha256(args.seed),
        "work_units": [
            {
                "work_unit_id": unit.work_unit_id,
                "jira_unit": unit.jira_unit,
                "task_format": unit.task_format,
                "schema_sha256": unit.schema_sha256,
                "authority": unit.authority,
                "source_hashes": list(unit.source_hashes),
                "dependencies": list(unit.dependencies),
                "pre_routing_effort_points": unit.pre_routing_effort_points,
                "scope": unit.scope,
                "identity": unit.identity(),
            }
            for unit in units
        ],
        "route_decisions": [
            {
                "work_unit_id": decision.work_unit_id,
                "work_unit_identity": decision.work_unit_identity,
                "disposition": decision.disposition.value,
                "provider": decision.provider,
                "model": decision.model,
                "reason": decision.reason,
                "decided_at": decision.decided_at,
            }
            for decision in decisions
        ],
        "source_records": source_records,
        "validation": report,
        "canonical_or_protected_authority": False,
    }
    path, digest = write_content_addressed_json(args.storage_root, "snapshots", snapshot)
    print(json.dumps({"status": "PASS", "snapshot_path": str(path), "snapshot_sha256": digest, **report}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
