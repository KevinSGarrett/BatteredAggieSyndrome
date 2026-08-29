"""Materialize the corrected 2026 Week Zero calendar and the Texas A&M T-7D gate.

The producer is offline. It consumes the checkpoint capture manifest written by
tools/acquire_2026_week_zero_t7d_evidence.py, the immutable raw pages that manifest
points at, and the already frozen Cycle #20 forecast rows, which it reads without
recomputing any probability.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aggie_analytics.data.national_foundation_reconciliation import (  # noqa: E402
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import parse_utc  # noqa: E402
from aggie_analytics.data.week_zero_2026_calendar import (  # noqa: E402
    CONTRACT_RELATIVE,
    EVIDENCE_RELATIVE,
    GATE_RELATIVE,
    assert_forecasts_unrevised,
    assert_no_backdated_capture,
    build_bundle,
    build_calendar_correction,
    confirm_official_kickoff,
    domain_observations,
    evaluate_checkpoints,
    gate_identity_of,
    load_contract,
    parse_tamu_official_events,
    read_frozen_target_forecasts,
    reconcile_membership,
    select_official_event,
    validate_artifact,
)

PRODUCER = "tools/build_week_zero_2026_calendar_and_t7d_authority.py"
CHECKPOINT_ID = "T_MINUS_7D"
CHECKPOINT_WINDOW_DAYS = 14


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def latest_capture_manifest(data_root: Path, *, capture_identity: str | None) -> dict[str, Any]:
    root = data_root / "manifests" / "shadow" / "week_zero_2026_t7d_capture" / "sha256"
    if capture_identity:
        path = root / capture_identity / "week_zero_2026_t7d_capture_manifest.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing capture manifest: {path}")
        return read_json(path)
    candidates = sorted(root.glob("*/week_zero_2026_t7d_capture_manifest.json"))
    if not candidates:
        raise FileNotFoundError("no T-7D capture manifest is present under the data root")
    manifests = [read_json(path) for path in candidates]
    return max(manifests, key=lambda row: str(row["issued_at_utc"]))


def frozen_forecast_rows(data_root: Path, repo_root: Path) -> list[dict[str, Any]]:
    gate = read_json(repo_root / "artifacts/shadow/prospective_2026_shadow_forecast_gate.json")
    manifest = read_json(data_root / gate["manifest"]["relative_path"])
    payload = next(
        row
        for row in manifest["payloads"]
        if row["role"] == "PROSPECTIVE_2026_SHADOW_FORECAST_ROWS"
    )
    path = data_root / payload["relative_path"]
    observed = sha256_file(path)
    if observed != payload["sha256"]:
        raise ValueError("frozen forecast payload hash drift")
    return read_jsonl(path)


def write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--execution-time-utc", required=True)
    result.add_argument("--capture-identity", default=None)
    result.add_argument("--validate-only", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()

    if args.validate_only:
        outcome = validate_artifact(repo_root)
        print(json.dumps(outcome, indent=2, sort_keys=True))
        return 0 if outcome["result"] == "PASS" else 1

    contract = load_contract(repo_root)
    execution_time = parse_utc(args.execution_time_utc)
    capture_manifest = latest_capture_manifest(data_root, capture_identity=args.capture_identity)
    if capture_manifest["contract_id"] != contract["contract_id"]:
        raise ValueError("capture manifest contract identity drift")

    captures = [row for row in capture_manifest["captures"] if row["state"] == "CAPTURED"]
    assert_no_backdated_capture(
        captures, earliest_permitted=execution_time - timedelta(days=CHECKPOINT_WINDOW_DAYS)
    )
    capture_inventory = []
    for row in sorted(captures, key=lambda item: str(item["source_key"])):
        path = data_root / row["raw_relative_path"]
        observed = sha256_file(path)
        if observed != row["raw_sha256"]:
            raise ValueError(f"immutable capture hash drift: {row['raw_relative_path']}")
        capture_inventory.append(
            {
                "source_key": row["source_key"],
                "source_uri": row["source_uri"],
                "raw_relative_path": row["raw_relative_path"],
                "raw_sha256": row["raw_sha256"],
                "raw_bytes": int(row["raw_bytes"]),
                "retrieved_at_utc": row["retrieved_at_utc"],
                "route_id": row["route_id"],
                "request_identity_sha256": row["request_identity_sha256"],
            }
        )

    date_observations = [
        {
            "game_date": row["game_date"],
            "date_observation_state": row["date_observation_state"],
            "source_echoed_game_date": row.get("source_echoed_game_date"),
            "parsed_card_count": row.get("parsed_card_count") or 0,
        }
        for row in captures
        if "game_date" in row
    ]
    predecessor_gate = read_json(
        repo_root / "artifacts/shadow/prospective_2026_shadow_cohort_gate.json"
    )
    predecessor_contract = read_json(
        repo_root / "configs/prospective_2026_shadow_cohort_contract.json"
    )
    predecessor_observations = {
        str(row["game_date"]): row for row in predecessor_gate.get("date_observations", ())
    }
    calendar_rows = reconcile_membership(
        build_calendar_correction(
            contract=contract,
            predecessor_window=predecessor_contract["schedule_window"],
            date_observations=date_observations,
        ),
        predecessor_observations=predecessor_observations,
    )

    tamu_capture = next(row for row in captures if row["source_key"] == "TAMU_OFFICIAL_SCHEDULE")
    document = (data_root / tamu_capture["raw_relative_path"]).read_text(
        encoding="utf-8", errors="replace"
    )
    event = select_official_event(parse_tamu_official_events(document), contract=contract)
    confirmation = confirm_official_kickoff(contract=contract, event=event, document=document)

    checkpoint_rows = evaluate_checkpoints(
        contract=contract,
        capture_times={CHECKPOINT_ID: parse_utc(str(tamu_capture["retrieved_at_utc"]))},
        execution_time=execution_time,
    )

    target = contract["target_contest"]
    frozen_rows = read_frozen_target_forecasts(
        forecast_rows=frozen_forecast_rows(data_root, repo_root),
        ncaa_contest_id=str(target["ncaa_contest_id"]),
    )
    preservation = assert_forecasts_unrevised(
        rows=frozen_rows,
        bound_snapshot_identity=str(target["bound_snapshot_identity"]),
        kickoff_lower_bound=parse_utc(str(target["kickoff_utc_conservative_lower_bound"])),
    )
    domain_matrix = read_json(
        repo_root / "artifacts/data_lake/national_pit_domain_admission_matrix_gate.json"
    )
    domain_rows = domain_observations(
        contract=contract, confirmation=confirmation, domain_matrix=domain_matrix
    )

    bundle = build_bundle(
        contract=contract,
        contract_sha256=sha256_file(repo_root / CONTRACT_RELATIVE),
        capture_inventory=capture_inventory,
        calendar_rows=calendar_rows,
        confirmation=confirmation,
        checkpoint_rows=checkpoint_rows,
        forecast_preservation=preservation,
        frozen_rows=frozen_rows,
        domain_rows=domain_rows,
        execution_time=execution_time,
        producer=PRODUCER,
    )
    gate = dict(bundle)
    if gate_identity_of(gate) != gate["gate_identity"]:
        raise ValueError("gate identity is not reproducible")

    replay = {
        "schema_version": bundle["schema_version"],
        "artifact_type": "WEEK_ZERO_2026_CALENDAR_AND_TAMU_T7D_REPLAY",
        "contract_id": bundle["contract_id"],
        "gate_identity": bundle["gate_identity"],
        "capture_identity": capture_manifest["capture_identity"],
        "capture_manifest_relative_path": (
            "manifests/shadow/week_zero_2026_t7d_capture/sha256/"
            f"{capture_manifest['capture_identity']}/week_zero_2026_t7d_capture_manifest.json"
        ),
        "execution_time_utc": bundle["execution_time_utc"],
        "checkpoint_ledger": bundle["checkpoint_ledger"],
        "official_kickoff_confirmation": bundle["official_kickoff_confirmation"],
        "corrected_calendar": bundle["corrected_calendar"],
        "counts": bundle["counts"],
        "replay_identity": stable_hash(
            {
                "capture_identity": capture_manifest["capture_identity"],
                "gate_identity": bundle["gate_identity"],
            }
        ),
    }

    write_json(repo_root / GATE_RELATIVE, gate)
    write_json(repo_root / EVIDENCE_RELATIVE, replay)
    outcome = validate_artifact(repo_root)
    print(
        json.dumps(
            {
                "result": bundle["result"],
                "gate_identity": bundle["gate_identity"],
                "capture_identity": capture_manifest["capture_identity"],
                "counts": bundle["counts"],
                "kickoff_utc_independently_confirmed": confirmation[
                    "kickoff_utc_independently_confirmed"
                ],
                "confirmation_state": confirmation["confirmation_state"],
                "t7d_state": next(
                    row["state"]
                    for row in checkpoint_rows
                    if row["checkpoint_id"] == CHECKPOINT_ID
                ),
                "validation": outcome,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if outcome["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
