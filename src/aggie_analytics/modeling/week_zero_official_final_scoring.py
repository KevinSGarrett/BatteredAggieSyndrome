"""BAT-674 Week Zero 2026 official-final scoring core.

This module is the single deterministic derivation used by both the BAT-674
producer and the BAT-674 consumer validator.  Everything it emits is a pure
function of raw official bytes plus the immutable BAT-664/BAT-665 predecessor
artifacts, so the validator can rebuild every committed object from the raw
NCAA HTML without calling the network and without writing anything.

Three corrections to the earlier Cycle #22 attempt are enforced here.

Source substitution.  The NCAA scoreboard answered the August 27 and August 28
requests with August 29 content.  A card is admissible as an official final only
when its source-published game date equals the requested game date, so the eight
August 29 finals are recorded once rather than three times.

Orientation.  A final is bound to a frozen contest only after the NCAA contest
identifier, the ordered away/home source participants and the canonical away/home
identities all match the frozen snapshot, the final was retrieved after kickoff,
the status is terminal, and the winner is internally consistent with the score.

Denominators.  Coverage and abstention are computed against the predeclared
eligible frozen-row opportunity count for that one candidate, never against the
pooled row count belonging to every candidate.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "aggie.shadow.week_zero_2026_official_final_scoring_successor.v1"
CONTRACT_ID = "BAT-674-WEEK-ZERO-2026-OFFICIAL-FINAL-SCORING-SUCCESSOR-V1"
JIRA_KEY = "BAT-674"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK-ZERO-OFFICIAL-FINAL-SCORING-001"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"

NON_AUTHORITATIVE_KEYS = frozenset({"gate_identity"})

LOG_LOSS_CLIP = (1e-15, 1.0 - 1e-15)
CALIBRATION_EDGES: tuple[float, ...] = (
    0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
)
TINY_SAMPLE_THRESHOLD = 30

SCORED = "SCORED"
AWAITING = "AWAITING_OFFICIAL_FINAL"
MISSED_CUTOFF = "MISSED_CUTOFF_NO_BACKFILL"
QUARANTINED = "CONFLICT_QUARANTINED"
PROOF_COMPLETE = "TEMPORAL_PROOF_COMPLETE"

ADMISSIBLE = "ADMISSIBLE_REQUESTED_DATE_MATCHES_SOURCE_PUBLISHED_DATE"
SUBSTITUTED = "SOURCE_DATE_SUBSTITUTION_OBSERVATION_NOT_ADMISSIBLE"

NO_DIRECTION = "NO_DIRECTION"

RECONCILIATION_EXACT = "NCAA_PREDECESSOR_CONTEST_ID_AND_ORIENTATION_EXACT"
RECONCILIATION_CFBD_QUOTA = "CFBD_ENRICHMENT_UNAVAILABLE_QUOTA"
RECONCILIATION_MISSED = "MISSED_CUTOFF_NO_BACKFILL"
RECONCILIATION_QUARANTINED = "CONFLICT_QUARANTINED"
RECONCILIATION_ABSTAIN = "UNRESOLVED_ABSTAIN"

UNSUPPORTED_ENTITY_FAILURE = "CANONICAL_IDENTITY_ABSENT_FOR_AT_LEAST_ONE_PARTICIPANT"


def failure_is_conflict(reason: str) -> bool:
    """An unresolved entity is an absence of evidence, not a conflict of evidence."""
    return reason != UNSUPPORTED_ENTITY_FAILURE


class OfficialFinalScoringViolation(RuntimeError):
    """Raised when an input or artifact is not admissible for BAT-674 scoring."""


# --------------------------------------------------------------------------- #
# canonical helpers
# --------------------------------------------------------------------------- #


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def identity_excluding_identity_field(payload: Mapping[str, Any]) -> str:
    return sha256_of({k: v for k, v in payload.items() if k not in NON_AUTHORITATIVE_KEYS})


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# raw scoreboard parsing
# --------------------------------------------------------------------------- #

_ROW_OPEN = re.compile(r'<tr\s+id="contest_(\d+)"\s*>')
_TEAM_ANCHOR = re.compile(r'href="/teams/(\d+)"\s*>([^<]+?)\s*</a>')
_SCORE_DIV = re.compile(r'<div\s+id="score_(\d+)"[^>]*>\s*(-?\d+)\s*</div>')
_NAME_RECORD = re.compile(r"^(.*?)\s*\((\d+)-(\d+)\)$")
_HEADER_DATETIME = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}\s*[AP]M)([^<]*)", re.IGNORECASE
)
_ATTENDANCE = re.compile(r"Attend:\s*([\d,]+)")
_TERMINAL_STATUS = re.compile(
    r"livestream_status_(\d+)\s+livestream_status\s+livestream_game_over\s*\">([^<]+?)\s*</div>"
)
_FORM_GAME_DATE = re.compile(r'<input[^>]*name="game_date"[^>]*value="([^"]*)"')


def _split_name_and_record(raw: str) -> tuple[str, dict[str, int] | None]:
    text = html.unescape(raw).strip()
    match = _NAME_RECORD.match(text)
    if not match:
        return text, None
    return match.group(1).strip(), {
        "wins": int(match.group(2)),
        "losses": int(match.group(3)),
    }


def _normalize_source_date(value: str | None) -> str | None:
    if not value or "/" not in value:
        return None
    month, day, year = value.split("/")
    return f"{year}-{month}-{day}"


def parse_scoreboard_cards(document: str) -> list[dict[str, Any]]:
    """Parse one NCAA livestream scoreboard page into ordered contest cards.

    One contest renders as a table whose first participant row is the away team
    and whose second is the home team.  The terminal status is emitted inside an
    HTML comment carrying the ``livestream_game_over`` class, so it is recovered
    from the comment body rather than from rendered text.
    """

    terminal_status: dict[str, str] = {}
    for contest_id, status in _TERMINAL_STATUS.findall(document):
        terminal_status.setdefault(contest_id, status.strip())

    opens = list(_ROW_OPEN.finditer(document))
    per_contest: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []

    for index, match in enumerate(opens):
        contest_id = match.group(1)
        start = match.end()
        end = opens[index + 1].start() if index + 1 < len(opens) else len(document)
        segment = document[start:end]

        anchor = _TEAM_ANCHOR.search(segment)
        if anchor is None:
            continue
        score = _SCORE_DIV.search(segment)
        name, record = _split_name_and_record(anchor.group(2))
        entry = {
            "source_team_id": anchor.group(1),
            "source_team_name": name,
            "record_after_contest": record,
            "points": int(score.group(2)) if score else None,
            "source_score_element_id": score.group(1) if score else None,
        }
        if contest_id not in per_contest:
            per_contest[contest_id] = []
            order.append(contest_id)
        per_contest[contest_id].append(entry)

    cards: list[dict[str, Any]] = []
    for contest_id in order:
        rows = per_contest[contest_id]
        if len(rows) != 2:
            cards.append(
                {
                    "ncaa_contest_id": contest_id,
                    "parse_state": "REJECTED_PARTICIPANT_ROW_COUNT",
                    "participant_row_count": len(rows),
                }
            )
            continue

        anchor_position = document.find(f'<tr id="contest_{contest_id}">')
        header_slice = document[max(0, anchor_position - 1500) : anchor_position]
        header = _HEADER_DATETIME.search(header_slice)
        attendance = _ATTENDANCE.search(header_slice)

        away, home = rows[0], rows[1]
        winner = None
        if away["points"] is not None and home["points"] is not None:
            if home["points"] > away["points"]:
                winner = "HOME"
            elif away["points"] > home["points"]:
                winner = "AWAY"
            else:
                winner = "TIE"

        cards.append(
            {
                "ncaa_contest_id": contest_id,
                "parse_state": "PARSED",
                "source_published_game_date": _normalize_source_date(
                    header.group(1) if header else None
                ),
                "source_published_clock_text": header.group(2).strip() if header else None,
                "source_published_broadcast_text": (
                    (header.group(3).strip() or None) if header else None
                ),
                "attendance_text": attendance.group(1) if attendance else None,
                "final_status_text": terminal_status.get(contest_id),
                "final_status_is_terminal": contest_id in terminal_status,
                "away_source_team_id": away["source_team_id"],
                "away_source_team_name": away["source_team_name"],
                "away_points": away["points"],
                "away_record_after_contest": away["record_after_contest"],
                "home_source_team_id": home["source_team_id"],
                "home_source_team_name": home["source_team_name"],
                "home_points": home["points"],
                "home_record_after_contest": home["record_after_contest"],
                "winner_orientation": winner,
                "home_win": None if winner in (None, "TIE") else int(winner == "HOME"),
            }
        )
    return cards


def source_published_form_date(document: str) -> str | None:
    """The date the source itself says the returned scoreboard represents."""
    values = sorted(set(_FORM_GAME_DATE.findall(document)))
    if len(values) != 1:
        return None
    return _normalize_source_date(values[0])


# --------------------------------------------------------------------------- #
# capture manifest with admissibility gating
# --------------------------------------------------------------------------- #


def build_official_capture_manifest(
    *,
    captures: Sequence[Mapping[str, Any]],
    contract_sha256: str,
    issued_at_utc: str,
) -> dict[str, Any]:
    """Materialize the corrected BAT-674 official capture manifest.

    ``captures`` carries one entry per requested game date with the raw bytes
    already resolved.  A capture whose source-published date differs from the
    requested date is preserved as a source-substitution observation and cannot
    contribute a single admissible official final.
    """

    capture_rows: list[dict[str, Any]] = []
    admissible_finals: list[dict[str, Any]] = []
    substitution_observations: list[dict[str, Any]] = []

    for capture in sorted(captures, key=lambda row: str(row["requested_game_date"])):
        requested = str(capture["requested_game_date"])
        document = str(capture["document"])
        raw_sha256 = hashlib.sha256(capture["raw_bytes"]).hexdigest()
        if raw_sha256 != str(capture["raw_sha256"]):
            raise OfficialFinalScoringViolation(
                f"raw capture bytes do not match the declared SHA-256 for {requested}"
            )

        published = source_published_form_date(document)
        cards = parse_scoreboard_cards(document)
        admissible = published == requested

        capture_rows.append(
            {
                "requested_game_date": requested,
                "source_published_game_date": published,
                "admissibility": ADMISSIBLE if admissible else SUBSTITUTED,
                "is_source_substitution": not admissible,
                "raw_sha256": raw_sha256,
                "raw_bytes": len(capture["raw_bytes"]),
                "raw_relative_path": str(capture["raw_relative_path"]),
                "request_identity_sha256": str(capture["request_identity_sha256"]),
                "retrieved_at_utc": str(capture["retrieved_at_utc"]),
                "route_id": str(capture["route_id"]),
                "source_uri": str(capture["source_uri"]),
                "parsed_card_count": len(cards),
            }
        )

        for card in cards:
            if card.get("parse_state") != "PARSED":
                continue
            bound = {
                **card,
                "requested_game_date": requested,
                "capture_source_published_game_date": published,
                "capture_raw_sha256": raw_sha256,
                "capture_request_identity_sha256": str(capture["request_identity_sha256"]),
                "capture_retrieved_at_utc": str(capture["retrieved_at_utc"]),
                "capture_route_id": str(capture["route_id"]),
                "capture_source_uri": str(capture["source_uri"]),
            }
            if not admissible:
                substitution_observations.append(
                    {
                        **bound,
                        "admissibility": SUBSTITUTED,
                        "exclusion_reason": (
                            "SOURCE_PUBLISHED_GAME_DATE_DOES_NOT_EQUAL_REQUESTED_GAME_DATE"
                        ),
                    }
                )
                continue
            if not card.get("final_status_is_terminal"):
                continue
            admissible_finals.append({**bound, "admissibility": ADMISSIBLE})

    admissible_finals.sort(key=lambda row: str(row["ncaa_contest_id"]))
    substitution_observations.sort(
        key=lambda row: (str(row["requested_game_date"]), str(row["ncaa_contest_id"]))
    )

    unique_final_ids = sorted({str(row["ncaa_contest_id"]) for row in admissible_finals})
    if len(unique_final_ids) != len(admissible_finals):
        duplicates = sorted(
            identifier
            for identifier, count in Counter(
                str(row["ncaa_contest_id"]) for row in admissible_finals
            ).items()
            if count > 1
        )
        raise OfficialFinalScoringViolation(
            f"duplicate admissible official finals for contests: {duplicates}"
        )

    core = {
        "artifact_type": "WEEK_ZERO_2026_OFFICIAL_FINAL_CAPTURE_MANIFEST",
        "admissible_final_capture_count": sum(
            1 for row in capture_rows if row["admissibility"] == ADMISSIBLE
        ),
        "capture_count": len(capture_rows),
        "captures": capture_rows,
        "contract_id": CONTRACT_ID,
        "contract_sha256": contract_sha256,
        "decision_unit": LOCAL_ISSUE_ID,
        "jira_key": JIRA_KEY,
        "lane": LANE,
        "official_finals": admissible_finals,
        "requested_game_dates": [row["requested_game_date"] for row in capture_rows],
        "schema_version": "aggie.shadow.week_zero_2026_official_final_capture.v1",
        "source_substitution_capture_count": sum(
            1 for row in capture_rows if row["admissibility"] == SUBSTITUTED
        ),
        "source_substitution_observations": substitution_observations,
        "unique_official_final_count": len(unique_final_ids),
    }
    identity = sha256_of(core)
    return {**core, "capture_identity": identity, "issued_at_utc": issued_at_utc}


# --------------------------------------------------------------------------- #
# real identities
# --------------------------------------------------------------------------- #


def frozen_forecast_row_identity(frozen_row: Mapping[str, Any]) -> str:
    """Immutable identity of the complete frozen predecessor forecast row."""
    return sha256_of(dict(frozen_row))


def temporal_verdict_row_identity(verdict_row: Mapping[str, Any]) -> str:
    return sha256_of(dict(verdict_row))


def contest_orientation_identity(proof: Mapping[str, Any]) -> str:
    return sha256_of(
        {
            "ncaa_contest_id": proof["ncaa_contest_id"],
            "away_source_team_id": proof["away_source_team_id"],
            "home_source_team_id": proof["home_source_team_id"],
            "away_canonical_team_id": proof["away_canonical_team_id"],
            "home_canonical_team_id": proof["home_canonical_team_id"],
            "away_points": proof["away_points"],
            "home_points": proof["home_points"],
            "official_raw_response_sha256": proof["official_raw_response_sha256"],
        }
    )


def scoring_row_identity(row: Mapping[str, Any]) -> str:
    return sha256_of({k: v for k, v in row.items() if k != "scoring_row_identity"})


# --------------------------------------------------------------------------- #
# orientation proof
# --------------------------------------------------------------------------- #


def prove_contest_orientation(
    *,
    final_card: Mapping[str, Any],
    frozen_contest_row: Mapping[str, Any],
    snapshot_record: Mapping[str, Any],
    predecessor_participants: Sequence[Mapping[str, Any]],
    capture_identity: str,
) -> dict[str, Any]:
    """Fail closed unless the captured final provably belongs to the frozen contest.

    The ordered participant check is identifier-based against the immutable BAT-665
    predecessor capture, which published the same provider's away-then-home source
    team identifiers.  Display names are only corroborating evidence; a contest is
    never bound by name alone.
    """

    failures: list[str] = []
    contest_id = str(frozen_contest_row["ncaa_contest_id"])

    if str(final_card.get("ncaa_contest_id")) != contest_id:
        failures.append("CONTEST_SUBSTITUTION")

    frozen_source_ids = [
        str(participant.get("source_team_id") or "") for participant in predecessor_participants
    ]
    captured_away_source = str(final_card.get("away_source_team_id") or "")
    captured_home_source = str(final_card.get("home_source_team_id") or "")

    if len(frozen_source_ids) == 2 and all(frozen_source_ids):
        if [captured_away_source, captured_home_source] == list(reversed(frozen_source_ids)):
            failures.append("ORDERED_PARTICIPANT_SWAP")
        elif [captured_away_source, captured_home_source] != frozen_source_ids:
            failures.append("ORDERED_PARTICIPANT_IDENTITY_MISMATCH")
    else:
        failures.append("PREDECESSOR_DOES_NOT_CARRY_TWO_ORDERED_SOURCE_PARTICIPANTS")

    frozen_names = [
        str(snapshot_record.get("away_source_display_name") or ""),
        str(snapshot_record.get("home_source_display_name") or ""),
    ]
    captured_names = [
        str(final_card.get("away_source_team_name") or ""),
        str(final_card.get("home_source_team_name") or ""),
    ]
    if all(frozen_names) and captured_names != frozen_names:
        failures.append("ORDERED_PARTICIPANT_DISPLAY_NAME_MISMATCH")

    away_canonical = snapshot_record.get("away_canonical_team_id")
    home_canonical = snapshot_record.get("home_canonical_team_id")
    if away_canonical is None or home_canonical is None:
        failures.append("CANONICAL_IDENTITY_ABSENT_FOR_AT_LEAST_ONE_PARTICIPANT")

    kickoff = parse_utc(frozen_contest_row.get("kickoff_bound_utc"))
    retrieved = parse_utc(final_card.get("capture_retrieved_at_utc"))
    if kickoff is None:
        failures.append("KICKOFF_BOUND_UNKNOWN")
    elif retrieved is None:
        failures.append("FINAL_RETRIEVAL_TIME_UNKNOWN")
    elif retrieved <= kickoff:
        failures.append("FINAL_CAPTURED_BEFORE_KICKOFF")

    frozen_date = str(snapshot_record.get("source_published_game_date") or "")
    captured_date = str(final_card.get("source_published_game_date") or "")
    if frozen_date and captured_date and frozen_date != captured_date:
        failures.append("KICKOFF_DATE_INCONSISTENT")
    if str(final_card.get("capture_source_published_game_date") or "") != str(
        final_card.get("requested_game_date") or ""
    ):
        failures.append("SOURCE_DATE_MISMATCH")

    if not final_card.get("final_status_is_terminal"):
        failures.append("FINAL_STATUS_NOT_TERMINAL")

    home_points = final_card.get("home_points")
    away_points = final_card.get("away_points")
    if not isinstance(home_points, int) or not isinstance(away_points, int):
        failures.append("SCORE_ABSENT")
    else:
        expected = None
        if home_points > away_points:
            expected = "HOME"
        elif away_points > home_points:
            expected = "AWAY"
        else:
            expected = "TIE"
        if str(final_card.get("winner_orientation")) != expected:
            failures.append("WINNER_INCONSISTENT_WITH_SCORE")
        if expected == "TIE":
            failures.append("UNRESOLVED_TIE")

    proof = {
        "ncaa_contest_id": contest_id,
        "away_source_team_id": captured_away_source,
        "away_source_team_name": final_card.get("away_source_team_name"),
        "home_source_team_id": captured_home_source,
        "home_source_team_name": final_card.get("home_source_team_name"),
        "away_canonical_team_id": away_canonical,
        "home_canonical_team_id": home_canonical,
        "away_points": away_points,
        "home_points": home_points,
        "winner_orientation": final_card.get("winner_orientation"),
        "home_win": final_card.get("home_win"),
        "final_status_text": final_card.get("final_status_text"),
        "final_status_is_terminal": bool(final_card.get("final_status_is_terminal")),
        "kickoff_bound_utc": frozen_contest_row.get("kickoff_bound_utc"),
        "final_capture_retrieved_at_utc": final_card.get("capture_retrieved_at_utc"),
        "final_capture_after_kickoff": (
            kickoff is not None and retrieved is not None and retrieved > kickoff
        ),
        "requested_game_date": final_card.get("requested_game_date"),
        "source_published_game_date": final_card.get("source_published_game_date"),
        "predecessor_ordered_source_team_ids": frozen_source_ids,
        "official_capture_identity": capture_identity,
        "official_raw_response_sha256": final_card.get("capture_raw_sha256"),
        "official_request_identity_sha256": final_card.get(
            "capture_request_identity_sha256"
        ),
        "proof_state": "ORIENTATION_PROVEN" if not failures else "ORIENTATION_FAILED_CLOSED",
        "failure_reasons": sorted(failures),
    }
    proof["contest_orientation_identity"] = contest_orientation_identity(proof)
    return proof


# --------------------------------------------------------------------------- #
# metrics with correct denominators
# --------------------------------------------------------------------------- #


def _clip(probability: float) -> float:
    return min(max(probability, LOG_LOSS_CLIP[0]), LOG_LOSS_CLIP[1])


def _bin_index(probability: float) -> int:
    if probability >= 1.0:
        return len(CALIBRATION_EDGES) - 2
    return int(probability * (len(CALIBRATION_EDGES) - 1))


def calibration_bins(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Full calibration-bin contents, not bare counts."""
    bins: list[dict[str, Any]] = []
    for index in range(len(CALIBRATION_EDGES) - 1):
        low = CALIBRATION_EDGES[index]
        high = CALIBRATION_EDGES[index + 1]
        members = [
            row
            for row in rows
            if _bin_index(float(row["frozen_probability_home_win"])) == index
        ]
        count = len(members)
        observed = sum(int(row["home_win"]) for row in members)
        bins.append(
            {
                "bin_lower": low,
                "bin_upper": high,
                "row_count": count,
                "mean_predicted_probability": (
                    sum(float(row["frozen_probability_home_win"]) for row in members) / count
                    if count
                    else None
                ),
                "observed_wins": observed,
                "empirical_win_rate": (observed / count if count else None),
                "tiny_sample_warning": bool(count) and count < TINY_SAMPLE_THRESHOLD,
            }
        )
    return bins


