"""Independently reconstruct Week 1 official-final scoring rows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.modeling.week_zero_official_final_scoring import (  # noqa: E402
    parse_scoreboard_cards,
)

GATE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_WEEK1_OFFICIAL_FINAL_SCORING.json"
)
WEEK1_GATE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
)
SKILL = "artifacts/scientific_integrity/cycle26/CYCLE26_PREDICTIVE_SKILL_EVIDENCE.json"
MARGIN_CAPABLE = "national_margin_ridge"
SCOREBOARD_RELATIVE = "raw/SRC-NCAA-OFFICIAL-STATS/ncaa_week1_2026_schedule_scoreboard"
PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM = 30


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


def _terminal_snapshot(
    card: Mapping[str, Any], capture_sha256: str
) -> dict[str, Any] | None:
    if not card.get("final_status_is_terminal"):
        return None
    contest_id = str(card.get("ncaa_contest_id") or "").strip()
    if not contest_id:
        return None
    try:
        home_points = int(card["home_points"])
        away_points = int(card["away_points"])
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "ncaa_contest_id": contest_id,
        "home_points": home_points,
        "away_points": away_points,
        "final_status_text": card.get("final_status_text"),
        "capture_sha256": capture_sha256,
    }


def _merge_terminals(
    captures: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
) -> dict[str, Any]:
    terminals: dict[str, dict[str, Any]] = {}
    contributing: list[str] = []
    conflicts: dict[str, list[dict[str, Any]]] = {}
    for capture_sha256, cards in captures:
        for card in cards:
            snapshot = _terminal_snapshot(card, capture_sha256)
            if snapshot is None:
                continue
            contest_id = str(snapshot["ncaa_contest_id"])
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
            if capture_sha256 not in contributing:
                contributing.append(capture_sha256)
    return {
        "terminals": terminals,
        "contributing_capture_sha256": contributing,
        "quarantined_conflicts": conflicts,
    }


def _collect_directory_union(data_root: Path) -> dict[str, Any]:
    directory = data_root / SCOREBOARD_RELATIVE
    paths = sorted(
        [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".html"
        ],
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    captures: list[tuple[str, list[dict[str, Any]]]] = []
    for path in paths:
        cards = parse_scoreboard_cards(
            path.read_text(encoding="utf-8", errors="replace")
        )
        captures.append((path.stem, cards))
    return _merge_terminals(captures)


def _unique_games(scored_rows: Sequence[Mapping[str, Any]]) -> set[str]:
    games: set[str] = set()
    seen: dict[str, set[str]] = {}
    for row in scored_rows:
        if row.get("scored") is not True:
            continue
        contest_id = str(row.get("ncaa_contest_id") or "")
        candidate_id = str(row.get("candidate_id") or "")
        if not contest_id or not candidate_id:
            continue
        games.add(contest_id)
        bucket = seen.setdefault(candidate_id, set())
        bucket.add(contest_id)
    return games


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args()
    repo = Path(args.repo_root)
    data = Path(args.data_root)
    findings: list[str] = []
    gate = json.loads((repo / GATE).read_text(encoding="utf-8"))
    week1 = json.loads((repo / WEEK1_GATE).read_text(encoding="utf-8"))
    skill = json.loads((repo / SKILL).read_text(encoding="utf-8"))
    if gate.get("forecast_payloads_rewritten") is True:
        findings.append("FORECAST_PAYLOAD_REWRITE")
    if gate.get("t24h_backfill") is True or gate.get("t90m_backfill") is True:
        findings.append("CHECKPOINT_BACKFILL")
    if gate.get("week1_outcome_training_forbidden") is not True:
        findings.append("OUTCOME_TRAINING_NOT_FORBIDDEN")
    if gate.get("capture_mode") != "DIRECTORY_UNION":
        findings.append("CAPTURE_MODE_NOT_DIRECTORY_UNION")
    if (
        gate["bound_predecessors"]["forecast_payload_sha256"]
        != week1["payloads"]["forecast_rows"]["sha256"]
    ):
        findings.append("FORECAST_PAYLOAD_HASH_DRIFT")
    if gate["bound_predecessors"].get("predecessor_scoring_payload_rewritten") is True:
        findings.append("PREDECESSOR_SCORING_REWRITE")
    merged = _collect_directory_union(data)
    terminals = merged["terminals"]
    if sorted(terminals) != list(gate["summary"]["terminal_contest_ids"]):
        findings.append("TERMINAL_ID_MISMATCH")
    if len(terminals) != int(gate["summary"]["terminal_contest_count"]):
        findings.append("TERMINAL_COUNT_MISMATCH")
    scoring_path = data / gate["payloads"]["scoring_rows"]["relative_path"]
    scored_rows = [
        json.loads(line)
        for line in scoring_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    fail = 0
    freeze = _parse_utc(week1.get("issued_at_utc"))
    for row in scored_rows:
        if row.get("scored") is not True:
            continue
        final = terminals.get(str(row.get("ncaa_contest_id")))
        if final is None:
            fail += 1
            continue
        kickoff = _parse_utc(row.get("kickoff_bound_utc"))
        if freeze is None or kickoff is None or not (freeze < kickoff):
            fail += 1
            continue
        if int(row["home_points"]) != int(final["home_points"]):
            fail += 1
        if int(row["away_points"]) != int(final["away_points"]):
            fail += 1
        label = int(final["home_points"] > final["away_points"])
        if final["home_points"] == final["away_points"]:
            fail += 1
            continue
        probability = float(row["forecast_probability_home"])
        expected_brier = (probability - float(label)) ** 2
        if abs(expected_brier - float(row["brier"])) > 1e-12:
            fail += 1
        clipped = min(max(probability, 1e-15), 1.0 - 1e-15)
        expected_ll = -math.log(clipped if label == 1 else (1.0 - clipped))
        if abs(expected_ll - float(row["binary_log_loss"])) > 1e-12:
            fail += 1
        if row.get("candidate_id") == MARGIN_CAPABLE:
            actual_margin = float(final["home_points"] - final["away_points"])
            expected_residual = (
                float(row["forecast_expected_margin_home"]) - actual_margin
            )
            if abs(expected_residual - float(row["margin_residual"])) > 1e-12:
                fail += 1
    if fail:
        findings.append(f"INDEPENDENT_RECONSTRUCTION_FAIL:{fail}")
    unique_games = _unique_games(scored_rows)
    if int(gate["summary"]["unique_scored_games"]) != len(unique_games):
        findings.append("UNIQUE_GAME_COUNT_MISMATCH")
    empirical = gate.get("empirical_assessment") or {}
    if (
        empirical.get("PREDICTIVE_SKILL_EVIDENCE_STATE") != "NOT_ESTABLISHED"
        and int(empirical.get("unique_scored_games") or 0)
        < PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM
    ):
        findings.append("WEEK1_SKILL_CLAIM_BELOW_PREDECLARED_FLOOR")
    if empirical.get("used_for_training_or_tuning") is True:
        findings.append("WEEK1_OUTCOME_USED_FOR_TUNING")
    if skill.get("PREDICTIVE_SKILL_EVIDENCE_STATE") != "DEVELOPMENT_EVIDENCE_ONLY":
        findings.append("DEVELOPMENT_SKILL_STATE_DRIFT")
    week1_partial = skill.get("week1_partial_official_finals") or {}
    if week1_partial.get("PREDICTIVE_SKILL_EVIDENCE_STATE") not in {
        "NOT_ESTABLISHED",
        None,
        "",
    } and int(week1_partial.get("unique_scored_games") or 0) < (
        PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM
    ):
        findings.append("SKILL_ARTIFACT_WEEK1_OVERCLAIM")
    if (skill.get("nonclaims") or {}).get("week1_outcome_tuned") is True:
        findings.append("SKILL_ARTIFACT_WEEK1_TUNED")
    payload = {
        "validator": "week1_2026_official_final_scoring_successor",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "gate_identity": gate.get("gate_identity"),
        "terminal_contest_count": gate["summary"]["terminal_contest_count"],
        "scored_row_count": gate["summary"]["scored_row_count"],
        "unique_scored_games": gate["summary"]["unique_scored_games"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
