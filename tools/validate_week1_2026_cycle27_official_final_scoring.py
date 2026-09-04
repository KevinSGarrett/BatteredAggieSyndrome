"""Independently reconstruct Cycle 27 Week 1 official-final scoring.

Metric reconstruction uses ``aggie_analytics.scientific_reference`` only. This
validator does not import producer scoring helpers or producer_metric_math.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.scientific_reference.coherence import residual_metrics  # noqa: E402
from aggie_analytics.scientific_reference.metrics import (  # noqa: E402
    accuracy,
    brier_score,
    log_loss,
)
from aggie_analytics.scientific_reference.ncaa_scoreboard_cards import (  # noqa: E402
    reconstruct_scoreboard_cards,
)

GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING.json"
)
MANIFEST_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/"
    "CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING_INPUT_MANIFEST.json"
)
ROWS_RELATIVE = (
    "artifacts/scientific_integrity/cycle27/"
    "CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING_ROWS.jsonl"
)
WEEK1_GATE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
)
PRODUCER_RELATIVE = (
    "src/aggie_analytics/data/week1_2026_cycle27_official_final_scoring.py"
)
PARSER_VERSION = "aggie.week_zero_official_final_scoring.parse_scoreboard_cards.v1"
NO_DIRECTION = "NO_DIRECTION"
MARGIN_CAPABLE = "national_margin_ridge"
STATE_SCORED = "SCORED"
STATE_AWAITING = "AWAITING_OFFICIAL_FINAL"
STATE_ABSTAINED = "ABSTAINED"
STATE_CONFLICT = "CONFLICT_QUARANTINED"
STATE_MISSED_CUTOFF = "MISSED_CUTOFF_NO_BACKFILL"
STATE_AUTHORIZED_EXCLUSION = "AUTHORIZED_EXCLUSION"
PREDECESSOR_GATE = "b5f20df45d939d71e0b72b31ee558d87e0b696608816b1e56806c1ac09d4c27c"
PREDECESSOR_DATASET = "1b1adb9e3c7da9269ec176d4c7aa3029db00a2d35352623a6dd44f37c95b293b"
FORBIDDEN_PRODUCER_IMPORTS = {
    "aggie_analytics.data.producer_metric_math",
    "aggie_analytics.data.week1_2026_official_final_scoring_successor",
    "aggie_analytics.data.week1_2026_cycle27_official_final_scoring",
    "aggie_analytics.modeling.week_zero_official_final_scoring",
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _favorite_direction(probability: float) -> str:
    if probability > 0.5:
        return "HOME"
    if probability < 0.5:
        return "AWAY"
    return NO_DIRECTION


def _freeze_before_kickoff(freeze_utc: str, kickoff_utc: str | None) -> bool:
    freeze = _parse_utc(freeze_utc)
    kickoff = _parse_utc(kickoff_utc)
    if freeze is None or kickoff is None:
        return False
    return freeze < kickoff


def _receipt_after_kickoff(
    retrieved_at_utc: str | None, kickoff_utc: str | None
) -> bool:
    retrieved = _parse_utc(retrieved_at_utc)
    kickoff = _parse_utc(kickoff_utc)
    if retrieved is None or kickoff is None:
        return False
    return retrieved > kickoff


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _merge_terminals(captures: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    terminals: dict[str, dict[str, Any]] = {}
    conflicts: dict[str, list[dict[str, Any]]] = {}
    for capture in captures:
        cards = reconstruct_scoreboard_cards(str(capture["document"]))
        for card in cards:
            if not card.get("final_status_is_terminal"):
                continue
            contest_id = str(card.get("ncaa_contest_id") or "").strip()
            if not contest_id:
                continue
            try:
                snapshot = {
                    "ncaa_contest_id": contest_id,
                    "home_points": int(card["home_points"]),
                    "away_points": int(card["away_points"]),
                    "capture_sha256": capture["sha256"],
                    "retrieved_at_utc": capture.get("retrieved_at_utc"),
                }
            except (KeyError, TypeError, ValueError):
                continue
            if contest_id in conflicts:
                continue
            previous = terminals.get(contest_id)
            if previous is not None and (
                previous["home_points"] != snapshot["home_points"]
                or previous["away_points"] != snapshot["away_points"]
            ):
                conflicts[contest_id] = [previous, snapshot]
                terminals.pop(contest_id, None)
                continue
            terminals[contest_id] = snapshot
    return {"terminals": terminals, "quarantined_conflicts": conflicts}


def reconstruct_states(
    *,
    forecast_rows: Sequence[Mapping[str, Any]],
    terminals: Mapping[str, Mapping[str, Any]],
    conflicts: Mapping[str, Any],
    freeze_utc: str,
    authorized_exclusions: set[str],
) -> list[dict[str, Any]]:
    reconstructed: list[dict[str, Any]] = []
    for row in forecast_rows:
        contest_id = str(row.get("ncaa_contest_id") or "")
        candidate_id = str(row.get("candidate_id") or "")
        checkpoint_id = str(row.get("checkpoint_id") or "")
        identity = (
            contest_id,
            candidate_id,
            checkpoint_id,
            str(row.get("forecast_row_identity") or ""),
        )
        if contest_id in authorized_exclusions:
            reconstructed.append(
                {"identity": identity, "state": STATE_AUTHORIZED_EXCLUSION}
            )
            continue
        if contest_id in conflicts:
            reconstructed.append({"identity": identity, "state": STATE_CONFLICT})
            continue
        if not _freeze_before_kickoff(freeze_utc, row.get("kickoff_bound_utc")):
            reconstructed.append({"identity": identity, "state": STATE_MISSED_CUTOFF})
            continue
        final = terminals.get(contest_id)
        if final is None:
            reconstructed.append({"identity": identity, "state": STATE_AWAITING})
            continue
        if int(final["home_points"]) == int(final["away_points"]):
            reconstructed.append(
                {"identity": identity, "state": STATE_AUTHORIZED_EXCLUSION}
            )
            continue
        if row.get("probability_home") is None:
            reconstructed.append({"identity": identity, "state": STATE_ABSTAINED})
            continue
        reconstructed.append(
            {
                "identity": identity,
                "state": STATE_SCORED,
                "probability_home": float(row["probability_home"]),
                "expected_margin_home": row.get("expected_margin_home"),
                "candidate_id": candidate_id,
                "ncaa_contest_id": contest_id,
                "home_points": int(final["home_points"]),
                "away_points": int(final["away_points"]),
                "label_home_win": int(final["home_points"] > final["away_points"]),
            }
        )
    return reconstructed


def reconstruct_metrics(scored: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_candidate: dict[str, dict[str, Any]] = {}
    unique_games: set[str] = set()
    for row in scored:
        contest_id = str(row["ncaa_contest_id"])
        candidate_id = str(row["candidate_id"])
        unique_games.add(contest_id)
        bucket = by_candidate.setdefault(
            candidate_id,
            {
                "predicted": [],
                "observed": [],
                "directional_predicted": [],
                "directional_observed": [],
                "expected_margin": [],
                "actual_margin": [],
                "games": set(),
            },
        )
        if contest_id in bucket["games"]:
            continue
        bucket["games"].add(contest_id)
        probability = float(row["probability_home"])
        label = float(row["label_home_win"])
        bucket["predicted"].append(probability)
        bucket["observed"].append(label)
        if _favorite_direction(probability) != NO_DIRECTION:
            bucket["directional_predicted"].append(probability)
            bucket["directional_observed"].append(label)
        if (
            candidate_id == MARGIN_CAPABLE
            and row.get("expected_margin_home") is not None
        ):
            bucket["expected_margin"].append(float(row["expected_margin_home"]))
            bucket["actual_margin"].append(
                float(row["home_points"] - row["away_points"])
            )
    candidates = []
    for candidate_id in sorted(by_candidate):
        bucket = by_candidate[candidate_id]
        directional_den = len(bucket["directional_predicted"])
        residuals = residual_metrics(bucket["expected_margin"], bucket["actual_margin"])
        candidates.append(
            {
                "candidate_id": candidate_id,
                "unique_games": len(bucket["games"]),
                "brier": brier_score(bucket["predicted"], bucket["observed"]),
                "log_loss": log_loss(bucket["predicted"], bucket["observed"]),
                "directional_denominator": directional_den,
                "directional_accuracy": (
                    accuracy(
                        bucket["directional_predicted"],
                        bucket["directional_observed"],
                    )
                    if directional_den
                    else None
                ),
                "residual_mae": residuals.get("mae"),
            }
        )
    return {"unique_scored_games": len(unique_games), "candidates": candidates}


def validate(
    *,
    repo_root: Path,
    data_root: Path,
    gate: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    scored_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    findings: list[str] = []
    validator_imports = _module_imports(Path(__file__).resolve())
    overlap = sorted(validator_imports & FORBIDDEN_PRODUCER_IMPORTS)
    if overlap:
        findings.append(f"VALIDATOR_IMPORTS_PRODUCER:{','.join(overlap)}")
    producer_path = repo_root / PRODUCER_RELATIVE
    if producer_path.is_file():
        producer_imports = _module_imports(producer_path)
        if any(
            item == "aggie_analytics.scientific_reference"
            or item.startswith("aggie_analytics.scientific_reference.")
            for item in producer_imports
        ):
            findings.append("PRODUCER_IMPORTS_INDEPENDENT_REFERENCE")
        if "aggie_analytics.data.producer_metric_math" in producer_imports:
            findings.append("PRODUCER_IMPORTS_PRODUCER_METRIC_MATH")
    reference_path = (
        repo_root / "src/aggie_analytics/scientific_reference/ncaa_scoreboard_cards.py"
    )
    if reference_path.is_file():
        reference_imports = _module_imports(reference_path)
        overlap_reference = sorted(reference_imports & FORBIDDEN_PRODUCER_IMPORTS)
        if overlap_reference:
            findings.append(
                f"INDEPENDENT_PARSER_IMPORTS_PRODUCER:{','.join(overlap_reference)}"
            )
    loaded_gate = gate or json.loads(
        (repo_root / GATE_RELATIVE).read_text(encoding="utf-8")
    )
    loaded_manifest = manifest or json.loads(
        (repo_root / MANIFEST_RELATIVE).read_text(encoding="utf-8")
    )
    if scored_rows is None:
        scored_rows = _load_jsonl(repo_root / ROWS_RELATIVE)
    if loaded_gate.get("capture_mode") != "PINNED_MANIFEST":
        findings.append("CAPTURE_MODE_NOT_PINNED_MANIFEST")
    if loaded_manifest.get("capture_mode") != "PINNED_MANIFEST":
        findings.append("MANIFEST_CAPTURE_MODE_NOT_PINNED")
    if loaded_gate.get("parser_version") != PARSER_VERSION:
        findings.append("PARSER_VERSION_MISMATCH")
    if loaded_gate.get("forecast_payloads_rewritten") is True:
        findings.append("FORECAST_PAYLOAD_REWRITE")
    if loaded_gate.get("predecessor_scoring_payload_rewritten") is True:
        findings.append("PREDECESSOR_SCORING_REWRITE")
    bound = loaded_gate.get("bound_predecessors") or {}
    if bound.get("predecessor_scoring_gate_identity") != PREDECESSOR_GATE:
        findings.append("PREDECESSOR_GATE_LINEAGE_DRIFT")
    if bound.get("predecessor_scoring_dataset_identity") != PREDECESSOR_DATASET:
        findings.append("PREDECESSOR_DATASET_LINEAGE_DRIFT")
    if int(bound.get("predecessor_joined_forecast_rows") or 0) != 50:
        findings.append("PREDECESSOR_JOINED_COUNT_LINEAGE_DRIFT")
    if int(bound.get("predecessor_scored_row_count") or 0) != 41:
        findings.append("PREDECESSOR_SCORED_COUNT_LINEAGE_DRIFT")
    week1_path = repo_root / WEEK1_GATE
    if week1_path.is_file() and bound.get("week1_successor_gate_identity"):
        week1 = json.loads(week1_path.read_text(encoding="utf-8"))
        if (
            bound.get("forecast_payload_sha256")
            != week1["payloads"]["forecast_rows"]["sha256"]
        ):
            findings.append("FORECAST_PAYLOAD_HASH_DRIFT")
    forecast_rel = loaded_manifest["forecast_payload"]["relative_path"]
    forecast_path = data_root / forecast_rel
    forecast_bytes = forecast_path.read_bytes()
    if _sha256_bytes(forecast_bytes) != loaded_manifest["forecast_payload"]["sha256"]:
        findings.append("MUTATED_FROZEN_FORECAST_PAYLOAD")
    forecast_rows = _load_jsonl(forecast_path)
    captures: list[dict[str, Any]] = []
    for capture in loaded_manifest.get("captures") or []:
        path = data_root / capture["relative_path"]
        payload = path.read_bytes()
        if _sha256_bytes(payload) != capture["sha256"]:
            findings.append(f"PINNED_CAPTURE_HASH_DRIFT:{capture['relative_path']}")
            continue
        if len(payload) != int(capture["bytes"]):
            findings.append(f"PINNED_CAPTURE_SIZE_DRIFT:{capture['relative_path']}")
            continue
        retrieved_at = None
        receipt_rel = capture.get("acquisition_receipt_relative_path")
        receipt_digest = str(capture.get("acquisition_receipt_sha256") or "").lower()
        if receipt_rel:
            receipt_path = data_root / str(receipt_rel)
            if not receipt_path.is_file():
                findings.append(f"ACQUISITION_RECEIPT_MISSING:{receipt_rel}")
                continue
            receipt_bytes = receipt_path.read_bytes()
            if _sha256_bytes(receipt_bytes) != receipt_digest:
                findings.append(f"ACQUISITION_RECEIPT_HASH_DRIFT:{receipt_rel}")
                continue
            receipt_payload = json.loads(receipt_bytes.decode("utf-8"))
            retrieved_at = receipt_payload.get("retrieved_at_utc")
            html_digest = str(receipt_payload.get("html_sha256") or "").lower()
            if html_digest and html_digest != capture["sha256"]:
                findings.append(f"ACQUISITION_RECEIPT_HTML_HASH_MISMATCH:{receipt_rel}")
                continue
        captures.append(
            {
                **capture,
                "document": payload.decode("utf-8", errors="replace"),
                "retrieved_at_utc": retrieved_at,
            }
        )
    merged = _merge_terminals(captures)
    kickoff_by_contest = {
        str(row.get("ncaa_contest_id") or ""): row.get("kickoff_bound_utc")
        for row in forecast_rows
        if row.get("ncaa_contest_id")
    }
    terminals = dict(merged["terminals"])
    for contest_id, snapshot in list(terminals.items()):
        retrieved = snapshot.get("retrieved_at_utc")
        if retrieved in (None, ""):
            terminals.pop(contest_id, None)
            continue
        if not _receipt_after_kickoff(
            str(retrieved), kickoff_by_contest.get(contest_id)
        ):
            terminals.pop(contest_id, None)
    reconstructed = reconstruct_states(
        forecast_rows=forecast_rows,
        terminals=terminals,
        conflicts=merged["quarantined_conflicts"],
        freeze_utc=str(loaded_manifest.get("freeze_utc") or ""),
        authorized_exclusions=set(
            loaded_manifest.get("authorized_exclusion_contest_ids") or []
        ),
    )
    produced_by_identity = {
        (
            str(row.get("ncaa_contest_id") or ""),
            str(row.get("candidate_id") or ""),
            str(row.get("checkpoint_id") or ""),
            str(row.get("forecast_row_identity") or ""),
        ): row
        for row in scored_rows
    }
    reconstructed_by_identity = {row["identity"]: row for row in reconstructed}
    extra = sorted(set(produced_by_identity) - set(reconstructed_by_identity))
    missing = sorted(set(reconstructed_by_identity) - set(produced_by_identity))
    if extra:
        findings.append(f"EXTRA_SCORED_ROWS:{len(extra)}")
    if missing:
        findings.append(f"MISSING_SCORED_ROWS:{len(missing)}")
    metric_fail = 0
    scored_for_metrics: list[dict[str, Any]] = []
    for identity, expected in reconstructed_by_identity.items():
        produced = produced_by_identity.get(identity)
        if produced is None:
            continue
        if produced.get("state") != expected["state"]:
            metric_fail += 1
            continue
        if expected["state"] != STATE_SCORED:
            continue
        probability = float(expected["probability_home"])
        label = float(expected["label_home_win"])
        reconstructed_brier = brier_score([probability], [label])
        reconstructed_ll = log_loss([probability], [label])
        if abs(float(produced["brier"]) - float(reconstructed_brier or 0.0)) > 1e-12:
            metric_fail += 1
        if (
            abs(float(produced["binary_log_loss"]) - float(reconstructed_ll or 0.0))
            > 1e-12
        ):
            metric_fail += 1
        if produced.get("favorite_direction") != _favorite_direction(probability):
            metric_fail += 1
        if (
            expected["candidate_id"] == MARGIN_CAPABLE
            and expected.get("expected_margin_home") is not None
        ):
            actual_margin = float(expected["home_points"] - expected["away_points"])
            predicted = float(expected["expected_margin_home"])
            residual = residual_metrics([predicted], [actual_margin])
            produced_residual = produced.get("residual_margin")
            produced_error = produced.get("prediction_error_margin")
            if (
                produced_residual is None
                or abs(float(produced_residual) - (actual_margin - predicted)) > 1e-12
            ):
                metric_fail += 1
            if (
                produced_error is None
                or abs(float(produced_error) - (predicted - actual_margin)) > 1e-12
            ):
                metric_fail += 1
            if residual.get("mae") is None:
                metric_fail += 1
        scored_for_metrics.append(expected)
    if metric_fail:
        findings.append(f"INDEPENDENT_RECONSTRUCTION_FAIL:{metric_fail}")
    empirical = reconstruct_metrics(scored_for_metrics)
    gate_empirical = loaded_gate.get("empirical_assessment") or {}
    produced_unique = gate_empirical.get("unique_scored_games")
    if (
        produced_unique is None
        or int(produced_unique) != empirical["unique_scored_games"]
    ):
        findings.append("UNIQUE_GAME_COUNT_MISMATCH")
    produced_by_candidate = {
        item["candidate_id"]: item for item in gate_empirical.get("candidates") or []
    }
    for item in empirical["candidates"]:
        produced = produced_by_candidate.get(item["candidate_id"]) or {}
        if produced.get("directional_denominator") != item["directional_denominator"]:
            findings.append(f"DIRECTIONAL_DENOMINATOR_MISMATCH:{item['candidate_id']}")
        if item["directional_denominator"] == 0:
            if produced.get("directional_accuracy") is not None:
                findings.append(
                    f"DIRECTIONAL_ACCURACY_NOT_NULL_WHEN_DEN_ZERO:{item['candidate_id']}"
                )
        elif produced.get("directional_accuracy") is not None:
            if (
                abs(
                    float(produced["directional_accuracy"])
                    - float(item["directional_accuracy"] or 0.0)
                )
                > 1e-12
            ):
                findings.append(f"DIRECTIONAL_ACCURACY_MISMATCH:{item['candidate_id']}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    findings = validate(
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
    )
    payload = {
        "validator": "week1_2026_cycle27_official_final_scoring",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