def favorite_direction(probability: float) -> str:
    """At exactly 0.5 there is no favorite; the threshold behaviour is predeclared."""
    if probability > 0.5:
        return "HOME"
    if probability < 0.5:
        return "AWAY"
    return NO_DIRECTION


def candidate_metrics(
    *,
    scored_rows: Sequence[Mapping[str, Any]],
    predeclared_eligible_opportunity_count: int,
    pending_row_count: int,
    temporal_exclusion_count: int,
    unsupported_count: int,
    missed_cutoff_with_no_forecast_count: int,
) -> dict[str, Any]:
    """Per-candidate metrics against that candidate's own opportunity population."""

    scored = list(scored_rows)
    count = len(scored)
    directional = [
        row for row in scored if favorite_direction(float(row["frozen_probability_home_win"])) != NO_DIRECTION
    ]
    no_direction = count - len(directional)
    correct = sum(
        1
        for row in directional
        if (float(row["frozen_probability_home_win"]) > 0.5 and int(row["home_win"]) == 1)
        or (float(row["frozen_probability_home_win"]) < 0.5 and int(row["home_win"]) == 0)
    )

    metrics: dict[str, Any] = {
        "predeclared_eligible_frozen_opportunity_count": predeclared_eligible_opportunity_count,
        "scored_row_count": count,
        "pending_row_count": pending_row_count,
        "temporal_exclusion_count": temporal_exclusion_count,
        "unsupported_count": unsupported_count,
        "missed_cutoff_with_no_forecast_count": missed_cutoff_with_no_forecast_count,
        "coverage": (
            count / predeclared_eligible_opportunity_count
            if predeclared_eligible_opportunity_count
            else None
        ),
        "abstention_count": max(predeclared_eligible_opportunity_count - count, 0),
        "classification_threshold_behaviour": (
            "PROBABILITY_EXACTLY_ONE_HALF_IS_NO_DIRECTION_AND_IS_EXCLUDED_FROM_DIRECTIONAL_METRICS"
        ),
        "directional_row_count": len(directional),
        "no_direction_row_count": no_direction,
        "calibration_bins": calibration_bins(scored),
        "tiny_sample_warning": count < TINY_SAMPLE_THRESHOLD,
    }

    if not count:
        metrics.update(
            {
                "brier_score": None,
                "log_loss": None,
                "directional_accuracy": None,
                "mean_absolute_residual": None,
                "mean_signed_residual": None,
                "expected_home_wins": 0.0,
                "candidate_observed_home_wins": 0,
            }
        )
        return metrics

    probabilities = [float(row["frozen_probability_home_win"]) for row in scored]
    outcomes = [int(row["home_win"]) for row in scored]
    metrics.update(
        {
            "brier_score": sum(
                (probability - outcome) ** 2
                for probability, outcome in zip(probabilities, outcomes)
            )
            / count,
            "log_loss": sum(
                -(
                    outcome * math.log(_clip(probability))
                    + (1 - outcome) * math.log(1 - _clip(probability))
                )
                for probability, outcome in zip(probabilities, outcomes)
            )
            / count,
            "directional_accuracy": (correct / len(directional) if directional else None),
            "mean_absolute_residual": sum(
                abs(outcome - probability)
                for probability, outcome in zip(probabilities, outcomes)
            )
            / count,
            "mean_signed_residual": sum(
                outcome - probability
                for probability, outcome in zip(probabilities, outcomes)
            )
            / count,
            "expected_home_wins": sum(probabilities),
            "candidate_observed_home_wins": sum(outcomes),
        }
    )
    return metrics


