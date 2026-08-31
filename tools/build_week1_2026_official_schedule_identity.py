"""Materialize the official 2026 Week 1 national schedule and identity universe."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    binding_identity,
    sha256_file,
)
from aggie_analytics.data.week1_2026_official_schedule_identity import (  # noqa: E402
    CONTEST_PAYLOAD_NAME,
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    PARTICIPANT_PAYLOAD_NAME,
    PAYLOAD_SLUG,
    Week1ScheduleIdentityViolation,
    build_contest_rows,
    build_gate,
    build_participant_rows,
    dataset_manifest,
    index_predecessor_identities,
    index_team_season_authority,
    load_contract,
    read_jsonl,
    stable_hash,
    summarize,
)


def canonical_payload_entry(gate: Mapping[str, Any], data_root: Path, name: str) -> Path:
    """Resolve a predecessor payload through its manifest rather than by convention."""

    manifest = json.loads(
        (data_root / gate["manifest"]["relative_path"]).read_text(encoding="utf-8-sig")
    )
    for payload in manifest["payloads"]:
        if payload["name"] == name:
            return data_root / payload["relative_path"]
    raise Week1ScheduleIdentityViolation(f"predecessor manifest does not declare payload {name}")


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return (
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    ).encode("utf-8")


def write_payload(data_root: Path, name: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    payload_bytes = jsonl_bytes(rows)
    identity = stable_hash(list(rows))
    relative = f"canonical/{PAYLOAD_SLUG}/sha256/{identity}/{name}"
    target = data_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        handle.write(payload_bytes)
    return {
        "name": name,
        "relative_path": relative,
        "role": name.replace(".jsonl", "").upper(),
        "rows": len(rows),
        "bytes": len(payload_bytes),
        "sha256": sha256_file(target),
        "payload_identity": identity,
    }


def load_inputs(repo_root: Path, data_root: Path) -> dict[str, Any]:
    contract = load_contract(repo_root)
    sources = contract["sources"]

    schedule_manifest_path = data_root / sources["schedule_capture"]["manifest_relative_path"]
    schedule_manifest = json.loads(schedule_manifest_path.read_text(encoding="utf-8-sig"))
    if schedule_manifest.get("capture_identity") != sources["schedule_capture"]["capture_identity"]:
        raise Week1ScheduleIdentityViolation("schedule capture identity drifted from the contract")

    authority_manifest_path = data_root / sources["team_season_authority"]["manifest_relative_path"]
    authority_manifest = json.loads(authority_manifest_path.read_text(encoding="utf-8-sig"))
    if (
        authority_manifest.get("capture_identity")
        != sources["team_season_authority"]["capture_identity"]
    ):
        raise Week1ScheduleIdentityViolation("season authority capture identity drifted")

    benchmark_gate_path = repo_root / sources["entity_identity_benchmark"]["gate_relative_path"]
    benchmark_gate = json.loads(benchmark_gate_path.read_text(encoding="utf-8-sig"))
    cohort_path = canonical_payload_entry(
        benchmark_gate, data_root, sources["entity_identity_benchmark"]["cohort_payload_name"]
    )

    captures = [row for row in schedule_manifest["captures"] if row["state"] == "CAPTURED"]
    documents: dict[str, str] = {}
    capture_inventory: list[dict[str, Any]] = []
    for capture in captures:
        raw_path = data_root / capture["raw_relative_path"]
        observed = sha256_file(raw_path)
        if observed != capture["raw_sha256"]:
            raise Week1ScheduleIdentityViolation(
                f"raw capture hash drifted for {capture['requested_game_date']}"
            )
        documents[capture["requested_game_date"]] = raw_path.read_text(
            encoding="utf-8", errors="replace"
        )
        capture_inventory.append(
            {
                "requested_game_date": capture["requested_game_date"],
                "source_uri": capture["source_uri"],
                "request_identity_sha256": capture["request_identity_sha256"],
                "raw_relative_path": capture["raw_relative_path"],
                "raw_sha256": observed,
                "raw_bytes": raw_path.stat().st_size,
                "retrieved_at_utc": capture["retrieved_at_utc"],
                "route_id": capture["route_id"],
                "attempts": capture["attempts"],
            }
        )
    capture_inventory.sort(key=lambda row: row["requested_game_date"])

    return {
        "contract": contract,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "captures": captures,
        "documents": documents,
        "capture_inventory": capture_inventory,
        "authority": index_team_season_authority(authority_manifest),
        "predecessor": index_predecessor_identities(read_jsonl(cohort_path)),
        "bound_predecessors": {
            "national_entity_identity_benchmark_gate_identity": benchmark_gate["gate_identity"],
            "national_entity_identity_benchmark_gate_sha256": sha256_file(benchmark_gate_path),
            "week1_source_universe_capture_identity": schedule_manifest["capture_identity"],
            "week1_source_universe_capture_manifest_sha256": sha256_file(schedule_manifest_path),
            "team_season_authority_capture_identity": authority_manifest["capture_identity"],
            "team_season_authority_capture_manifest_sha256": sha256_file(authority_manifest_path),
        },
    }


def build(repo_root: Path, data_root: Path, execution_time: datetime) -> dict[str, Any]:
    inputs = load_inputs(repo_root, data_root)
    contests = build_contest_rows(
        contract=inputs["contract"],
        captures=inputs["captures"],
        documents=inputs["documents"],
        predecessor=inputs["predecessor"],
        authority=inputs["authority"],
    )
    participants = build_participant_rows(contests)
    payloads = [
        write_payload(data_root, CONTEST_PAYLOAD_NAME, contests),
        write_payload(data_root, PARTICIPANT_PAYLOAD_NAME, participants),
    ]
    summary = summarize(contests, participants)
    manifest = dataset_manifest(
        contract=inputs["contract"],
        summary=summary,
        capture_inventory=inputs["capture_inventory"],
        payloads=payloads,
        execution_time=execution_time,
    )
    manifest_relative = (
        f"manifests/{PAYLOAD_SLUG}/sha256/{manifest['dataset_identity']}"
        f"/{PAYLOAD_SLUG}_manifest.json"
    )
    manifest_path = data_root / manifest_relative
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )

    gate = build_gate(
        contract=inputs["contract"],
        contract_sha256=inputs["contract_sha256"],
        contests=contests,
        participants=participants,
        capture_inventory=inputs["capture_inventory"],
        manifest_relative_path=manifest_relative,
        manifest_sha256=sha256_file(manifest_path),
        dataset_identity=manifest["dataset_identity"],
        payloads=[
            {key: value for key, value in payload.items() if key != "relative_path"}
            for payload in payloads
        ],
        bound_predecessors=inputs["bound_predecessors"],
        execution_time=execution_time,
    )
    gate["gate_identity"] = binding_identity(gate, "gate_identity")
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return gate


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", ""))
    parser.add_argument("--execution-time", default=None)
    args = parser.parse_args(argv)
    if not args.data_root:
        print("AGGIE_ANALYTICS_DATA_ROOT is required", file=sys.stderr)
        return 2
    execution_time = (
        datetime.fromisoformat(args.execution_time.replace("Z", "+00:00"))
        if args.execution_time
        else datetime.now(timezone.utc)
    )
    try:
        gate = build(Path(args.repo_root), Path(args.data_root), execution_time)
    except Week1ScheduleIdentityViolation as exc:
        print(f"week 1 schedule identity violation: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"gate_identity": gate["gate_identity"], "summary": gate["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
