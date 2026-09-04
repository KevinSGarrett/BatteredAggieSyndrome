"""Append-only Week 1 official-final scoring for frozen EARLY_WEEK1 rows.

Predecessor forecast payloads are never rewritten. Residuals are emitted only
when a terminal official final and a freeze-before-kickoff prediction both exist.
Week 1 outcomes are not used to train, select, tune or promote.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.modeling.week_zero_official_final_scoring import (
    parse_scoreboard_cards,
)

SCHEMA_VERSION = "aggie.shadow.week1_2026_official_final_scoring_successor.v1"
CONTRACT_ID = "CYCLE26-WEEK1-2026-OFFICIAL-FINAL-SCORING-SUCCESSOR-V1"
JIRA_KEY = "BAT-694"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-NATIONAL-FORECAST-COHORT-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "WEEK1_OFFICIAL_FINAL_SCORING_APPEND_ONLY"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_OFFICIAL_FINAL_SCORING_PARTIAL"
GATE_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_WEEK1_OFFICIAL_FINAL_SCORING.json"
)
WEEK1_GATE_RELATIVE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
)
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
MARGIN_CAPABLE = "national_margin_ridge"
SEP3_CAPTURE_SHA256 = "02fbf4ab441ccae3f9172285ee9f3cb57e9e91a43ecc03967c3ebef50be03868"


class Week1OfficialFinalScoringError(ValueError):
    """Raised when official-final scoring would rewrite or backfill unsafely."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_utc(value: str | None) -> datetime | None:
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


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def decisive_home_win(home_points: int, away_points: int) -> int | None:
    if home_points == away_points:
        return None
    return int(home_points > away_points)


def score_row(
    *,
    probability_home: float | None,
    expected_margin_home: float | None,
    home_points: int,
    away_points: int,
    candidate_id: str,
) -> dict[str, Any]:
    label = decisive_home_win(home_points, away_points)
    actual_margin = float(home_points - away_points)
    if label is None:
        return {
            "label_home_win": None,
            "actual_margin_home": actual_margin,
            "brier": None,
            "binary_log_loss": None,
            "margin_residual": None,
            "scored": False,
            "unscored_reason": "TIE_OR_NO_CONTEST_NOT_SILENTLY_COUNTED",
        }
    if probability_home is None:
        return {
            "label_home_win": label,
            "actual_margin_home": actual_margin,
            "brier": None,
            "binary_log_loss": None,
            "margin_residual": None,
            "scored": False,
            "unscored_reason": "ABSTAINED_OR_MISSING_PROBABILITY",
        }
    probability = float(probability_home)
    if not (0.0 <= probability <= 1.0):
        raise Week1OfficialFinalScoringError("probability outside [0,1] before metrics")
    brier = (probability - float(label)) ** 2
    clipped = min(max(probability, 1e-15), 1.0 - 1e-15)
    if label == 1:
        log_loss = -math.log(clipped)
    else:
        log_loss = -math.log(1.0 - clipped)
    margin_residual = None
    if candidate_id == MARGIN_CAPABLE:
        if expected_margin_home is None:
            return {
                "label_home_win": label,
                "actual_margin_home": actual_margin,
                "brier": brier,
                "binary_log_loss": log_loss,
                "margin_residual": None,
                "scored": False,
                "unscored_reason": "MARGIN_NOT_SUPPORTED_OR_MISSING",
            }
        margin_residual = float(expected_margin_home) - actual_margin
    return {
        "label_home_win": label,
        "actual_margin_home": actual_margin,
        "brier": brier,
        "binary_log_loss": log_loss,
        "margin_residual": margin_residual,
        "scored": True,
        "unscored_reason": None,
    }


def freeze_before_kickoff(freeze_utc: str, kickoff_utc: str | None) -> bool:
    freeze = parse_utc(freeze_utc)
    kickoff = parse_utc(kickoff_utc)
    if freeze is None or kickoff is None:
        return False
    return freeze < kickoff


