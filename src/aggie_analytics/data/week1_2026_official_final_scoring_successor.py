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
from typing import Any, Mapping, Sequence

from aggie_analytics.modeling.week_zero_official_final_scoring import (
    parse_scoreboard_cards,
)

SCHEMA_VERSION = "aggie.shadow.week1_2026_official_final_scoring_successor.v2"
CONTRACT_ID = "CYCLE26-WEEK1-2026-OFFICIAL-FINAL-SCORING-SUCCESSOR-V2"
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
SKILL_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_PREDICTIVE_SKILL_EVIDENCE.json"
)
WEEK1_GATE_RELATIVE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
)
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
MARGIN_CAPABLE = "national_margin_ridge"
CAPTURE_MODE_DIRECTORY_UNION = "DIRECTORY_UNION"
PREDECESSOR_SCORING_DATASET_IDENTITY = (
    "724a3434609397c329d718922574af78251bbed0ead57f21c8e9380b7f232fe4"
)
PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM = 30
SCOREBOARD_RELATIVE = "raw/SRC-NCAA-OFFICIAL-STATS/ncaa_week1_2026_schedule_scoreboard"


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


def scoreboard_directory(data_root: Path) -> Path:
    return data_root / SCOREBOARD_RELATIVE


def list_scoreboard_html_paths(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise Week1OfficialFinalScoringError(
            f"official scoreboard directory missing: {directory}"
        )
    paths = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == ".html"
    ]
    return sorted(paths, key=lambda path: (path.stat().st_mtime, path.name))


