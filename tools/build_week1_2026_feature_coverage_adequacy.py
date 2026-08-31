"""Materialize the Week 1 2026 feature coverage and forecast-input adequacy gate."""

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
    stable_hash,
)
from aggie_analytics.data.week1_2026_feature_coverage_adequacy import (  # noqa: E402
    CANDIDATE_PAYLOAD_NAME,
    CONTEST_PAYLOAD_NAME,
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    PAYLOAD_SLUG,
    Week1AdequacyViolation,
    build_adequacy_rows,
    build_gate,
    compare_contest_to_national_distribution,
    dataset_manifest,
    load_contract,
    read_jsonl,
    summarize,
)

FOCUS_AWAY_DISPLAY_NAME = "Missouri St."
FOCUS_HOME_DISPLAY_NAME = "Texas A&M"


def canonical_payload_path(gate: Mapping[str, Any], data_root: Path, name: str) -> Path:
    manifest = json.loads(
        (data_root / gate["manifest"]["relative_path"]).read_text(encoding="utf-8-sig")
    )
    for payload in manifest["payloads"]:
        if payload["name"] == name:
            return data_root / payload["relative_path"]
    raise Week1AdequacyViolation(
        f"predecessor manifest does not declare payload {name}"
    )


def write_payload(
    data_root: Path, name: str, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    payload_bytes = (
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        )
    ).encode("utf-8")
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

    spine_gate_path = repo_root / sources["feature_spine"]["gate_relative_path"]
    spine_gate = json.loads(spine_gate_path.read_text(encoding="utf-8-sig"))
    rows = read_jsonl(
        canonical_payload_path(
            spine_gate, data_root, sources["feature_spine"]["row_payload_name"]
        )
    )
    cells = read_jsonl(
        canonical_payload_path(
            spine_gate, data_root, sources["feature_spine"]["cell_payload_name"]
        )
    )

    schedule_gate_path = repo_root / sources["schedule_identity"]["gate_relative_path"]
    schedule_gate = json.loads(schedule_gate_path.read_text(encoding="utf-8-sig"))
    candidate_gate_path = repo_root / sources["frozen_candidates"]["gate_relative_path"]
    candidate_gate = json.loads(candidate_gate_path.read_text(encoding="utf-8-sig"))

    declared = {
        requirement["candidate_id"]
        for requirement in contract["candidate_feature_requirements"]
    }
    frozen = {candidate["candidate_id"] for candidate in candidate_gate["candidates"]}
    if declared != frozen:
        raise Week1AdequacyViolation(
            "the declared candidate requirements do not match the frozen candidate set"
        )

    return {
        "contract": contract,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "rows": rows,
        "cells": cells,
        "bound_predecessors": {
            "feature_spine_gate_identity": spine_gate["gate_identity"],
            "feature_spine_gate_sha256": sha256_file(spine_gate_path),
            "feature_spine_dataset_identity": spine_gate["manifest"][
                "dataset_identity"
            ],
            "feature_spine_payload_root_sha256": spine_gate["payload_root_sha256"],
            "feature_spine_snapshot_issuance_utc": spine_gate["snapshot_issuance_utc"],
            "week1_schedule_identity_gate_identity": schedule_gate["gate_identity"],
            "week1_schedule_identity_gate_sha256": sha256_file(schedule_gate_path),
            "frozen_candidate_gate_identity": candidate_gate["gate_identity"],
            "frozen_candidate_gate_sha256": sha256_file(candidate_gate_path),
        },
    }


def find_focus_contest(rows: Sequence[Mapping[str, Any]]) -> str | None:
    """Discover the focus contest from the universe rather than hardcoding its id."""

    by_contest: dict[str, set[str]] = {}
    for row in rows:
        by_contest.setdefault(row["ncaa_contest_id"], set()).add(
            row["source_display_name"]
        )
    matches = sorted(
        contest_id
        for contest_id, names in by_contest.items()
        if {FOCUS_AWAY_DISPLAY_NAME, FOCUS_HOME_DISPLAY_NAME} <= names
    )
    if len(matches) > 1:
        raise Week1AdequacyViolation(
            "the focus contest label matched more than one contest"
        )
    return matches[0] if matches else None


def build(repo_root: Path, data_root: Path, execution_time: datetime) -> dict[str, Any]:
    inputs = load_inputs(repo_root, data_root)
    contest_rows, candidate_rows = build_adequacy_rows(
        contract=inputs["contract"], rows=inputs["rows"], cells=inputs["cells"]
    )
    focus_contest_id = find_focus_contest(inputs["rows"])
    focus_report = None
    if focus_contest_id is not None:
        focus_row = next(
            row for row in contest_rows if row["ncaa_contest_id"] == focus_contest_id
        )
        focus_report = compare_contest_to_national_distribution(
            contest_row=focus_row,
            contest_rows=contest_rows,
            candidate_rows=candidate_rows,
        )

    payloads = [
        write_payload(data_root, CONTEST_PAYLOAD_NAME, contest_rows),
        write_payload(data_root, CANDIDATE_PAYLOAD_NAME, candidate_rows),
    ]
    summary = summarize(contest_rows, candidate_rows, inputs["rows"])
    manifest = dataset_manifest(
        contract=inputs["contract"],
        summary=summary,
        payloads=payloads,
        bound_predecessors=inputs["bound_predecessors"],
        execution_time=execution_time,
    )
    manifest_relative = (
        f"manifests/{PAYLOAD_SLUG}/sha256/{manifest['dataset_identity']}"
        f"/{PAYLOAD_SLUG}_manifest.json"
    )
    manifest_path = data_root / manifest_relative
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    gate = build_gate(
        contract=inputs["contract"],
        contract_sha256=inputs["contract_sha256"],
        contest_rows=contest_rows,
        candidate_rows=candidate_rows,
        spine_rows=inputs["rows"],
        focus_report=focus_report,
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
        json.dumps(gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return gate


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument(
        "--data-root", default=os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", "")
    )
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
    except Week1AdequacyViolation as exc:
        print(f"week 1 adequacy violation: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {"gate_identity": gate["gate_identity"], "summary": gate["summary"]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