def build_gate(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
    capture_sha256: str = SEP3_CAPTURE_SHA256,
) -> dict[str, Any]:
    week1 = read_json(repo_root / WEEK1_GATE_RELATIVE)
    freeze_utc = str(week1.get("issued_at_utc") or "")
    relative = week1["payloads"]["forecast_rows"]["relative_path"]
    rows = read_jsonl(data_root / relative)
    html_path = (
        data_root
        / "raw"
        / "SRC-NCAA-OFFICIAL-STATS"
        / "ncaa_week1_2026_schedule_scoreboard"
        / f"{capture_sha256}.html"
    )
    if not html_path.is_file():
        raise Week1OfficialFinalScoringError(
            f"official scoreboard capture missing: {html_path}"
        )
    document = html_path.read_text(encoding="utf-8", errors="replace")
    cards = parse_scoreboard_cards(document)
    terminals = {
        str(card["ncaa_contest_id"]): card
        for card in cards
        if card.get("final_status_is_terminal") and card.get("ncaa_contest_id")
    }
    scored_rows: list[dict[str, Any]] = []
    for row in rows:
        contest_id = str(row.get("ncaa_contest_id") or "")
        final = terminals.get(contest_id)
        if final is None:
            continue
        if not freeze_before_kickoff(freeze_utc, row.get("kickoff_bound_utc")):
            scored_rows.append(
                {
                    "ncaa_contest_id": contest_id,
                    "candidate_id": row.get("candidate_id"),
                    "forecast_row_identity": row.get("forecast_row_identity"),
                    "checkpoint_id": row.get("checkpoint_id"),
                    "scored": False,
                    "unscored_reason": "FREEZE_NOT_BEFORE_KICKOFF",
                    "forecast_probability_home": row.get("probability_home"),
                    "forecast_expected_margin_home": row.get("expected_margin_home"),
                }
            )
            continue
        home_points = int(final["home_points"])
        away_points = int(final["away_points"])
        metrics = score_row(
            probability_home=row.get("probability_home"),
            expected_margin_home=row.get("expected_margin_home"),
            home_points=home_points,
            away_points=away_points,
            candidate_id=str(row.get("candidate_id") or ""),
        )
        scored_rows.append(
            {
                "ncaa_contest_id": contest_id,
                "candidate_id": row.get("candidate_id"),
                "forecast_row_identity": row.get("forecast_row_identity"),
                "checkpoint_id": row.get("checkpoint_id"),
                "control_only": bool(row.get("control_only")),
                "home_points": home_points,
                "away_points": away_points,
                "final_status_text": final.get("final_status_text"),
                "forecast_probability_home": row.get("probability_home"),
                "forecast_expected_margin_home": row.get("expected_margin_home"),
                "kickoff_bound_utc": row.get("kickoff_bound_utc"),
                **metrics,
            }
        )
    payload = (
        "\n".join(json.dumps(row, sort_keys=True) for row in scored_rows) + "\n"
    ).encode("utf-8")
    dataset_identity = sha256_bytes(payload)
    payload_rel = (
        "canonical/week1_2026_official_final_scoring_successor/"
        f"sha256/{dataset_identity}/week1_2026_official_final_scoring_rows.jsonl"
    )
    scored_count = sum(1 for row in scored_rows if row.get("scored"))
    gate = {
        "artifact_type": "CYCLE26_WEEK1_OFFICIAL_FINAL_SCORING",
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": PASS_RESULT,
        "publication_label": SHADOW_CLASSIFICATION,
        "week1_outcome_training_forbidden": True,
        "forecast_payloads_rewritten": False,
        "checkpoint_scored": "EARLY_WEEK1",
        "t24h_backfill": False,
        "t90m_backfill": False,
        "capture_sha256": capture_sha256,
        "bound_predecessors": {
            "week1_successor_gate_identity": week1.get("gate_identity"),
            "forecast_payload_sha256": week1["payloads"]["forecast_rows"]["sha256"],
            "early_week1_freeze_utc": freeze_utc,
        },
        "summary": {
            "scoreboard_cards": len(cards),
            "terminal_contest_count": len(terminals),
            "terminal_contest_ids": sorted(terminals),
            "joined_forecast_rows": len(scored_rows),
            "scored_row_count": scored_count,
            "remaining_nonterminal_sep3_cards": sum(
                1 for card in cards if not card.get("final_status_is_terminal")
            ),
        },
        "payloads": {
            "scoring_rows": {
                "relative_path": payload_rel,
                "sha256": dataset_identity,
                "bytes": len(payload),
                "row_count": len(scored_rows),
            }
        },
        "scientific_nonclaims": [
            "Does not train, select, tune or promote using Week 1 outcomes.",
            "Does not rewrite frozen EARLY_WEEK1 forecast payloads.",
            "Does not backfill missed T-24H or T-90M checkpoints.",
            "Does not claim predictive skill or production credibility.",
            "Partial finals are not a complete Week 1 scoring run.",
        ],
        "_payload_bytes": payload,
    }
    gate["dataset_identity"] = dataset_identity
    gate["gate_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in gate.items() if not str(key).startswith("_")}
        )
    )
    return gate


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
    capture_sha256: str = SEP3_CAPTURE_SHA256,
) -> dict[str, Any]:
    gate = build_gate(
        repo_root=repo_root,
        data_root=data_root,
        issued_at_utc=issued_at_utc,
        capture_sha256=capture_sha256,
    )
    payload = gate.pop("_payload_bytes")
    payload_path = data_root / gate["payloads"]["scoring_rows"]["relative_path"]
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_bytes(payload)
    gate_path = repo_root / GATE_RELATIVE
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_bytes(
        json.dumps(gate, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    return gate