def terminal_snapshot(
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


def merge_terminal_cards(
    captures: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
) -> dict[str, Any]:
    """Union terminal cards across captures.

    Later captures may add newly terminal contests. Conflicting scores for the
    same contest are quarantined and never restored by a later agreeing file.
    """

    terminals: dict[str, dict[str, Any]] = {}
    contributing: list[str] = []
    conflicts: dict[str, list[dict[str, Any]]] = {}
    for capture_sha256, cards in captures:
        for card in cards:
            snapshot = terminal_snapshot(card, capture_sha256)
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


def collect_directory_union_terminals(data_root: Path) -> dict[str, Any]:
    directory = scoreboard_directory(data_root)
    captures: list[tuple[str, list[dict[str, Any]]]] = []
    card_count = 0
    for path in list_scoreboard_html_paths(directory):
        cards = parse_scoreboard_cards(
            path.read_text(encoding="utf-8", errors="replace")
        )
        card_count += len(cards)
        captures.append((path.stem, cards))
    merged = merge_terminal_cards(captures)
    merged["scoreboard_html_count"] = len(captures)
    merged["scoreboard_card_count"] = card_count
    return merged


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def unique_game_empirical_assessment(
    scored_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Unique-game prospective census. Does not establish predictive skill."""

    unique_games: set[str] = set()
    by_candidate: dict[str, dict[str, Any]] = {}
    for row in scored_rows:
        if row.get("scored") is not True:
            continue
        contest_id = str(row.get("ncaa_contest_id") or "").strip()
        candidate_id = str(row.get("candidate_id") or "").strip()
        if not contest_id or not candidate_id:
            continue
        unique_games.add(contest_id)
        bucket = by_candidate.setdefault(
            candidate_id,
            {
                "brier": [],
                "log_loss": [],
                "margin_abs": [],
                "accuracy": [],
                "games": set(),
            },
        )
        if contest_id in bucket["games"]:
            continue
        bucket["games"].add(contest_id)
        bucket["brier"].append(float(row["brier"]))
        bucket["log_loss"].append(float(row["binary_log_loss"]))
        label = row.get("label_home_win")
        probability = float(row["forecast_probability_home"])
        if label in (0, 1):
            predicted_home = probability >= 0.5
            bucket["accuracy"].append(float(predicted_home == bool(label)))
        if candidate_id == MARGIN_CAPABLE and row.get("margin_residual") is not None:
            bucket["margin_abs"].append(abs(float(row["margin_residual"])))
    unique_count = len(unique_games)
    skill_state = (
        "NOT_ESTABLISHED"
        if unique_count < PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM
        else "DEVELOPMENT_EVIDENCE_ONLY"
    )
    candidates = []
    for candidate_id in sorted(by_candidate):
        bucket = by_candidate[candidate_id]
        entry = {
            "candidate_id": candidate_id,
            "unique_games": len(bucket["games"]),
            "brier": _mean(bucket["brier"]),
            "log_loss": _mean(bucket["log_loss"]),
            "accuracy": _mean(bucket["accuracy"]),
            "control_only": candidate_id == "national_base_rate",
        }
        if candidate_id == MARGIN_CAPABLE:
            entry["margin_mae"] = _mean(bucket["margin_abs"])
        else:
            entry["margin_mae"] = None
        candidates.append(entry)
    return {
        "PREDICTIVE_SKILL_EVIDENCE_STATE": skill_state,
        "predeclared_min_unique_games_for_skill_claim": (
            PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM
        ),
        "unique_scored_games": unique_count,
        "denominator": "UNIQUE_GAME_NOT_ORIENTED_ROW",
        "used_for_training_or_tuning": False,
        "candidates": candidates,
        "reason": (
            "Week 1 unique-game n is below the predeclared skill floor; "
            "residuals are a prospective census only."
            if skill_state == "NOT_ESTABLISHED"
            else "Week 1 residuals remain a prospective census and do not "
            "replace the 2023 development partition."
        ),
    }


def bind_week1_partial_skill(
    *,
    repo_root: Path,
    empirical: Mapping[str, Any],
    scoring_gate_identity: str,
) -> None:
    path = repo_root / SKILL_RELATIVE
    payload = read_json(path)
    if payload.get("PREDICTIVE_SKILL_EVIDENCE_STATE") != "DEVELOPMENT_EVIDENCE_ONLY":
        raise Week1OfficialFinalScoringError(
            "2023 development skill state must remain DEVELOPMENT_EVIDENCE_ONLY"
        )
    nonclaims = dict(payload.get("nonclaims") or {})
    nonclaims["week1_outcome_tuned"] = False
    nonclaims["future_predictive_skill"] = False
    payload["nonclaims"] = nonclaims
    payload["week1_partial_official_finals"] = {
        **dict(empirical),
        "scoring_gate_identity": scoring_gate_identity,
        "does_not_replace_2023_development_evidence": True,
        "used_for_training_or_tuning": False,
    }
    path.write_bytes(
        json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )


def build_gate(
    *,
    repo_root: Path,
    data_root: Path,
    issued_at_utc: str,
) -> dict[str, Any]:
    week1 = read_json(repo_root / WEEK1_GATE_RELATIVE)
    freeze_utc = str(week1.get("issued_at_utc") or "")
    relative = week1["payloads"]["forecast_rows"]["relative_path"]
    rows = read_jsonl(data_root / relative)
    merged = collect_directory_union_terminals(data_root)
    terminals: dict[str, dict[str, Any]] = merged["terminals"]
    expected_contests = sorted(
        {
            str(row.get("ncaa_contest_id") or "")
            for row in rows
            if row.get("ncaa_contest_id")
        }
    )
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
                "source_capture_sha256": final.get("capture_sha256"),
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
    empirical = unique_game_empirical_assessment(scored_rows)
    contributing = list(merged["contributing_capture_sha256"])
    quarantined = sorted(merged["quarantined_conflicts"])
    terminal_ids = sorted(terminals)
    awaiting = sorted(
        contest
        for contest in expected_contests
        if contest not in terminals and contest not in merged["quarantined_conflicts"]
    )
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
        "capture_mode": CAPTURE_MODE_DIRECTORY_UNION,
        "capture_sha256": contributing[-1] if contributing else None,
        "capture_sha256_list": contributing,
        "bound_predecessors": {
            "week1_successor_gate_identity": week1.get("gate_identity"),
            "forecast_payload_sha256": week1["payloads"]["forecast_rows"]["sha256"],
            "early_week1_freeze_utc": freeze_utc,
            "predecessor_scoring_dataset_identity": (
                PREDECESSOR_SCORING_DATASET_IDENTITY
            ),
            "predecessor_scoring_payload_rewritten": False,
        },
        "summary": {
            "scoreboard_html_count": merged["scoreboard_html_count"],
            "scoreboard_cards": merged["scoreboard_card_count"],
            "terminal_contest_count": len(terminals),
            "terminal_contest_ids": terminal_ids,
            "quarantined_conflict_contest_ids": quarantined,
            "universe_contest_count": len(expected_contests),
            "awaiting_final_contest_count": len(awaiting),
            "joined_forecast_rows": len(scored_rows),
            "scored_row_count": scored_count,
            "unique_scored_games": empirical["unique_scored_games"],
        },
        "empirical_assessment": empirical,
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
            "Does not rewrite the predecessor partial scoring payload.",
            "Does not backfill missed T-24H or T-90M checkpoints.",
            "Does not claim predictive skill or production credibility.",
            "Partial finals are not a complete Week 1 scoring run.",
            "Directory union does not upgrade a single-file capture into a missed cutoff.",
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
) -> dict[str, Any]:
    gate = build_gate(
        repo_root=repo_root,
        data_root=data_root,
        issued_at_utc=issued_at_utc,
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
    bind_week1_partial_skill(
        repo_root=repo_root,
        empirical=gate["empirical_assessment"],
        scoring_gate_identity=str(gate["gate_identity"]),
    )
    return gate
