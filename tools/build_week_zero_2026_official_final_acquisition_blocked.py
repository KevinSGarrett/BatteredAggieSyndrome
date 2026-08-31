"""Materialize fail-closed Week Zero official-final acquisition blocked evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

NON_AUTHORITATIVE_KEYS = frozenset({"gate_identity"})


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.as_posix()} must contain a JSON object")
    return value


def canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        {key: value for key, value in payload.items() if key not in NON_AUTHORITATIVE_KEYS},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_utc(value: str | None) -> str:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    else:
        parsed = datetime.now(timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def latest_capture_manifest(data_root: Path) -> dict[str, Any]:
    root = data_root / "manifests" / "shadow" / "week_zero_2026_live_execution" / "sha256"
    candidates = sorted(root.glob("*/week_zero_2026_live_execution_capture_manifest.json"))
    if not candidates:
        raise ValueError("no Week Zero live execution capture manifest exists")
    manifests = [read_json(path) for path in candidates]
    manifests.sort(key=lambda item: str(item.get("issued_at_utc")))
    return manifests[-1]


def load_capture_manifest(data_root: Path, capture_identity: str) -> dict[str, Any]:
    path = (
        data_root
        / "manifests"
        / "shadow"
        / "week_zero_2026_live_execution"
        / "sha256"
        / capture_identity
        / "week_zero_2026_live_execution_capture_manifest.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"capture manifest missing: {path}")
    return read_json(path)


def most_recent_successful_capture(data_root: Path) -> dict[str, Any] | None:
    root = data_root / "manifests" / "shadow" / "week_zero_2026_live_execution" / "sha256"
    candidates = sorted(root.glob("*/week_zero_2026_live_execution_capture_manifest.json"))
    successful: list[dict[str, Any]] = []
    for path in candidates:
        payload = read_json(path)
        if int(payload.get("captured_count") or 0) > 0:
            successful.append(payload)
    if not successful:
        return None
    successful.sort(key=lambda item: str(item.get("issued_at_utc")))
    return successful[-1]


def build_blocked_gate(
    *,
    repo_root: Path,
    data_root: Path,
    capture_manifest: Mapping[str, Any],
    issued_at_utc: str,
) -> dict[str, Any]:
    contract = read_json(
        repo_root / "configs" / "week_zero_2026_official_final_scoring_successor_contract.json"
    )
    successor_gate = read_json(
        repo_root / "artifacts" / "shadow" / "week_zero_2026_official_final_scoring_successor_gate.json"
    )
    if any(str(item.get("state")) != "TECHNICALLY_UNAVAILABLE" for item in capture_manifest.get("captures", [])):
        raise ValueError("capture is not fully blocked; refuse blocked-gate materialization")
    prior_success = most_recent_successful_capture(data_root)

    gate = {
        "schema_version": "aggie.shadow.week_zero_2026_official_final_acquisition_blocked.v1",
        "artifact_type": "WEEK_ZERO_2026_OFFICIAL_FINAL_ACQUISITION_BLOCKED_GATE",
        "result": "FAIL_CLOSED_OFFICIAL_FINAL_ACQUISITION_BLOCKED",
        "jira_key": "BAT-674",
        "local_issue_id": "POST-TASK-2026-WEEK-ZERO-OFFICIAL-FINAL-SCORING-001",
        "lane": "PROSPECTIVE_SHADOW_OBSERVATION_ONLY",
        "contract_id": contract["contract_id"],
        "requested_game_dates": ["2026-08-27", "2026-08-28", "2026-08-29"],
        "official_route": dict(contract["source"]),
        "attempted_capture_identity": capture_manifest.get("capture_identity"),
        "attempted_capture_issued_at_utc": capture_manifest.get("issued_at_utc"),
        "attempts_by_date": [
            {
                "game_date": row.get("game_date"),
                "failure_condition": row.get("failure_condition", "UNKNOWN"),
                "source_uri": row.get("source_uri"),
                "request_identity_sha256": row.get("request_identity_sha256"),
                "attempts": row.get("attempts", []),
            }
            for row in capture_manifest.get("captures", [])
        ],
        "fallback_route_audit": {
            "declared_public_official_fallback_routes": [],
            "audit_result": (
                "NO_DECLARED_PUBLIC_OFFICIAL_FALLBACK_ROUTES_FOR_ALL_EIGHT_WEEK_ZERO_CONTESTS"
            ),
            "policy": "DO_NOT_USE_UNOFFICIAL_OR_UNDECLARED_FALLBACKS",
        },
        "state_protection": {
            "bound_predecessor_gate_identity": contract["predecessor_authority"]["gate_identity"],
            "bound_successor_gate_identity": successor_gate.get("gate_identity"),
            "successor_contest_state_counts": successor_gate.get("contest_state_counts"),
            "successor_forecast_state_counts": successor_gate.get("forecast_state_counts"),
            "scored_row_count": successor_gate.get("metrics", {}).get("scored_row_count"),
            "frozen_probability_mutation_performed": False,
            "forecast_backfill_performed": False,
        },
        "prior_successful_capture_context": (
            None
            if prior_success is None
            else {
                "capture_identity": prior_success.get("capture_identity"),
                "issued_at_utc": prior_success.get("issued_at_utc"),
                "captured_count": prior_success.get("captured_count"),
                "official_final_count": len(prior_success.get("official_finals", [])),
            }
        ),
        "reconstruction_bindings": {
            "attempted_capture_manifest_path": str(
                (
                    data_root
                    / "manifests"
                    / "shadow"
                    / "week_zero_2026_live_execution"
                    / "sha256"
                    / str(capture_manifest.get("capture_identity"))
                    / "week_zero_2026_live_execution_capture_manifest.json"
                )
            ),
            "successor_gate_path": "artifacts/shadow/week_zero_2026_official_final_scoring_successor_gate.json",
            "successor_replay_path": "artifacts/shadow/week_zero_2026_official_final_scoring_successor_replay.json",
            "successor_scoring_payload_path": "artifacts/shadow/week_zero_2026_official_final_scoring_successor_payload.json",
            "successor_residual_payload_path": "artifacts/shadow/week_zero_2026_prospective_residual_successor_payload.json",
            "successor_transition_ledger_path": "artifacts/shadow/week_zero_2026_official_final_scoring_successor_state_transitions.json",
        },
        "negative_findings": {
            "unofficial_source_substitution_performed": False,
            "undeclared_credential_requested": False,
            "scoring_claimed_without_official_final": False,
        },
        "issued_at_utc": issued_at_utc,
    }
    gate["gate_identity"] = canonical_hash(gate)
    return gate


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--capture-identity", default=None)
    parser.add_argument("--issued-at-utc", default=None)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    data_root = args.data_root.resolve()
    issued_at_utc = parse_utc(args.issued_at_utc)
    capture = (
        latest_capture_manifest(data_root)
        if args.capture_identity is None
        else load_capture_manifest(data_root, args.capture_identity)
    )
    gate = build_blocked_gate(
        repo_root=repo_root,
        data_root=data_root,
        capture_manifest=capture,
        issued_at_utc=issued_at_utc,
    )
    gate_path = repo_root / "artifacts" / "shadow" / "week_zero_2026_official_final_acquisition_blocked_gate.json"
    replay_path = repo_root / "artifacts" / "shadow" / "week_zero_2026_official_final_acquisition_blocked_replay.json"
    write_json(gate_path, gate)
    write_json(
        replay_path,
        {
            "result": gate["result"],
            "gate_identity": gate["gate_identity"],
            "attempted_capture_identity": gate["attempted_capture_identity"],
            "state_protection": gate["state_protection"],
            "replay_command": (
                "python -B tools/build_week_zero_2026_official_final_acquisition_blocked.py "
                "--repo-root . --data-root <data-root>"
            ),
        },
    )
    print(
        json.dumps(
            {
                "result": gate["result"],
                "gate_identity": gate["gate_identity"],
                "attempted_capture_identity": gate["attempted_capture_identity"],
                "scored_row_count": gate["state_protection"]["scored_row_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
