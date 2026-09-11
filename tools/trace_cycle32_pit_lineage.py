"""Independently re-check predecessor PROVEN PIT rows. Do not invent a count."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.pit_kernel import (  # noqa: E402
    PROVEN,
    PitKernelError,
    validate_row_authority,
)

PRED = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)
FEATURE_KEYS = (
    "pit_prior_games_played",
    "pit_prior_margin_mean",
    "pit_prior_points_against_mean",
    "pit_prior_points_for_mean",
    "pit_prior_season_win_rate",
    "pit_prior_win_rate",
    "pit_season_to_date_games",
    "pit_season_to_date_win_rate",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def limiting_keys(row: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    authority = row.get("authority") if isinstance(row.get("authority"), dict) else {}
    for field in (
        "source_id",
        "effective_utc",
        "known_at_utc",
        "receipt_sha256",
        "classification",
        "evidence_class",
        "source_publication_utc",
    ):
        if not (authority or {}).get(field) and not row.get(field):
            missing.append(f"authority.{field}")
    if row.get("ordinary_home_exposure") is None:
        missing.append("ordinary_home_exposure")
    if str(row.get("site_class") or "") in {"", "UNKNOWN"}:
        missing.append("site_class")
    for side in ("home_features", "away_features"):
        feat = row.get(side) or {}
        for key in FEATURE_KEYS:
            if key not in feat:
                missing.append(f"{side}.{key}")
            elif feat.get(key) is None and key in {
                "pit_prior_margin_mean",
                "pit_prior_games_played",
            }:
                missing.append(f"{side}.{key}=null")
    if not row.get("contributing_event_ids"):
        missing.append("contributing_event_ids")
    if not row.get("frozen_input_identity"):
        missing.append("frozen_input_identity")
    return missing


def independent_verdict(row: dict[str, Any]) -> str:
    authority = row.get("authority") if isinstance(row.get("authority"), dict) else {}
    payload = {
        "source_id": authority.get("source_id") or row.get("source_id"),
        "effective_utc": authority.get("effective_utc") or row.get("effective_utc"),
        "known_at_utc": authority.get("known_at_utc") or row.get("known_at_utc"),
        "receipt_sha256": authority.get("receipt_sha256") or row.get("receipt_sha256"),
        "classification": authority.get("classification")
        or row.get("classification")
        or row.get("authority_class"),
        "evidence_class": authority.get("evidence_class") or row.get("evidence_class"),
        "source_publication_utc": authority.get("source_publication_utc")
        or row.get("source_publication_utc"),
    }
    cutoff = (
        str(row.get("target_cutoff_utc") or row.get("known_at_utc") or "")
        or "2018-09-01T19:00:00Z"
    )
    try:
        if not all(payload.get(field) for field in ("source_id", "effective_utc", "known_at_utc", "receipt_sha256", "classification", "evidence_class")):
            return "MISSING_CONTRIBUTING_AUTHORITY"
        return validate_row_authority(payload, target_cutoff=cutoff)
    except (PitKernelError, ValueError, TypeError):
        return "AUTHORITY_VALIDATION_FAILED"


def main() -> int:
    rows = load_jsonl(PRED / "PIT_KERNEL_ROWS.jsonl")
    claimed = [
        row
        for row in rows
        if str(row.get("row_verdict") or row.get("authority_class") or "")
        in {PROVEN, "PROVEN"}
    ]
    independent_proven = 0
    dispositions: list[dict[str, Any]] = []
    reasons = Counter()
    for row in claimed:
        limits = limiting_keys(row)
        verdict = independent_verdict(row)
        if verdict == PROVEN and not limits:
            independent_proven += 1
            state = PROVEN
        else:
            state = "RETROSPECTIVE_CANDIDATE_NOT_INDEPENDENTLY_PROVEN"
            reasons.update(limits or [verdict])
        dispositions.append(
            {
                "canonical_game_id": row.get("canonical_game_id"),
                "season": row.get("season"),
                "predecessor_verdict": row.get("row_verdict") or row.get("authority_class"),
                "independent_verdict": verdict if verdict != PROVEN or limits else PROVEN,
                "limiting_dependency_keys": limits,
                "predecessor_claim_not_cycle32_proof": True,
            }
        )
    payload = {
        "artifact_type": "CYCLE32_PIT_FEATURE_LINEAGE",
        "artifact_class": "REAL_EVIDENCE",
        "as_of_utc": utc_now(),
        "predecessor_kernel_rows": len(rows),
        "predecessor_claimed_proven": len(claimed),
        "independently_proven_cycle32": independent_proven,
        "did_not_manufacture_positive_pit_count": True,
        "trust_classification": "UNTRUSTED_SHADOW",
        "limiting_reason_counts": dict(reasons),
        "rows": dispositions[:50],
        "all_claimed_rows_traced": True,
        "traced_claimed_proven_count": len(claimed),
        "notes": [
            "Predecessor PROVEN labels are stored claims, not Cycle32 feature-vector proof.",
            "A receipt-shaped dictionary is not sufficient. Missing lineage stays retrospective.",
        ],
    }
    out = OUT / "science" / "CYCLE32_PIT_FEATURE_LINEAGE.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "predecessor_claimed_proven": len(claimed),
                "independently_proven_cycle32": independent_proven,
                "limiting_reason_counts": dict(reasons),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
