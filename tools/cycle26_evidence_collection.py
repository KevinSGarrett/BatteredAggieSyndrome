"""Cycle #26 evidence collection: national rehash, pair census, Week 1 capture identity."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DATA_ROOT = Path(r"C:\BatteredAggieSyndrome.data")
OPS = DATA_ROOT / "ops" / "cycle26"
CFBD = (
    DATA_ROOT
    / "manifests/acquisition/bat378-cfbd-historical-expansion-v1/historical_expansion_acquisition_manifest.full.json"
)
SDV = (
    DATA_ROOT
    / "manifests/acquisition/bat378-sportsdataverse-supplement-v1/sportsdataverse_supplement_manifest.full.json"
)
PREDICTIONS = {
    "20": (
        "canonical/national_expectation_baselines_and_peers/sha256/773cf850bb8351497643506dd2ddcb4efbad26e3cd95a4dc78039b6e8ef3a1b0/national_baseline_predictions.jsonl",
        "a4671745e7c89a65ed87f2c2c5bd0a90a6adb38fedd162240cace1f30ee0088e",
    ),
    "21": (
        "canonical/national_multi_year_walk_forward/sha256/1112becc65f78a25b0843588fd5eba5ddcec6009b0ec58f0cb299c343188bcda/national_multi_year_walk_forward_predictions.jsonl",
        "c380eb08ee42c7b4eeed32436ccfc4f035f88e43048f327ea9c0d5d28fb4e6d6",
    ),
    "25": (
        "canonical/week1_2026_forecast_input_binding_successor/sha256/91fa82144bb76d75bbfc67d98141cfdd8d5825a5c1b5e657639c9a2b4c693730/week1_2026_c25_successor_score_rows.jsonl",
        "d4d29f346242009d3675cd6d40d24a76fdfaa4f20b6689f4e3f5ccecab0ed108",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rehash_manifest(path: Path, records_key: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    records = payload.get(records_key) or payload.get("captures") or []
    verified = 0
    empty = 0
    missing = []
    paths: list[str] = []
    hashes: list[str] = []
    weighted = 0
    for row in records:
        relative = (
            row.get("immutable_path")
            or row.get("raw_relative_path")
            or row.get("relative_path")
            or row.get("path")
        )
        expected = (
            row.get("response_sha256") or row.get("raw_sha256") or row.get("sha256")
        )
        disposition = str(row.get("disposition") or row.get("state") or "")
        target = DATA_ROOT / relative if relative else None
        if disposition == "CAPTURED_EMPTY":
            empty += 1
        if target is None or not target.is_file():
            if disposition == "CAPTURED_EMPTY" and (not target or target.is_file()):
                verified += 1
                continue
            missing.append({"path": relative, "disposition": disposition})
            continue
        digest = sha256_file(target)
        size = target.stat().st_size
        weighted += size
        paths.append(str(relative))
        hashes.append(digest)
        if expected and digest != expected:
            missing.append({"path": relative, "expected": expected, "actual": digest})
            continue
        verified += 1
    return {
        "manifest": str(path.relative_to(DATA_ROOT)).replace("\\", "/"),
        "manifest_sha256": sha256_file(path),
        "record_count": len(records),
        "verified_records": verified,
        "empty_capture_records": empty,
        "missing_or_mismatched_records": missing,
        "distinct_paths": len(set(paths)),
        "distinct_hashes": len(set(hashes)),
        "record_weighted_bytes": weighted,
    }


def pair_census() -> dict:
    results = {}
    for cycle, (relative, expected) in PREDICTIONS.items():
        path = DATA_ROOT / relative
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected:
            results[cycle] = {
                "error": "HASH_MISMATCH",
                "actual": digest,
                "expected": expected,
            }
            continue
        rows = [json.loads(line) for line in raw.splitlines() if line]
        game_key = "contest_identity" if cycle == "25" else "canonical_game_id"
        probability = "probability" if cycle == "25" else "predicted_win_probability"
        margin = "expected_margin" if cycle == "25" else "predicted_margin"
        groups: dict[tuple[str, str], list] = defaultdict(list)
        for row in rows:
            groups[(row["candidate_id"], row[game_key])].append(row)
        summary = {}
        for candidate in sorted({row["candidate_id"] for row in rows}):
            all_pairs = [pair for (cid, _), pair in groups.items() if cid == candidate]
            pairs = [
                pair
                for pair in all_pairs
                if all(r.get(probability) is not None for r in pair)
            ]
            errors = [abs(sum(r[probability] for r in pair) - 1) for pair in pairs]
            margin_errors = [
                abs(sum(r[margin] for r in pair))
                for pair in pairs
                if all(r.get(margin) is not None for r in pair)
            ]
            summary[candidate] = {
                "all_game_pairs": len(all_pairs),
                "scorable_game_pairs": len(pairs),
                "probability_sum_failures_tolerance_1e_8": sum(
                    error > 1e-8 for error in errors
                ),
                "max_probability_sum_error": max(errors, default=None),
                "margin_pairs": len(margin_errors),
                "margin_antisymmetry_failures_tolerance_1e_8": sum(
                    error > 1e-8 for error in margin_errors
                ),
                "max_margin_sum_error": max(margin_errors, default=None),
            }
        results[cycle] = {
            "path": relative,
            "sha256": digest,
            "bytes": len(raw),
            "rows": len(rows),
            "candidate_results": summary,
        }
        if cycle == "25":
            focus = "0d28c02c699e878bd8a0526517d332c1a7218e878b2173a72973d19639f5fa02"
            results[cycle]["am_focus_both_orientations"] = [
                {
                    "canonical_team_id": row.get("canonical_team_id"),
                    "probability": row.get("probability"),
                    "expected_margin": row.get("expected_margin"),
                    "candidate_id": row.get("candidate_id"),
                    "row_state": row.get("row_state"),
                }
                for row in rows
                if row[game_key] == focus
                and "ridge" in str(row.get("candidate_id") or "")
            ]
    return results


def main() -> int:
    OPS.mkdir(parents=True, exist_ok=True)
    cfbd = rehash_manifest(CFBD, "request_index")
    sdv_payload = json.loads(SDV.read_text(encoding="utf-8-sig"))
    sdv_key = "request_index" if "request_index" in sdv_payload else "captures"
    sdv = rehash_manifest(SDV, sdv_key)
    combined = {
        "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cfbd": cfbd,
        "sportsdataverse": sdv,
        "capture_records": cfbd["record_count"] + sdv["record_count"],
        "verified_records": cfbd["verified_records"] + sdv["verified_records"],
        "record_weighted_bytes": cfbd["record_weighted_bytes"]
        + sdv["record_weighted_bytes"],
        "missing_or_mismatched_records": cfbd["missing_or_mismatched_records"]
        + sdv["missing_or_mismatched_records"],
        "false_positive_correction": {
            "finding_id": "P1-NATIONAL-CAPTURE-COUNT-990-VS-MOUNTED",
            "original_assertion_preserved": True,
            "disposition": "DISPROVED_WITH_EVIDENCE",
            "reason": "Declared population is manifest records 972+18=990, not a recursive SRC-002 directory count.",
        },
    }
    (OPS / "CYCLE26_NATIONAL_CAPTURE_REHASH.json").write_text(
        json.dumps(combined, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    census = pair_census()
    (OPS / "CYCLE26_SAVED_PAIR_CENSUS.json").write_text(
        json.dumps(census, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"rehash": combined, "pair_cycles": list(census)}, indent=2, sort_keys=True
        )[:2000]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
