"""Validate raw-to-feature-to-forecast traces without producer helpers."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TRACE_FIELDS = (
    "raw_source_identity",
    "raw_sha256",
    "canonical_game_id",
    "feature_row_identity",
    "forecast_row_identity",
    "known_at_utc",
    "cutoff_utc",
    "current_opponent_key",
    "trust_classification",
)


def validate_trace(row: dict[str, Any]) -> list[str]:
    findings = [
        f"TRACE_MISSING:{field}" for field in REQUIRED_TRACE_FIELDS if field not in row
    ]
    if row.get("copied_from_terminal_historical_row") is True:
        findings.append("TRACE_HISTORICAL_TRANSPLANT")
    if row.get("target_outcome_read") is True:
        findings.append("TRACE_TARGET_OUTCOME_READ")
    return findings


def validate_payload(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for index, row in enumerate(payload.get("traces") or []):
        for item in validate_trace(row):
            findings.append(f"{index}:{item}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=False)
    args = parser.parse_args(argv)
    findings: list[str] = []
    if args.payload:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        findings = validate_payload(payload)
    print(
        json.dumps(
            {
                "validator": "raw_to_forecast_trace",
                "result": "PASS" if not findings else "FAIL",
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
