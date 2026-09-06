"""Validate cross-output scientific coherence without producer helpers."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.scientific_reference.coherence import (  # noqa: E402
    joint_distribution_coherent,
    pair_normalize,
)

REQUIRED_ROW_FIELDS = (
    "home_win_probability",
    "away_win_probability",
    "expected_margin_home",
    "expected_margin_away",
)


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
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
    if not _nonempty(source):
        return False
    if authority.get("caller_provided_empty_list") is True:
        return False
    return True


def _opportunity_key(row: dict[str, Any]) -> str:
    if _nonempty(row.get("opportunity_id")):
        return str(row["opportunity_id"]).strip()
    parts = [
        row.get("candidate_id") or row.get("candidate_version"),
        row.get("canonical_game_id") or row.get("game_id"),
        row.get("checkpoint_id") or row.get("checkpoint"),
    ]
    if all(_nonempty(str(item) if item is not None else "") for item in parts):
        return "|".join(str(item).strip() for item in parts)
    if _nonempty(row.get("canonical_game_id")):
        return str(row["canonical_game_id"]).strip()
    if _nonempty(row.get("forecast_row_identity")):
        return str(row["forecast_row_identity"]).strip()
    return ""


def _is_abstention(row: dict[str, Any]) -> bool:
    if row.get("abstained") is True:
        return True
    reason = row.get("abstain_reason") or row.get("trust_classification")
    if isinstance(reason, str) and reason.upper().startswith("ABSTAIN"):
        return True
    return False


def _interval_distribution_findings(index: int, row: dict[str, Any]) -> list[str]:
    """Invariant 5: p, margin, and interval must share one declared distribution."""
    lower = row.get("interval_lower")
    upper = row.get("interval_upper")
    level = row.get("interval_nominal_level")
    declared = row.get("distribution_identity")
    interval_distribution = row.get("interval_distribution_identity")
    present = [
        item is not None
        for item in (lower, upper, level, declared, interval_distribution)
    ]
    if not any(present):
        return []
    findings: list[str] = []
    if not all(item is not None for item in (lower, upper, level, declared)):
        findings.append(f"CROSS_OUTPUT_INTERVAL_FIELDS_INCOMPLETE:{index}")
        return findings
    if (
        not _finite_number(lower)
        or not _finite_number(upper)
        or not _finite_number(level)
    ):
        findings.append(f"CROSS_OUTPUT_INTERVAL_NONFINITE:{index}")
        return findings
    if not _nonempty(declared):
        findings.append(f"CROSS_OUTPUT_DISTRIBUTION_IDENTITY_EMPTY:{index}")
    if interval_distribution is not None and str(interval_distribution) != str(
        declared
    ):
        findings.append(
            f"CROSS_OUTPUT_INCOHERENT:{index}:ABSTAIN_PROBABILITY_DISTRIBUTION_INCOHERENCE"
        )
        return findings
    stdev = row.get("residual_stdev")
    if stdev is None:
        return findings
    if not _finite_number(stdev):
        findings.append(f"CROSS_OUTPUT_INTERVAL_NONFINITE:{index}")
        return findings
    reconstructed = joint_distribution_coherent(
        {
            "expected_margin_home": row.get("expected_margin_home"),
            "home_win_probability": row.get("home_win_probability"),
            "interval_lower": lower,
            "interval_upper": upper,
        },
        residual_stdev=float(stdev),
        interval_mass=float(level),
    )
    if not reconstructed["coherent"]:
        findings.append(
            f"CROSS_OUTPUT_INCOHERENT:{index}:{reconstructed['abstain_reason']}"
        )
    return findings


def validate_rows(rows: list[dict]) -> list[str]:
    findings: list[str] = []
    seen_keys: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.append(f"CROSS_OUTPUT_ROW_NOT_OBJECT:{index}")
            continue
        key = _opportunity_key(row)
        if key:
            if key in seen_keys:
                findings.append(f"CROSS_OUTPUT_DUPLICATE_KEY:{index}:{key}")
            seen_keys.add(key)
        if _is_abstention(row):
            hidden = any(
                _finite_number(row.get(field)) and float(row.get(field)) not in {0.0}
                for field in ("home_win_probability", "away_win_probability")
                if row.get(field) is not None
            )
            if hidden and not row.get("emit_hidden_probability_explicitly"):
                findings.append(f"CROSS_OUTPUT_ABSTENTION_HIDDEN_P:{index}")
            continue
        missing = [field for field in REQUIRED_ROW_FIELDS if field not in row]
        if missing:
            findings.append(f"CROSS_OUTPUT_MISSING_FIELDS:{index}:{','.join(missing)}")
            continue
        values = [row[field] for field in REQUIRED_ROW_FIELDS]
        if any(not _finite_number(item) for item in values):
            findings.append(f"CROSS_OUTPUT_NONFINITE:{index}")
            continue
        home_p = float(row["home_win_probability"])
        away_p = float(row["away_win_probability"])
        if home_p not in {0.0, 1.0} and not (0.0 <= home_p <= 1.0):
            findings.append(f"CROSS_OUTPUT_PROBABILITY_OUT_OF_RANGE:{index}")
        if home_p > 1.0 or away_p > 1.0 or home_p < 0.0 or away_p < 0.0:
            findings.append(f"CROSS_OUTPUT_INVALID_P_NOT_NORMALIZABLE:{index}")
        result = pair_normalize(
            home_p,
            away_p,
            float(row["expected_margin_home"]),
            float(row["expected_margin_away"]),
        )
        if not result["coherent"]:
            findings.append(
                f"CROSS_OUTPUT_INCOHERENT:{index}:{result['abstain_reason']}"
            )
        findings.extend(_interval_distribution_findings(index, row))
        schema = row.get("schema_version")
        if schema is not None and not _nonempty(schema):
            findings.append(f"CROSS_OUTPUT_SCHEMA_EMPTY:{index}")
        child = row.get("child_sha256") or row.get("payload_sha256")
        if child is not None and (
            not isinstance(child, str) or len(child) != 64 or child == "0" * 64
        ):
            findings.append(f"CROSS_OUTPUT_CHILD_HASH_INVALID:{index}")
    return findings


def validate_payload(payload: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if "rows" not in payload:
        return ["CROSS_OUTPUT_POPULATION_MISSING"]
    rows = payload.get("rows")
    if not isinstance(rows, list):
        return ["CROSS_OUTPUT_POPULATION_NOT_LIST"]
    expected = payload.get("expected_opportunity_ids")
    if expected is None:
        findings.append("CROSS_OUTPUT_EXPECTED_POPULATION_MISSING")
        expected_ids: list[str] = []
    else:
        if not isinstance(expected, list) or not all(
            isinstance(item, str) and item.strip() for item in expected
        ):
            return ["CROSS_OUTPUT_EXPECTED_POPULATION_INVALID"]
        expected_ids = list(expected)
    if not rows:
        if expected_ids:
            findings.append("CROSS_OUTPUT_EMPTY_UNEXPECTED_POPULATION")
        elif not _independent_empty_universe(payload):
            findings.append("CROSS_OUTPUT_EMPTY_COHORT_WITHOUT_AUTHORITY")
        return findings
    findings.extend(validate_rows(rows))
    emitted = {_opportunity_key(row) for row in rows if isinstance(row, dict)}
    emitted.discard("")
    if expected_ids:
        missing = sorted(set(expected_ids) - emitted)
        extra = sorted(emitted - set(expected_ids))
        if missing:
            findings.append(f"CROSS_OUTPUT_UNACCOUNTED_OPPORTUNITIES:{len(missing)}")
        if extra:
            findings.append(f"CROSS_OUTPUT_EXTRA_OPPORTUNITIES:{len(extra)}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=False)
    args = parser.parse_args(argv)
    findings: list[str] = []
    if not args.payload:
        findings = ["CROSS_OUTPUT_PAYLOAD_MISSING"]
    else:
        path = Path(args.payload)
        if not path.is_file():
            findings = ["CROSS_OUTPUT_PAYLOAD_MISSING"]
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
            findings = validate_payload(payload)
    print(
        json.dumps(
            {
                "validator": "cross_output_coherence",
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