def pooled_model_row_diagnostics(scored_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Pooled diagnostics across every candidate row, explicitly labelled as pooled."""
    rows = list(scored_rows)
    return {
        "diagnostic_scope": "POOLED_ACROSS_EVERY_CANDIDATE_ROW_NOT_CONTEST_LEVEL",
        "pooled_scored_row_count": len(rows),
        "pooled_candidate_count": len({str(row["candidate_id"]) for row in rows}),
        "pooled_home_win_row_count": sum(int(row["home_win"]) for row in rows),
        "pooled_expected_home_wins": sum(
            float(row["frozen_probability_home_win"]) for row in rows
        ),
    }


def unique_contest_outcome_diagnostics(
    scored_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Contest-level outcomes counted once per contest, never once per candidate."""
    by_contest: dict[str, int] = {}
    for row in scored_rows:
        by_contest[str(row["ncaa_contest_id"])] = int(row["home_win"])
    return {
        "diagnostic_scope": "UNIQUE_CONTEST_OUTCOMES_COUNTED_ONCE_PER_CONTEST",
        "unique_scored_contest_count": len(by_contest),
        "contest_level_observed_home_wins": sum(by_contest.values()),
        "contest_level_observed_away_wins": len(by_contest) - sum(by_contest.values()),
        "home_win_by_contest": dict(sorted(by_contest.items())),
    }


def brier_contribution(probability: float, outcome: int) -> float:
    return (probability - outcome) ** 2


def log_loss_contribution(probability: float, outcome: int) -> float:
    bounded = _clip(probability)
    return -(outcome * math.log(bounded) + (1 - outcome) * math.log(1 - bounded))


def state_counts(rows: Iterable[Mapping[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field)) for row in rows).items()))
