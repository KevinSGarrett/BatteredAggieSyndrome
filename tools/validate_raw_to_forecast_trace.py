"""Validate raw-to-feature-to-forecast traces without producer helpers."""

from __future__ import annotations

import argparse
import json
import re
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
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
IDENTITY_FIELDS = (
    "raw_source_identity",
    "canonical_game_id",
    "feature_row_identity",
    "forecast_row_identity",
    "current_opponent_key",
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_trace(row: dict[str, Any]) -> list[str]:
    findings = [
        f"TRACE_MISSING:{field}" for field in REQUIRED_TRACE_FIELDS if field not in row
    ]
    if all(row.get(field) is None for field in REQUIRED_TRACE_FIELDS if field in row) and not findings:
        findings.append("TRACE_NULL_ONLY")
    for field in IDENTITY_FIELDS:
        if field in row and not _nonempty(row.get(field)):
            findings.append(f"TRACE_EMPTY_ID:{field}")
    digest = row.get("raw_sha256")
    if "raw_sha256" in row and not (isinstance(digest, str) and SHA256_RE.fullmatch(digest)):
        findings.append("TRACE_HASH_MALFORMED")
    if row.get("copied_from_terminal_historical_row") is True:
        findings.append("TRACE_HISTORICAL_TRANSPLANT")
    if row.get("target_outcome_read") is True:
        findings.append("TRACE_TARGET_OUTCOME_READ")
    return findings


def validate_payload(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if not payload:
        return ["TRACE_PAYLOAD_EMPTY"]
    if "traces" not in payload:
        return ["TRACE_POPULATION_MISSING"]
    traces = payload.get("traces")
    if not isinstance(traces, list):
        return ["TRACE_POPULATION_NOT_LIST"]
    expected = payload.get("expected_opportunity_ids")
    if expected is None:
        findings.append("TRACE_EXPECTED_POPULATION_MISSING")
        expected_ids: list[str] = []
    else:
        if not isinstance(expected, list) or not all(isinstance(item, str) and item.strip() for item in expected):
            return ["TRACE_EXPECTED_POPULATION_INVALID"]
        expected_ids = list(expected)
    if not traces:
        if expected_ids:
            findings.append("TRACE_EMPTY_UNEXPECTED_POPULATION")
        else:
            findings.append("TRACE_EMPTY_COHORT_WITHOUT_ACCOUNTING")
        return findings
    seen_forecast: set[str] = set()
    for index, row in enumerate(traces):
        if not isinstance(row, dict):
            findings.append(f"{index}:TRACE_ROW_NOT_OBJECT")
            continue
        if all(value is None for value in row.values()):
            findings.append(f"{index}:TRACE_NULL_ONLY")
        for item in validate_trace(row):
            findings.append(f"{index}:{item}")
        forecast_id = str(row.get("forecast_row_identity") or "")
        if forecast_id:
            if forecast_id in seen_forecast:
                findings.append(f"{index}:TRACE_DUPLICATE_FORECAST_IDENTITY")
            seen_forecast.add(forecast_id)
    if expected_ids:
        emitted = {
            str(row.get("canonical_game_id") or "")
            for row in traces
            if isinstance(row, dict)
        }
        missing = sorted(set(expected_ids) - emitted)
        if missing:
            findings.append(f"TRACE_UNACCOUNTED_OPPORTUNITIES:{len(missing)}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=False)
    args = parser.parse_args(argv)
    findings: list[str] = []
    if not args.payload:
        findings = ["TRACE_PAYLOAD_EMPTY"]
    else:
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
