"""Materialize the timestamped national Week 1 2026 current-feature spine."""

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
from aggie_analytics.data.week1_2026_current_feature_spine import (  # noqa: E402
    CELL_PAYLOAD_NAME,
    CONTRACT_RELATIVE,
    GATE_RELATIVE,
    PAYLOAD_SLUG,
    ROW_PAYLOAD_NAME,
    Week1FeatureSpineViolation,
    assert_future_append_invariance,
    build_gate,
    build_spine_rows,
    dataset_manifest,
    index_rankings,
    index_weather_vintages,
    index_week_zero_finals,
    load_contract,
    parse_ranking_document,
    read_jsonl,
    summarize,
)


def canonical_payload_path(gate: Mapping[str, Any], data_root: Path, name: str) -> Path:
    manifest = json.loads(
        (data_root / gate["manifest"]["relative_path"]).read_text(encoding="utf-8-sig")
    )
    for payload in manifest["payloads"]:
        if payload["name"] == name:
            return data_root / payload["relative_path"]
    raise Week1FeatureSpineViolation(f"predecessor manifest does not declare payload {name}")


def write_payload(data_root: Path, name: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    payload_bytes = (
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
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

    schedule_gate_path = repo_root / sources["schedule_identity"]["gate_relative_path"]
    schedule_gate = json.loads(schedule_gate_path.read_text(encoding="utf-8-sig"))
    contests = read_jsonl(
        canonical_payload_path(
            schedule_gate, data_root, sources["schedule_identity"]["contest_payload_name"]
        )
    )
    participants = read_jsonl(
        canonical_payload_path(
            schedule_gate, data_root, sources["schedule_identity"]["participant_payload_name"]
        )
    )

    alias_gate_path = repo_root / sources["entity_alias_authority"]["gate_relative_path"]
    alias_gate = json.loads(alias_gate_path.read_text(encoding="utf-8-sig"))
    alias_rows = read_jsonl(
        canonical_payload_path(
            alias_gate, data_root, sources["entity_alias_authority"]["cohort_payload_name"]
        )
    )
    aliases: dict[str, list[str]] = {}
    for row in alias_rows:
        for participant in row.get("participants", []):
            name = participant.get("spine_display_name")
            if not name:
                continue
            key = str(participant["source_team_id"])
            if name not in aliases.setdefault(key, []):
                aliases[key].append(str(name))

    scoring_gate_path = repo_root / sources["week_zero_official_finals"]["gate_relative_path"]
    scoring_gate = json.loads(scoring_gate_path.read_text(encoding="utf-8-sig"))
    scoring_payload_path = repo_root / sources["week_zero_official_finals"]["payload_relative_path"]
    scoring_payload = json.loads(scoring_payload_path.read_text(encoding="utf-8-sig"))

    ranking_manifest_path = data_root / sources["current_rankings"]["manifest_relative_path"]
    ranking_manifest = json.loads(ranking_manifest_path.read_text(encoding="utf-8-sig"))
    if ranking_manifest.get("capture_identity") != sources["current_rankings"]["capture_identity"]:
        raise Week1FeatureSpineViolation("ranking capture identity drifted from the contract")
    ranking_capture = next(
        row for row in ranking_manifest["captures"] if row["state"] == "CAPTURED"
    )
    ranking_raw_path = data_root / ranking_capture["raw_relative_path"]
    if sha256_file(ranking_raw_path) != ranking_capture["raw_sha256"]:
        raise Week1FeatureSpineViolation("ranking raw capture hash drifted")
    poll = parse_ranking_document(ranking_raw_path.read_text(encoding="utf-8", errors="replace"))

    weather_manifest_path = data_root / sources["weather_vintage"]["manifest_relative_path"]
    weather_manifest = json.loads(weather_manifest_path.read_text(encoding="utf-8-sig"))
    if weather_manifest.get("capture_identity") != sources["weather_vintage"]["capture_identity"]:
        raise Week1FeatureSpineViolation("weather capture identity drifted from the contract")
    vintages = index_weather_vintages(weather_manifest["captures"])
    forecast_periods: dict[str, list[dict[str, Any]]] = {}
    for team_id, vintage in vintages.items():
        forecast_path = data_root / vintage["forecast_raw_relative_path"]
        if sha256_file(forecast_path) != vintage["forecast_raw_sha256"]:
            raise Week1FeatureSpineViolation(f"weather forecast hash drifted for {team_id}")
        forecast_periods[team_id] = json.loads(forecast_path.read_text(encoding="utf-8"))[
            "properties"
        ]["periods"]

    candidate_gate_path = (
        repo_root / sources["frozen_prior_domain"]["candidate_gate_relative_path"]
    )
    candidate_gate = json.loads(candidate_gate_path.read_text(encoding="utf-8-sig"))
    frozen_gate_path = (
        repo_root / sources["frozen_prior_domain"]["frozen_forecast_gate_relative_path"]
    )
    frozen_gate = json.loads(frozen_gate_path.read_text(encoding="utf-8-sig"))
    frozen_rows = read_jsonl(
        canonical_payload_path(
            frozen_gate, data_root, sources["frozen_prior_domain"]["frozen_forecast_payload_name"]
        )
    )
    absence_reasons = sorted(
        {
            str(row["abstention_reason"])
            for row in frozen_rows
            if row.get("abstention_state") == "MISSING_REQUIRED_FEATURES_ABSTAIN"
            and row.get("candidate_id") == "prior_only"
        }
    )
    if not absence_reasons:
        raise Week1FeatureSpineViolation(
            "the frozen predecessor does not record why the prior domain is unmaterialized"
        )

    return {
        "contract": contract,
        "contract_sha256": sha256_file(repo_root / CONTRACT_RELATIVE),
        "contests": contests,
        "participants": participants,
        "aliases": aliases,
        "week_zero": index_week_zero_finals(scoring_payload["orientation_proofs"]),
        "poll": poll,
        "ranking_capture": {
            "poll_id": ranking_manifest["captures"][0]["poll_id"],
            "capture_identity": ranking_manifest["capture_identity"],
            "raw_sha256": ranking_capture["raw_sha256"],
            "raw_relative_path": ranking_capture["raw_relative_path"],
            "retrieved_at_utc": ranking_capture["retrieved_at_utc"],
            "source_uri": ranking_capture["source_uri"],
            "manifest_relative_path": sources["current_rankings"]["manifest_relative_path"],
        },
        "weather": vintages,
        "forecast_periods": forecast_periods,
        "weather_evidence": {
            "manifest_relative_path": sources["weather_vintage"]["manifest_relative_path"],
            "manifest_sha256": sha256_file(weather_manifest_path),
            "capture_identity": weather_manifest["capture_identity"],
            "provider": weather_manifest["provider"],
            "product": weather_manifest["product"],
            "captured_site_count": weather_manifest["captured_count"],
            "failed_site_count": weather_manifest["failed_count"],
            "venue_coordinate_authority": sources["weather_vintage"][
                "venue_coordinate_authority"
            ],
            "venue_coordinate_is_official_2026_venue_evidence": False,
            "observed_postgame_weather_used": False,
        },
        "prior_evidence": {
            "candidate_source": sources["frozen_prior_domain"]["candidate_gate_relative_path"],
            "candidate_gate_identity": candidate_gate["gate_identity"],
            "candidate_gate_sha256": sha256_file(candidate_gate_path),
            "frozen_forecast_gate_identity": frozen_gate["gate_identity"],
            "retraining_performed": False,
            "week_zero_outcomes_updated_a_prior": False,
            "absence_reason": absence_reasons[0],
            "absence_reasons": absence_reasons,
        },
        "bound_predecessors": {
            "week1_schedule_identity_gate_identity": schedule_gate["gate_identity"],
            "week1_schedule_identity_gate_sha256": sha256_file(schedule_gate_path),
            "week_zero_official_final_scoring_gate_identity": scoring_gate["gate_identity"],
            "week_zero_official_final_scoring_gate_sha256": sha256_file(scoring_gate_path),
            "week_zero_official_final_scoring_payload_sha256": sha256_file(scoring_payload_path),
            "national_expectation_baselines_gate_identity": candidate_gate["gate_identity"],
            "prospective_shadow_forecast_gate_identity": frozen_gate["gate_identity"],
            "entity_alias_authority_gate_identity": alias_gate["gate_identity"],
            "entity_alias_authority_gate_sha256": sha256_file(alias_gate_path),
            "current_ranking_capture_identity": ranking_manifest["capture_identity"],
            "weather_vintage_capture_identity": weather_manifest["capture_identity"],
        },
    }


def build(repo_root: Path, data_root: Path, execution_time: datetime) -> dict[str, Any]:
    inputs = load_inputs(repo_root, data_root)
    rankings = index_rankings(
        inputs["poll"]["entries"], inputs["participants"], inputs["aliases"]
    )
    rows, cells = build_spine_rows(
        contract=inputs["contract"],
        contests=inputs["contests"],
        participants=inputs["participants"],
        rankings=rankings,
        ranking_capture=inputs["ranking_capture"],
        publication_authority_text=inputs["poll"]["publication_authority_text"],
        week_zero=inputs["week_zero"],
        weather=inputs["weather"],
        forecast_periods=inputs["forecast_periods"],
        prior_evidence=inputs["prior_evidence"],
        snapshot_issuance=execution_time,
    )
    assert_future_append_invariance(rows, cells)

    payloads = [
        write_payload(data_root, ROW_PAYLOAD_NAME, rows),
        write_payload(data_root, CELL_PAYLOAD_NAME, cells),
    ]
    ranking_evidence = {
        **inputs["ranking_capture"],
        "publication_authority_text": inputs["poll"]["publication_authority_text"],
        "poll_entry_count": len(inputs["poll"]["entries"]),
        "bound_participant_count": len(rankings["by_source_team_id"]),
        "unmatched_poll_entries": rankings["unmatched_poll_entries"],
        "conflicting_poll_entries": rankings["conflicting_poll_entries"],
        "poll_coverage_complete": rankings["poll_coverage_complete"],
        "alias_authorities": inputs["contract"]["sources"]["current_rankings"][
            "alias_authorities"
        ],
        "unbound_poll_entry_policy": inputs["contract"]["sources"]["current_rankings"][
            "unbound_poll_entry_policy"
        ],
        "join_method": inputs["contract"]["sources"]["current_rankings"]["join_method"],
        "join_is_consumed_by_a_model": False,
        "unranked_encoding": inputs["contract"]["sources"]["current_rankings"]["unranked_encoding"],
    }

    summary = summarize(rows, cells)
    manifest = dataset_manifest(
        contract=inputs["contract"],
        summary=summary,
        source_inventory=[
            {
                "domain": "CURRENT_RANKING",
                "manifest_relative_path": inputs["ranking_capture"]["manifest_relative_path"],
                "capture_identity": inputs["ranking_capture"]["capture_identity"],
                "raw_sha256": inputs["ranking_capture"]["raw_sha256"],
                "retrieved_at_utc": inputs["ranking_capture"]["retrieved_at_utc"],
            },
            {
                "domain": "WEATHER_VINTAGE",
                "manifest_relative_path": inputs["weather_evidence"]["manifest_relative_path"],
                "capture_identity": inputs["weather_evidence"]["capture_identity"],
                "manifest_sha256": inputs["weather_evidence"]["manifest_sha256"],
                "captured_site_count": inputs["weather_evidence"]["captured_site_count"],
            },
        ],
        payloads=payloads,
        snapshot_issuance=execution_time,
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
        rows=rows,
        cells=cells,
        ranking_evidence=ranking_evidence,
        weather_evidence=inputs["weather_evidence"],
        prior_evidence=inputs["prior_evidence"],
        manifest_relative_path=manifest_relative,
        manifest_sha256=sha256_file(manifest_path),
        dataset_identity=manifest["dataset_identity"],
        payloads=[
            {key: value for key, value in payload.items() if key != "relative_path"}
            for payload in payloads
        ],
        bound_predecessors=inputs["bound_predecessors"],
        snapshot_issuance=execution_time,
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
    except Week1FeatureSpineViolation as exc:
        print(f"week 1 feature spine violation: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"gate_identity": gate["gate_identity"], "summary": gate["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
