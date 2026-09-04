"""Independently reconstruct Week 1 official-final scoring rows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

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
MARGIN_CAPABLE = "national_margin_ridge"


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
    if gate.get("forecast_payloads_rewritten") is True:
        findings.append("FORECAST_PAYLOAD_REWRITE")
    if gate.get("t24h_backfill") is True or gate.get("t90m_backfill") is True:
        findings.append("CHECKPOINT_BACKFILL")
    if gate.get("week1_outcome_training_forbidden") is not True:
        findings.append("OUTCOME_TRAINING_NOT_FORBIDDEN")
    if (
        gate["bound_predecessors"]["forecast_payload_sha256"]
        != week1["payloads"]["forecast_rows"]["sha256"]
    ):
        findings.append("FORECAST_PAYLOAD_HASH_DRIFT")
    html_path = (
        data
        / "raw"
        / "SRC-NCAA-OFFICIAL-STATS"
        / "ncaa_week1_2026_schedule_scoreboard"
        / f"{gate['capture_sha256']}.html"
    )
    cards = parse_scoreboard_cards(
        html_path.read_text(encoding="utf-8", errors="replace")
    )
    terminals = {
        str(card["ncaa_contest_id"]): card
        for card in cards
        if card.get("final_status_is_terminal")
    }
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
    payload = {
        "validator": "week1_2026_official_final_scoring_successor",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "gate_identity": gate.get("gate_identity"),
        "terminal_contest_count": gate["summary"]["terminal_contest_count"],
        "scored_row_count": gate["summary"]["scored_row_count"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
