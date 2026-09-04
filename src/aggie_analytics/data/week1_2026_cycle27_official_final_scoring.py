"""Cycle 27 Week 1 official-final scoring with a pinned input manifest.

Predecessor Cycle 26 gate b5f20df45d939d71e0b72b31ee558d87e0b696608816b1e56806c1ac09d4c27c
and dataset 1b1adb9e3c7da9269ec176d4c7aa3029db00a2d35352623a6dd44f37c95b293b are lineage
only. This successor never rewrites those payloads and never enumerates a live
scoreboard directory during scoring or replay. Official-final captures are read
only from an explicit pin (receipt, hash, size, parser version, as-of instant).

Producer metric formulas live here. Independent reconstruction must use
``aggie_analytics.scientific_reference`` and must not import this module's
scoring helpers.
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

SCHEMA_VERSION = "aggie.shadow.week1_2026_cycle27_official_final_scoring.v1"
CONTRACT_ID = "CYCLE27-WEEK1-2026-OFFICIAL-FINAL-SCORING-SUCCESSOR-V1"
JIRA_KEY = "BAT-694"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-NATIONAL-FORECAST-COHORT-001"
PARENT_JIRA_KEY = "BAT-523"
CLASSIFICATION = "WEEK1_OFFICIAL_FINAL_SCORING_PINNED_MANIFEST"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"
PRIMARY_INCOMPLETE = "PRIMARY_TRUST_RECOVERY_INCOMPLETE"
PASS_RESULT = "PASS_WEEK1_OFFICIAL_FINAL_SCORING_PINNED_PARTIAL"
CAPTURE_MODE_PINNED = "PINNED_MANIFEST"
PARSER_VERSION = "aggie.week_zero_official_final_scoring.parse_scoreboard_cards.v1"
PARSER_MODULE_RELATIVE = (
    "src/aggie_analytics/modeling/week_zero_official_final_scoring.py"
)
MARGIN_CAPABLE = "national_margin_ridge"
NO_DIRECTION = "NO_DIRECTION"
PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM = 30

STATE_SCORED = "SCORED"
STATE_AWAITING = "AWAITING_OFFICIAL_FINAL"
STATE_ABSTAINED = "ABSTAINED"
STATE_CONFLICT = "CONFLICT_QUARANTINED"
STATE_MISSED_CUTOFF = "MISSED_CUTOFF_NO_BACKFILL"
STATE_AUTHORIZED_EXCLUSION = "AUTHORIZED_EXCLUSION"

PREDECESSOR_SCORING_GATE_IDENTITY = (
    "b5f20df45d939d71e0b72b31ee558d87e0b696608816b1e56806c1ac09d4c27c"
)
PREDECESSOR_SCORING_DATASET_IDENTITY = (
    "1b1adb9e3c7da9269ec176d4c7aa3029db00a2d35352623a6dd44f37c95b293b"
)
PREDECESSOR_JOINED_FORECAST_ROWS = 50
PREDECESSOR_SCORED_ROW_COUNT = 41

WEEK1_GATE_RELATIVE = (
    "artifacts/forecast/week1_2026_game_grain_national_forecast_successor_gate.json"
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
TEMPORAL_AUTHORITY_RELATIVE = (
    "artifacts/scientific_integrity/cycle26/CYCLE26_FITTED_PATH_TEMPORAL_AUTHORITY.json"
)

CODE_BUNDLE_RELATIVE = (
    "src/aggie_analytics/data/week1_2026_cycle27_official_final_scoring.py",
    "tools/build_week1_2026_cycle27_official_final_scoring.py",
    "tools/validate_week1_2026_cycle27_official_final_scoring.py",
    PARSER_MODULE_RELATIVE,
)

SCHEMA_CONTRACT = {
    "schema_version": SCHEMA_VERSION,
    "contract_id": CONTRACT_ID,
    "capture_mode": CAPTURE_MODE_PINNED,
    "states": [
        STATE_SCORED,
        STATE_AWAITING,
        STATE_ABSTAINED,
        STATE_CONFLICT,
        STATE_MISSED_CUTOFF,
        STATE_AUTHORIZED_EXCLUSION,
    ],
    "prediction_error": "predicted_minus_actual",
    "residual": "actual_minus_predicted",
    "no_direction": NO_DIRECTION,
    "directional_p_equals_one_half": (
        "NO_DIRECTION_EXCLUDED_FROM_NUMERATOR_AND_DENOMINATOR"
    ),
}


class Week1Cycle27OfficialFinalScoringError(ValueError):
    """Raised when Cycle 27 official-final scoring cannot bind pinned inputs."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def posix_relative(path: str) -> str:
    return str(path).replace("\\", "/")


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


def jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    if not rows:
        return b""
    return (
        "\n".join(
            json.dumps(
                dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
            for row in rows
        )
        + "\n"
    ).encode("utf-8")


def schema_identity() -> str:
    return sha256_bytes(canonical_json_bytes(SCHEMA_CONTRACT))


def compute_code_identity(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(b"aggie.cycle27.week1_official_final_scoring.code_bundle.v1\n")
    for relative in CODE_BUNDLE_RELATIVE:
        path = repo_root / relative
        if not path.is_file():
            raise Week1Cycle27OfficialFinalScoringError(
                f"code bundle member missing: {relative}"
            )
        hasher.update(b"PATH:")
        hasher.update(posix_relative(relative).encode("utf-8"))
        hasher.update(b"\n")
        hasher.update(path.read_bytes())
        hasher.update(b"\n")
    return hasher.hexdigest()


def parser_module_sha256(repo_root: Path) -> str:
    path = repo_root / PARSER_MODULE_RELATIVE
    if not path.is_file():
        raise Week1Cycle27OfficialFinalScoringError("parser module missing")
    return sha256_file(path)


def freeze_before_kickoff(freeze_utc: str, kickoff_utc: str | None) -> bool:
    freeze = parse_utc(freeze_utc)
    kickoff = parse_utc(kickoff_utc)
    if freeze is None or kickoff is None:
        return False
    return freeze < kickoff


def receipt_after_kickoff(
    retrieved_at_utc: str | None, kickoff_utc: str | None
) -> bool:
    retrieved = parse_utc(retrieved_at_utc)
    kickoff = parse_utc(kickoff_utc)
    if retrieved is None or kickoff is None:
        return False
    return retrieved > kickoff


def favorite_direction(probability: float) -> str:
    if probability > 0.5:
        return "HOME"
    if probability < 0.5:
        return "AWAY"
    return NO_DIRECTION


def frozen_probability_identity(row: Mapping[str, Any]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {
                "candidate_id": row.get("candidate_id"),
                "checkpoint_id": row.get("checkpoint_id"),
                "expected_margin_home": row.get("expected_margin_home"),
                "ncaa_contest_id": row.get("ncaa_contest_id"),
                "probability_home": row.get("probability_home"),
            }
        )
    )


def build_pinned_input_manifest(
    *,
    captures: Sequence[Mapping[str, Any]],
    forecast_payload: Mapping[str, Any],
    as_of_utc: str,
    parser_module_sha256_hex: str,
    freeze_utc: str,
    authorized_exclusion_contest_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Pin an explicit capture list. Callers must not glob during replay."""

    if parse_utc(as_of_utc) is None:
        raise Week1Cycle27OfficialFinalScoringError("as_of_utc is not a UTC instant")
    pinned_captures: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in captures:
        relative = posix_relative(str(raw.get("relative_path") or ""))
        digest = str(raw.get("sha256") or "").strip().lower()
        size = int(raw.get("bytes") or 0)
        if not relative or not digest or size < 0:
            raise Week1Cycle27OfficialFinalScoringError(
                "pinned capture requires relative_path, sha256, and bytes"
            )
        if digest in seen:
            raise Week1Cycle27OfficialFinalScoringError(
                f"duplicate pinned capture sha256: {digest}"
            )
        seen.add(digest)
        pinned_captures.append(
            {
                "bytes": size,
                "receipt_id": raw.get("receipt_id"),
                "relative_path": relative,
                "retrieved_at_utc": raw.get("retrieved_at_utc"),
                "sha256": digest,
            }
        )
    pinned_captures.sort(key=lambda item: (item["sha256"], item["relative_path"]))
    forecast = {
        "bytes": int(forecast_payload["bytes"]),
        "relative_path": posix_relative(str(forecast_payload["relative_path"])),
        "sha256": str(forecast_payload["sha256"]).strip().lower(),
    }
    manifest = {
        "artifact_type": "CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING_INPUT_MANIFEST",
        "as_of_utc": as_of_utc,
        "authorized_exclusion_contest_ids": sorted(
            {str(item) for item in (authorized_exclusion_contest_ids or []) if item}
        ),
        "capture_mode": CAPTURE_MODE_PINNED,
        "captures": pinned_captures,
        "forecast_payload": forecast,
        "freeze_utc": freeze_utc,
        "parser_module_sha256": parser_module_sha256_hex,
        "parser_version": PARSER_VERSION,
        "schema_version": SCHEMA_VERSION,
    }
    manifest["manifest_identity"] = sha256_bytes(canonical_json_bytes(manifest))
    return manifest


def capture_record_from_file(
    *,
    data_root: Path,
    relative_path: str,
    retrieved_at_utc: str | None = None,
    receipt_id: str | None = None,
) -> dict[str, Any]:
    path = data_root / posix_relative(relative_path)
    payload = path.read_bytes()
    digest = sha256_bytes(payload)
    return {
        "bytes": len(payload),
        "receipt_id": receipt_id or digest,
        "relative_path": posix_relative(relative_path),
        "retrieved_at_utc": retrieved_at_utc,
        "sha256": digest,
    }


def load_pinned_captures(
    *,
    data_root: Path,
    manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if manifest.get("capture_mode") != CAPTURE_MODE_PINNED:
        raise Week1Cycle27OfficialFinalScoringError(
            "capture_mode must be PINNED_MANIFEST"
        )
    loaded: list[dict[str, Any]] = []
    for capture in manifest.get("captures") or []:
        relative = posix_relative(str(capture["relative_path"]))
        path = data_root / relative
        if not path.is_file():
            raise Week1Cycle27OfficialFinalScoringError(
                f"pinned capture missing: {relative}"
            )
        payload = path.read_bytes()
        digest = sha256_bytes(payload)
        if digest != str(capture["sha256"]).lower():
            raise Week1Cycle27OfficialFinalScoringError(
                f"pinned capture hash drift: {relative}"
            )
        if len(payload) != int(capture["bytes"]):
            raise Week1Cycle27OfficialFinalScoringError(
                f"pinned capture size drift: {relative}"
            )
        loaded.append(
            {
                **dict(capture),
                "document": payload.decode("utf-8", errors="replace"),
            }
        )
    return loaded


def load_pinned_forecast_rows(
    *,
    data_root: Path,
    manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    forecast = manifest["forecast_payload"]
    relative = posix_relative(str(forecast["relative_path"]))
    path = data_root / relative
    payload = path.read_bytes()
    digest = sha256_bytes(payload)
    if digest != str(forecast["sha256"]).lower():
        raise Week1Cycle27OfficialFinalScoringError("MUTATED_FROZEN_FORECAST_PAYLOAD")
    if len(payload) != int(forecast["bytes"]):
        raise Week1Cycle27OfficialFinalScoringError(
            "MUTATED_FROZEN_FORECAST_PAYLOAD_SIZE"
        )
    rows = read_jsonl(path)
    for row in rows:
        recomputed = frozen_probability_identity(row)
        bound = str(row.get("frozen_probability_identity") or "")
        if bound and bound != recomputed:
            raise Week1Cycle27OfficialFinalScoringError(
                "MUTATED_FROZEN_PROBABILITY_NOT_BINDING"
            )
        row["frozen_probability_identity"] = recomputed
    return rows


def terminal_snapshot(
    card: Mapping[str, Any], capture: Mapping[str, Any]
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
        "capture_sha256": capture["sha256"],
        "retrieved_at_utc": capture.get("retrieved_at_utc"),
        "receipt_id": capture.get("receipt_id"),
    }


def merge_pinned_terminals(
    captures: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    terminals: dict[str, dict[str, Any]] = {}
    contributing: list[str] = []
    conflicts: dict[str, list[dict[str, Any]]] = {}
    rejected_before_kickoff: list[dict[str, Any]] = []
    card_count = 0
    for capture in captures:
        cards = parse_scoreboard_cards(str(capture["document"]))
        card_count += len(cards)
        for card in cards:
            snapshot = terminal_snapshot(card, capture)
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
            digest = str(snapshot["capture_sha256"])
            if digest not in contributing:
                contributing.append(digest)
    return {
        "terminals": terminals,
        "contributing_capture_sha256": contributing,
        "quarantined_conflicts": conflicts,
        "rejected_receipts_before_kickoff": rejected_before_kickoff,
        "scoreboard_html_count": len(captures),
        "scoreboard_card_count": card_count,
    }


def reject_pre_kickoff_receipts(
    *,
    merged: Mapping[str, Any],
    kickoff_by_contest: Mapping[str, str | None],
) -> dict[str, Any]:
    terminals = dict(merged["terminals"])
    rejected: list[dict[str, Any]] = list(
        merged.get("rejected_receipts_before_kickoff") or []
    )
    contributing = [
        digest
        for digest in merged["contributing_capture_sha256"]
        if any(row.get("capture_sha256") == digest for row in terminals.values())
    ]
    for contest_id, snapshot in list(terminals.items()):
        kickoff = kickoff_by_contest.get(contest_id)
        retrieved = snapshot.get("retrieved_at_utc")
        if retrieved is None:
            continue
        if not receipt_after_kickoff(str(retrieved), kickoff):
            rejected.append(
                {
                    "ncaa_contest_id": contest_id,
                    "capture_sha256": snapshot.get("capture_sha256"),
                    "receipt_id": snapshot.get("receipt_id"),
                    "retrieved_at_utc": retrieved,
                    "kickoff_bound_utc": kickoff,
                    "reason": "RECEIPT_BEFORE_KICKOFF_REJECTED",
                }
            )
            terminals.pop(contest_id, None)
    contributing = []
    for snapshot in terminals.values():
        digest = str(snapshot["capture_sha256"])
        if digest not in contributing:
            contributing.append(digest)
    return {
        **dict(merged),
        "terminals": terminals,
        "contributing_capture_sha256": contributing,
        "rejected_receipts_before_kickoff": rejected,
    }


def _score_metrics(
    *,
    probability_home: float,
    expected_margin_home: float | None,
    home_points: int,
    away_points: int,
    candidate_id: str,
) -> dict[str, Any]:
    label = 1 if home_points > away_points else 0
    actual_margin = float(home_points - away_points)
    probability = float(probability_home)
    if not (0.0 <= probability <= 1.0):
        raise Week1Cycle27OfficialFinalScoringError(
            "probability outside [0,1] before metrics"
        )
    brier = (probability - float(label)) ** 2
    clipped = min(max(probability, 1e-15), 1.0 - 1e-15)
    if label == 1:
        log_loss = -math.log(clipped)
    else:
        log_loss = -math.log(1.0 - clipped)
    direction = favorite_direction(probability)
    prediction_error_margin = None
    residual_margin = None
    if candidate_id == MARGIN_CAPABLE and expected_margin_home is not None:
        predicted_margin = float(expected_margin_home)
        prediction_error_margin = predicted_margin - actual_margin
        residual_margin = actual_margin - predicted_margin
    return {
        "label_home_win": label,
        "actual_margin_home": actual_margin,
        "brier": brier,
        "binary_log_loss": log_loss,
        "favorite_direction": direction,
        "prediction_error_margin": prediction_error_margin,
        "residual_margin": residual_margin,
        "prediction_error_definition": "predicted_minus_actual",
        "residual_definition": "actual_minus_predicted",
    }


def classify_forecast_row(
    *,
    row: Mapping[str, Any],
    freeze_utc: str,
    terminals: Mapping[str, Mapping[str, Any]],
    conflicts: Mapping[str, Any],
    authorized_exclusions: set[str],
) -> dict[str, Any]:
    contest_id = str(row.get("ncaa_contest_id") or "")
    candidate_id = str(row.get("candidate_id") or "")
    base = {
        "ncaa_contest_id": contest_id,
        "candidate_id": candidate_id,
        "forecast_row_identity": row.get("forecast_row_identity"),
        "frozen_probability_identity": row.get("frozen_probability_identity")
        or frozen_probability_identity(row),
        "checkpoint_id": row.get("checkpoint_id"),
        "control_only": bool(row.get("control_only")),
        "forecast_probability_home": row.get("probability_home"),
        "forecast_expected_margin_home": row.get("expected_margin_home"),
        "kickoff_bound_utc": row.get("kickoff_bound_utc"),
        "scored": False,
    }
    if contest_id in authorized_exclusions:
        return {
            **base,
            "state": STATE_AUTHORIZED_EXCLUSION,
            "unscored_reason": "AUTHORIZED_EXCLUSION",
        }
    if contest_id in conflicts:
        return {
            **base,
            "state": STATE_CONFLICT,
            "unscored_reason": "CONFLICT_QUARANTINED",
        }
    if not freeze_before_kickoff(freeze_utc, row.get("kickoff_bound_utc")):
        return {
            **base,
            "state": STATE_MISSED_CUTOFF,
            "unscored_reason": "MISSED_CUTOFF_NO_BACKFILL",
        }
    final = terminals.get(contest_id)
    if final is None:
        return {
            **base,
            "state": STATE_AWAITING,
            "unscored_reason": "AWAITING_OFFICIAL_FINAL",
        }
    home_points = int(final["home_points"])
    away_points = int(final["away_points"])
    if home_points == away_points:
        return {
            **base,
            "home_points": home_points,
            "away_points": away_points,
            "final_status_text": final.get("final_status_text"),
            "source_capture_sha256": final.get("capture_sha256"),
            "actual_margin_home": float(home_points - away_points),
            "state": STATE_AUTHORIZED_EXCLUSION,
            "unscored_reason": "TIE_OR_NO_CONTEST_NOT_SILENTLY_COUNTED",
        }
    probability = row.get("probability_home")
    if probability is None:
        return {
            **base,
            "home_points": home_points,
            "away_points": away_points,
            "final_status_text": final.get("final_status_text"),
            "source_capture_sha256": final.get("capture_sha256"),
            "actual_margin_home": float(home_points - away_points),
            "label_home_win": int(home_points > away_points),
            "state": STATE_ABSTAINED,
            "unscored_reason": "ABSTAINED_OR_MISSING_PROBABILITY",
        }
    if candidate_id == MARGIN_CAPABLE and row.get("expected_margin_home") is None:
        return {
            **base,
            "home_points": home_points,
            "away_points": away_points,
            "final_status_text": final.get("final_status_text"),
            "source_capture_sha256": final.get("capture_sha256"),
            "actual_margin_home": float(home_points - away_points),
            "label_home_win": int(home_points > away_points),
            "state": STATE_ABSTAINED,
            "unscored_reason": "MARGIN_NOT_SUPPORTED_OR_MISSING",
        }
    metrics = _score_metrics(
        probability_home=float(probability),
        expected_margin_home=row.get("expected_margin_home"),
        home_points=home_points,
        away_points=away_points,
        candidate_id=candidate_id,
    )
    return {
        **base,
        "home_points": home_points,
        "away_points": away_points,
        "final_status_text": final.get("final_status_text"),
        "source_capture_sha256": final.get("capture_sha256"),
        "state": STATE_SCORED,
        "unscored_reason": None,
        "scored": True,
        **metrics,
    }


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def unique_game_empirical_assessment(
    scored_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
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
                "directional_correct": [],
                "games": set(),
            },
        )
        if contest_id in bucket["games"]:
            continue
        bucket["games"].add(contest_id)
        bucket["brier"].append(float(row["brier"]))
        bucket["log_loss"].append(float(row["binary_log_loss"]))
        probability = float(row["forecast_probability_home"])
        direction = str(
            row.get("favorite_direction") or favorite_direction(probability)
        )
        label = row.get("label_home_win")
        if direction != NO_DIRECTION and label in (0, 1):
            predicted_home = direction == "HOME"
            bucket["directional_correct"].append(float(predicted_home == bool(label)))
        if candidate_id == MARGIN_CAPABLE and row.get("residual_margin") is not None:
            bucket["margin_abs"].append(abs(float(row["residual_margin"])))
    unique_count = len(unique_games)
    skill_state = (
        "NOT_ESTABLISHED"
        if unique_count < PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM
        else "DEVELOPMENT_EVIDENCE_ONLY"
    )
    candidates = []
    for candidate_id in sorted(by_candidate):
        bucket = by_candidate[candidate_id]
        directional_den = len(bucket["directional_correct"])
        entry = {
            "candidate_id": candidate_id,
            "unique_games": len(bucket["games"]),
            "brier": _mean(bucket["brier"]),
            "log_loss": _mean(bucket["log_loss"]),
            "directional_numerator": (
                int(sum(bucket["directional_correct"])) if directional_den else 0
            ),
            "directional_denominator": directional_den,
            "directional_accuracy": (
                _mean(bucket["directional_correct"]) if directional_den else None
            ),
            "no_direction_excluded_from_directional": True,
            "control_only": candidate_id == "national_base_rate",
            "margin_mae": (
                _mean(bucket["margin_abs"]) if candidate_id == MARGIN_CAPABLE else None
            ),
        }
        candidates.append(entry)
    return {
        "PREDICTIVE_SKILL_EVIDENCE_STATE": skill_state,
        "predeclared_min_unique_games_for_skill_claim": (
            PREDECLARED_MIN_UNIQUE_GAMES_FOR_SKILL_CLAIM
        ),
        "unique_scored_games": unique_count,
        "denominator": "UNIQUE_GAME_NOT_ORIENTED_ROW_NOT_REPEATED_CHECKPOINT",
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


def state_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {state: 0 for state in SCHEMA_CONTRACT["states"]}
    for row in rows:
        state = str(row.get("state") or "")
        if state in counts:
            counts[state] += 1
        else:
            counts[state] = counts.get(state, 0) + 1
    return counts


def score_from_pinned_manifest(
    *,
    repo_root: Path,
    data_root: Path,
    manifest: Mapping[str, Any],
    issued_at_utc: str,
) -> dict[str, Any]:
    if manifest.get("parser_version") != PARSER_VERSION:
        raise Week1Cycle27OfficialFinalScoringError("parser_version mismatch")
    expected_parser = parser_module_sha256(repo_root)
    if str(manifest.get("parser_module_sha256") or "") != expected_parser:
        raise Week1Cycle27OfficialFinalScoringError("parser_module_sha256 mismatch")
    freeze_utc = str(manifest.get("freeze_utc") or "")
    forecast_rows = load_pinned_forecast_rows(data_root=data_root, manifest=manifest)
    captures = load_pinned_captures(data_root=data_root, manifest=manifest)
    merged = merge_pinned_terminals(captures)
    kickoff_by_contest = {
        str(row.get("ncaa_contest_id") or ""): row.get("kickoff_bound_utc")
        for row in forecast_rows
        if row.get("ncaa_contest_id")
    }
    merged = reject_pre_kickoff_receipts(
        merged=merged, kickoff_by_contest=kickoff_by_contest
    )
    authorized = set(manifest.get("authorized_exclusion_contest_ids") or [])
    scored_rows = [
        classify_forecast_row(
            row=row,
            freeze_utc=freeze_utc,
            terminals=merged["terminals"],
            conflicts=merged["quarantined_conflicts"],
            authorized_exclusions=authorized,
        )
        for row in forecast_rows
    ]
    payload = jsonl_bytes(scored_rows)
    dataset_identity = sha256_bytes(payload)
    empirical = unique_game_empirical_assessment(scored_rows)
    counts = state_counts(scored_rows)
    scored_count = counts.get(STATE_SCORED, 0)
    expected_contests = sorted(
        {
            str(row.get("ncaa_contest_id") or "")
            for row in forecast_rows
            if row.get("ncaa_contest_id")
        }
    )
    temporal_incomplete = True
    temporal_path = repo_root / TEMPORAL_AUTHORITY_RELATIVE
    if temporal_path.is_file():
        temporal = read_json(temporal_path)
        temporal_incomplete = (
            str(
                (temporal.get("assessment") or {}).get("primary_trust_recovery")
                or PRIMARY_INCOMPLETE
            )
            == PRIMARY_INCOMPLETE
        )
    missing_receipt_times = any(
        capture.get("retrieved_at_utc") in (None, "")
        for capture in manifest.get("captures") or []
    )
    if missing_receipt_times:
        temporal_incomplete = True
    result = PASS_RESULT
    if temporal_incomplete:
        result = "UNTRUSTED_SHADOW_PRIMARY_TRUST_RECOVERY_INCOMPLETE"
    gate = {
        "artifact_type": "CYCLE27_WEEK1_OFFICIAL_FINAL_SCORING",
        "schema_version": SCHEMA_VERSION,
        "schema_identity": schema_identity(),
        "contract_id": CONTRACT_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": issued_at_utc,
        "result": result,
        "publication_label": SHADOW_CLASSIFICATION,
        "operator_hold": "ACTIVE",
        "merge_authorized": False,
        "week1_outcome_training_forbidden": True,
        "forecast_payloads_rewritten": False,
        "predecessor_scoring_payload_rewritten": False,
        "checkpoint_scored": "EARLY_WEEK1",
        "t24h_backfill": False,
        "t90m_backfill": False,
        "capture_mode": CAPTURE_MODE_PINNED,
        "input_manifest_identity": manifest.get("manifest_identity"),
        "parser_version": PARSER_VERSION,
        "parser_module_sha256": expected_parser,
        "as_of_utc": manifest.get("as_of_utc"),
        "primary_trust_recovery": (
            PRIMARY_INCOMPLETE if temporal_incomplete else "NOT_CLAIMED"
        ),
        "bound_predecessors": {
            "week1_successor_gate_identity": None,
            "forecast_payload_sha256": manifest["forecast_payload"]["sha256"],
            "early_week1_freeze_utc": freeze_utc,
            "predecessor_scoring_gate_identity": PREDECESSOR_SCORING_GATE_IDENTITY,
            "predecessor_scoring_dataset_identity": (
                PREDECESSOR_SCORING_DATASET_IDENTITY
            ),
            "predecessor_joined_forecast_rows": PREDECESSOR_JOINED_FORECAST_ROWS,
            "predecessor_scored_row_count": PREDECESSOR_SCORED_ROW_COUNT,
            "predecessor_scoring_payload_rewritten": False,
        },
        "summary": {
            "scoreboard_html_count": merged["scoreboard_html_count"],
            "scoreboard_cards": merged["scoreboard_card_count"],
            "terminal_contest_count": len(merged["terminals"]),
            "terminal_contest_ids": sorted(merged["terminals"]),
            "quarantined_conflict_contest_ids": sorted(merged["quarantined_conflicts"]),
            "rejected_receipt_before_kickoff_count": len(
                merged["rejected_receipts_before_kickoff"]
            ),
            "universe_contest_count": len(expected_contests),
            "forecast_row_count": len(scored_rows),
            "joined_forecast_rows": sum(
                1
                for row in scored_rows
                if row.get("state")
                in {STATE_SCORED, STATE_ABSTAINED, STATE_AUTHORIZED_EXCLUSION}
                and row.get("home_points") is not None
            ),
            "scored_row_count": scored_count,
            "unique_scored_games": empirical["unique_scored_games"],
            "state_counts": counts,
        },
        "empirical_assessment": empirical,
        "payloads": {
            "input_manifest": {
                "relative_path": MANIFEST_RELATIVE,
                "sha256": manifest.get("manifest_identity"),
            },
            "scoring_rows": {
                "relative_path": ROWS_RELATIVE,
                "sha256": dataset_identity,
                "bytes": len(payload),
                "row_count": len(scored_rows),
            },
        },
        "scientific_nonclaims": [
            "Does not train, select, tune or promote using Week 1 outcomes.",
            "Does not rewrite frozen EARLY_WEEK1 forecast payloads.",
            "Does not rewrite the predecessor Cycle 26 scoring gate or dataset.",
            "Does not backfill missed T-24H or T-90M checkpoints.",
            "Does not claim predictive skill or production credibility.",
            "Does not enumerate a live changing directory for historical replay.",
            "Does not release the operator hold or all-cycle trust gate.",
            "UNTRUSTED_SHADOW only; PRIMARY_TRUST_RECOVERY_INCOMPLETE remains allowed.",
        ],
        "_payload_bytes": payload,
        "_scored_rows": scored_rows,
        "_manifest": dict(manifest),
    }
    gate["dataset_identity"] = dataset_identity
    return gate


def bind_week1_gate_identity(
    gate: dict[str, Any], *, repo_root: Path
) -> dict[str, Any]:
    week1_path = repo_root / WEEK1_GATE_RELATIVE
    if week1_path.is_file():
        week1 = read_json(week1_path)
        bound = dict(gate.get("bound_predecessors") or {})
        bound["week1_successor_gate_identity"] = week1.get("gate_identity")
        forecast_sha = week1.get("payloads", {}).get("forecast_rows", {}).get("sha256")
        if forecast_sha and forecast_sha != bound.get("forecast_payload_sha256"):
            raise Week1Cycle27OfficialFinalScoringError("FORECAST_PAYLOAD_HASH_DRIFT")
        gate["bound_predecessors"] = bound
    gate["code_identity"] = compute_code_identity(repo_root)
    public = {key: value for key, value in gate.items() if not str(key).startswith("_")}
    gate["gate_identity"] = sha256_bytes(canonical_json_bytes(public))
    return gate


def materialize(
    *,
    repo_root: Path,
    data_root: Path,
    manifest: Mapping[str, Any],
    issued_at_utc: str,
) -> dict[str, Any]:
    gate = score_from_pinned_manifest(
        repo_root=repo_root,
        data_root=data_root,
        manifest=manifest,
        issued_at_utc=issued_at_utc,
    )
    gate = bind_week1_gate_identity(gate, repo_root=repo_root)
    payload = gate.pop("_payload_bytes")
    scored_rows = gate.pop("_scored_rows")
    pinned = gate.pop("_manifest")
    del scored_rows
    manifest_path = repo_root / MANIFEST_RELATIVE
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(
        json.dumps(pinned, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    rows_path = repo_root / ROWS_RELATIVE
    rows_path.write_bytes(payload)
    gate_path = repo_root / GATE_RELATIVE
    gate_path.write_bytes(
        json.dumps(gate, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    return gate
