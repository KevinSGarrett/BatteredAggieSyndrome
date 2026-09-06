"""Validate raw-to-feature-to-forecast traces without producer helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.scientific_reference.binding import (  # noqa: E402
    current_opponent_bound,
    temporal_order_ok,
)

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
ZERO_HASH = "0" * 64
IDENTITY_FIELDS = (
    "raw_source_identity",
    "canonical_game_id",
    "feature_row_identity",
    "forecast_row_identity",
    "current_opponent_key",
)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _independent_empty_universe(payload: dict[str, Any]) -> bool:
    authority = payload.get("empty_universe_authority")
    if not isinstance(authority, dict):
        return False
    if authority.get("empty_universe_authorized") is not True:
        return False
    source = authority.get("independent_source_identity") or authority.get(
        "pinned_cohort_contract_identity"
    )
    return _nonempty(source) and authority.get("caller_provided_empty_list") is not True


def _opportunity_key(row: dict[str, Any]) -> str:
    if _nonempty(row.get("opportunity_id")):
        return str(row["opportunity_id"]).strip()
    parts = [
        row.get("candidate_id") or row.get("candidate_version"),
        row.get("canonical_game_id"),
        row.get("checkpoint_id") or row.get("checkpoint"),
    ]
    if all(_nonempty(str(item) if item is not None else "") for item in parts):
        return "|".join(str(item).strip() for item in parts)
    if _nonempty(row.get("canonical_game_id")):
        return str(row["canonical_game_id"]).strip()
    return ""


def _resolve_raw_bytes(
    row: dict[str, Any], payload: dict[str, Any], data_root: Path | None
) -> bytes | None:
    inline = row.get("raw_bytes")
    if isinstance(inline, (bytes, bytearray)):
        return bytes(inline)
    if isinstance(inline, str) and inline:
        return inline.encode("utf-8")
    rel = row.get("raw_bytes_path") or row.get("raw_path")
    roots: list[Path] = []
    if data_root is not None:
        roots.append(data_root)
    payload_root = payload.get("data_root")
    if isinstance(payload_root, str) and payload_root.strip():
        roots.append(Path(payload_root))
    if _nonempty(rel):
        candidate = Path(str(rel))
        if candidate.is_file():
            return candidate.read_bytes()
        for root in roots:
            path = root / str(rel)
            if path.is_file():
                return path.read_bytes()
    return None


def validate_trace(
    row: dict[str, Any],
    *,
    payload: dict[str, Any] | None = None,
    data_root: Path | None = None,
) -> list[str]:
    payload = payload or {}
    findings = [
        f"TRACE_MISSING:{field}" for field in REQUIRED_TRACE_FIELDS if field not in row
    ]
    if (
        all(row.get(field) is None for field in REQUIRED_TRACE_FIELDS if field in row)
        and not findings
    ):
        findings.append("TRACE_NULL_ONLY")
    for field in IDENTITY_FIELDS:
        if field in row and not _nonempty(row.get(field)):
            findings.append(f"TRACE_EMPTY_ID:{field}")
    digest = row.get("raw_sha256")
    if "raw_sha256" in row and not (
        isinstance(digest, str) and SHA256_RE.fullmatch(digest)
    ):
        findings.append("TRACE_HASH_MALFORMED")
    elif isinstance(digest, str) and digest == ZERO_HASH:
        findings.append("TRACE_FAKE_HASH")
    if isinstance(digest, str) and SHA256_RE.fullmatch(digest) and digest != ZERO_HASH:
        raw = _resolve_raw_bytes(row, payload, data_root)
        if raw is None:
            findings.append("TRACE_RAW_BYTES_UNRESOLVED")
        else:
            actual = hashlib.sha256(raw).hexdigest()
            if actual != digest:
                findings.append("TRACE_HASH_MISMATCH")
    known = row.get("known_at_utc")
    cutoff = row.get("cutoff_utc")
    if _nonempty(known) and _nonempty(cutoff):
        try:
            if not temporal_order_ok(
                str(known), str(cutoff), acquisition_utc=row.get("acquisition_utc")
            ):
                findings.append("TRACE_FUTURE_KNOWN_AT")
        except ValueError:
            findings.append("TRACE_TIME_UNPARSEABLE")
        as_of = payload.get("as_of_utc")
        if _nonempty(as_of):
            try:
                if not temporal_order_ok(str(known), str(as_of)):
                    findings.append("TRACE_FUTURE_KNOWN_AT")
            except ValueError:
                findings.append("TRACE_AS_OF_UNPARSEABLE")
    if row.get("copied_from_terminal_historical_row") is True:
        findings.append("TRACE_HISTORICAL_TRANSPLANT")
    if row.get("target_outcome_read") is True:
        findings.append("TRACE_TARGET_OUTCOME_READ")
    contest = row.get("current_contest") or payload.get("current_contest")
    if isinstance(contest, dict) and any(
        row.get(field) for field in ("team_key", "opponent_key", "current_opponent_key")
    ):
        target = {
            "team_key": row.get("team_key") or row.get("canonical_team_id"),
            "opponent_key": row.get("opponent_key") or row.get("current_opponent_key"),
            "copied_from_terminal_historical_row": row.get(
                "copied_from_terminal_historical_row"
            ),
        }
        bound = current_opponent_bound(target, contest)
        if not bound["bound"]:
            findings.append(f"TRACE_WRONG_OPPONENT:{bound['reason']}")
    expected_opponent = row.get("expected_current_opponent_key") or payload.get(
        "expected_current_opponent_key"
    )
    if _nonempty(expected_opponent) and _nonempty(row.get("current_opponent_key")):
        if str(row["current_opponent_key"]).strip() != str(expected_opponent).strip():
            findings.append("TRACE_WRONG_OPPONENT:KEY_MISMATCH")
    return findings


def validate_payload(
    payload: dict[str, Any], *, data_root: Path | None = None
) -> list[str]:
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
        if not isinstance(expected, list) or not all(
            isinstance(item, str) and item.strip() for item in expected
        ):
            return ["TRACE_EXPECTED_POPULATION_INVALID"]
        expected_ids = list(expected)
    if not traces:
        if expected_ids:
            findings.append("TRACE_EMPTY_UNEXPECTED_POPULATION")
        elif not _independent_empty_universe(payload):
            findings.append("TRACE_EMPTY_COHORT_WITHOUT_AUTHORITY")
        return findings
    seen_forecast: set[str] = set()
    traced_keys: set[str] = set()
    for index, row in enumerate(traces):
        if not isinstance(row, dict):
            findings.append(f"{index}:TRACE_ROW_NOT_OBJECT")
            continue
        if all(value is None for value in row.values()):
            findings.append(f"{index}:TRACE_NULL_ONLY")
        for item in validate_trace(row, payload=payload, data_root=data_root):
            findings.append(f"{index}:{item}")
        forecast_id = str(row.get("forecast_row_identity") or "")
        if forecast_id:
            if forecast_id in seen_forecast:
                findings.append(f"{index}:TRACE_DUPLICATE_FORECAST_IDENTITY")
            seen_forecast.add(forecast_id)
        key = _opportunity_key(row)
        if key:
            traced_keys.add(key)
    if expected_ids:
        missing = sorted(set(expected_ids) - traced_keys)
        extra = sorted(traced_keys - set(expected_ids))
        if missing:
            findings.append(f"TRACE_UNACCOUNTED_OPPORTUNITIES:{len(missing)}")
            findings.append(f"TRACE_UNTRACED_ROWS:{len(missing)}")
        if extra:
            findings.append(f"TRACE_EXTRA_TRACES:{len(extra)}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=False)
    parser.add_argument("--data-root", required=False)
    args = parser.parse_args(argv)
    findings: list[str] = []
    data_root = Path(args.data_root) if args.data_root else None
    if not args.payload:
        findings = ["TRACE_PAYLOAD_EMPTY"]
    else:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        findings = validate_payload(payload, data_root=data_root)
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
