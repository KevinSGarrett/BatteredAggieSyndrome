"""Prospective 2026 national shadow cohort and pregame snapshot eligibility.

The cohort is a census of official Division I football contests inside a declared
Week Zero and Week One window. It answers exactly one question per contest: may a
pregame snapshot still be frozen for it, and if not, why not.

Two properties matter more than coverage here. Outcome evidence is never read, so
the parser deliberately ignores score, linescore, period, clock, and attendance
cells even though the official page carries them. And an eligibility decision is
never made against an assumed kickoff instant: the published local clock is
converted with the earliest continental United States offset, which produces the
earliest possible coordinated universal time instant and therefore refuses more
games than a best-guess conversion would.
"""

from __future__ import annotations

import html
import json
import platform
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    manifest_authoritative_sha256,
    sha256_file,
    stable_hash,
)

SCHEMA_VERSION = "aggie.shadow.prospective_2026_cohort.v1"
CONTRACT_ID = "BAT-656-PROSPECTIVE-2026-NATIONAL-SHADOW-COHORT-V1"
CLASSIFICATION = "PROSPECTIVE_2026_NATIONAL_SHADOW_COHORT_AND_PREGAME_SNAPSHOT_ELIGIBILITY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PASS_RESULT = "PASS_PROSPECTIVE_2026_NATIONAL_SHADOW_COHORT"

CONTRACT_RELATIVE = "configs/prospective_2026_shadow_cohort_contract.json"
GATE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_cohort_gate.json"
EVIDENCE_RELATIVE = "artifacts/shadow/prospective_2026_shadow_cohort_replay.json"

COHORT_STATES = (
    "PRECOMMITTED",
    "SNAPSHOT_ELIGIBLE",
    "MISSED_CUTOFF_NO_BACKFILL",
    "UNSUPPORTED_ENTITY",
    "MISSING_REQUIRED_FEATURES_ABSTAIN",
    "FAIL_CLOSED_IDENTITY_MISMATCH",
)

# Substrings that would betray outcome evidence in an emitted field name or value.
# The official scoreboard renders all of these; none of them may survive into a
# cohort row. The published kickoff clock is deliberately not on this list: it is
# pregame scheduling evidence, not an outcome.
FORBIDDEN_OUTCOME_MARKERS = (
    "score",
    "totalcol",
    "down_and_distance",
    "ball_on",
    "attendance",
    "game_clock",
    "quarter",
)

NON_AUTHORITATIVE_MANIFEST_KEYS = frozenset({"issued_at_utc", "producer"})

_CARD_PATTERN = re.compile(r"(?is)<div class=\"card m-2\".*?</table>\s*</div>\s*</div>\s*</div>")
_CONTEST_ID_PATTERN = re.compile(r"id=\"contest_(\d+)\"")
_HEADER_PATTERN = re.compile(
    r"(?is)<div class=\"col-6 p-0\">\s*(\d{2}/\d{2}/\d{4})([^<]*)</div>"
)
_PARTICIPANT_PATTERN = re.compile(
    r"(?is)<a\b[^>]*href=\"/teams/(\d+)\"[^>]*>(.*?)</a>"
)
_NEUTRAL_SITE_PATTERN = re.compile(
    r"(?is)<td colspan=\"10\" valign=\"middle\">\s*@([^<]+?)\s*</td>"
)
_CLOCK_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.IGNORECASE)
_RECORD_SUFFIX_PATTERN = re.compile(r"\s*\((\d+)-(\d+)(?:-(\d+))?\)\s*$")


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone aware")
    return parsed.astimezone(timezone.utc)


def load_contract(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / CONTRACT_RELATIVE
    contract = json.loads(path.read_text(encoding="utf-8-sig"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("prospective 2026 shadow cohort contract identity mismatch")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("prospective 2026 shadow cohort contract schema mismatch")
    if contract.get("lane") != LANE:
        raise ValueError("prospective 2026 shadow cohort lane must remain observation only")
    for field, expected in (
        ("prospective_shadow_observation", True),
        ("historical_pit_admission", False),
        ("protected_training_admission", False),
        ("protected_evaluation_admission", False),
        ("model_selection_or_tuning", False),
        ("champion_or_production_promotion", False),
        ("forecast_publication", False),
        ("canonical_entity_mutation", False),
        ("immutable_raw_capture_mutation", False),
    ):
        if contract["authority"].get(field) is not expected:
            raise ValueError(f"contract authority field must remain {expected}: {field}")
    if contract["outcome_exclusion"].get("outcome_fields_extracted") is not False:
        raise ValueError("contract must forbid outcome field extraction")
    if contract["eligibility"].get("retroactive_forecast_permitted") is not False:
        raise ValueError("contract must forbid retroactive forecasts")
    if sorted(contract["states"]["progress_states"] + contract["states"]["terminal_or_side_states"]) != sorted(
        COHORT_STATES
    ):
        raise ValueError("contract state vocabulary does not match the implementation")
    return contract


# Token-level orthographic expansions of the abbreviation style the official
# scoreboard uses. Every entry is a spelling variant of the same word, so none of
# them can rename one program into another. Genuine initialisms are deliberately
# absent: expanding those would be a curated alias table rather than a fold, and
# the contract forbids promoting a name that the source did not actually spell.
ORTHOGRAPHIC_TOKEN_EXPANSIONS = {
    "ala": "alabama",
    "ariz": "arizona",
    "ark": "arkansas",
    "calif": "california",
    "caro": "carolina",
    "colo": "colorado",
    "conn": "connecticut",
    "fla": "florida",
    "ga": "georgia",
    "ill": "illinois",
    "ky": "kentucky",
    "md": "maryland",
    "mich": "michigan",
    "minn": "minnesota",
    "miss": "mississippi",
    "mo": "missouri",
    "mont": "montana",
    "neb": "nebraska",
    "nev": "nevada",
    "no": "northern",
    "okla": "oklahoma",
    "ore": "oregon",
    "so": "southern",
    "st": "state",
    "tenn": "tennessee",
    "tex": "texas",
    "univ": "university",
    "va": "virginia",
    "wash": "washington",
    "wis": "wisconsin",
    "wyo": "wyoming",
}

# A trailing generic institution word carries no distinguishing information and the
# two sources disagree about whether to print it.
TRAILING_GENERIC_TOKENS = ("university",)


def normalize_team_name(value: str) -> str:
    """Fold an official display name to a comparison key without fuzzy matching.

    Only deterministic orthographic folds are applied: case, accents, ampersand
    spelling, punctuation, whitespace, the declared abbreviation expansions, and a
    trailing generic institution word. Two programs whose names differ by anything
    more than spelling cannot collide here, and the population index additionally
    discards any key that resolves to more than one canonical team.
    """

    text = unicodedata.normalize("NFKD", html.unescape(str(value)))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.casefold().replace("&", " and ")
    tokens = [
        ORTHOGRAPHIC_TOKEN_EXPANSIONS.get(token, token)
        for token in re.sub(r"[^a-z0-9]+", " ", text).split()
    ]
    while len(tokens) > 1 and tokens[-1] in TRAILING_GENERIC_TOKENS:
        tokens.pop()
    return " ".join(tokens)


def strip_record_suffix(value: str) -> tuple[str, bool]:
    """Remove the win-loss record the scoreboard appends to a participant label.

    The record is outcome evidence for prior games, so it is discarded rather than
    stored. The boolean reports whether a suffix was present, which is schema
    evidence rather than an outcome.
    """

    label = re.sub(r"\s+", " ", html.unescape(str(value))).strip()
    stripped = _RECORD_SUFFIX_PATTERN.sub("", label).strip()
    return stripped, stripped != label


def parse_scoreboard_document(document: str, *, game_date: str) -> list[dict[str, Any]]:
    """Extract identity, published clock, site, and participants for one date.

    Cards whose contest identifiers disagree, whose participant count is not two,
    or whose header date contradicts the requested date are returned with an
    explicit parse state instead of being silently dropped.
    """

    expected_date = datetime.strptime(str(game_date), "%Y-%m-%d").date()
    records: list[dict[str, Any]] = []
    for card in _CARD_PATTERN.findall(str(document)):
        contest_ids = sorted(set(_CONTEST_ID_PATTERN.findall(card)))
        if len(contest_ids) != 1:
            records.append(
                {
                    "parse_state": "FAIL_CLOSED_IDENTITY_MISMATCH",
                    "parse_reason": "CARD_DOES_NOT_CARRY_EXACTLY_ONE_CONTEST_IDENTIFIER",
                    "observed_contest_ids": contest_ids,
                }
            )
            continue
        contest_id = contest_ids[0]
        header = _HEADER_PATTERN.search(card)
        if header is None:
            records.append(
                {
                    "parse_state": "FAIL_CLOSED_IDENTITY_MISMATCH",
                    "parse_reason": "CARD_HEADER_DATE_ABSENT",
                    "ncaa_contest_id": contest_id,
                }
            )
            continue
        header_date = datetime.strptime(header.group(1), "%m/%d/%Y").date()
        annotation = re.sub(r"\s+", " ", html.unescape(header.group(2))).strip()
        clock_text = ""
        broadcast_text = ""
        if annotation:
            clock_match = re.match(r"(?i)^(TBA|\d{1,2}:\d{2}\s*(?:AM|PM))\b(.*)$", annotation)
            if clock_match is None:
                broadcast_text = annotation
            else:
                clock_text = re.sub(r"\s+", " ", clock_match.group(1)).strip().upper()
                broadcast_text = clock_match.group(2).strip()
        participants: list[dict[str, Any]] = []
        for source_team_id, raw_label in _PARTICIPANT_PATTERN.findall(card):
            label, had_record = strip_record_suffix(raw_label)
            if not label:
                continue
            participants.append(
                {
                    "source_team_id": source_team_id,
                    "source_display_name": label,
                    "source_label_carried_prior_record": had_record,
                }
            )
        neutral_site = _NEUTRAL_SITE_PATTERN.search(card)
        record: dict[str, Any] = {
            "ncaa_contest_id": contest_id,
            "requested_game_date": expected_date.isoformat(),
            "source_published_game_date": header_date.isoformat(),
            "source_published_clock_text": clock_text,
            "source_published_broadcast_text": broadcast_text,
            "neutral_site_text": (
                re.sub(r"\s+", " ", html.unescape(neutral_site.group(1))).strip() if neutral_site else ""
            ),
            "participants": participants,
            "parse_state": "PARSED",
            "parse_reason": "",
        }
        if header_date != expected_date:
            record["parse_state"] = "FAIL_CLOSED_IDENTITY_MISMATCH"
            record["parse_reason"] = "CARD_HEADER_DATE_DOES_NOT_MATCH_REQUESTED_DATE"
        elif len(participants) != 2:
            record["parse_state"] = "FAIL_CLOSED_IDENTITY_MISMATCH"
            record["parse_reason"] = "CARD_DOES_NOT_CARRY_EXACTLY_TWO_PARTICIPANTS"
        elif participants[0]["source_team_id"] == participants[1]["source_team_id"]:
            record["parse_state"] = "FAIL_CLOSED_IDENTITY_MISMATCH"
            record["parse_reason"] = "CARD_PARTICIPANTS_ARE_NOT_DISTINCT"
        records.append(record)
    records.sort(key=lambda row: (str(row.get("ncaa_contest_id", "")), row.get("parse_reason", "")))
    return records


_ISO_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z?)?$")
_SCORE_SHAPE_PATTERN = re.compile(r"\b\d{1,3}\s*-\s*\d{1,3}\b")
_PARENTHESIZED_RECORD_PATTERN = re.compile(r"\(\s*\d+\s*-\s*\d+(?:\s*-\s*\d+)?\s*\)")


def assert_no_outcome_evidence(rows: Iterable[Mapping[str, Any]]) -> None:
    """Fail closed if any emitted key or value carries outcome evidence.

    Keys are checked against the forbidden marker list and values against a bare
    score shape and the parenthesized win-loss record the scoreboard appends to a
    participant label. Identifiers and timestamps are exempted from the score shape
    because an ISO date is not a score.
    """

    def visit(node: Any, path: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                lowered_key = str(key).casefold()
                for marker in FORBIDDEN_OUTCOME_MARKERS:
                    if marker in lowered_key:
                        raise ValueError(f"cohort rows carried a forbidden outcome key: {path}{key}")
                visit(value, f"{path}{key}.")
            return
        if isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                visit(value, f"{path}{index}.")
            return
        if isinstance(node, str):
            lowered = node.casefold()
            for marker in FORBIDDEN_OUTCOME_MARKERS:
                if marker in lowered:
                    raise ValueError(f"cohort rows carried a forbidden outcome value at {path}")
            if _PARENTHESIZED_RECORD_PATTERN.search(node):
                raise ValueError(f"cohort rows carried a win-loss record at {path}")
            if not _ISO_TIMESTAMP_PATTERN.match(node) and _SCORE_SHAPE_PATTERN.search(node):
                raise ValueError(f"cohort rows carried a score-shaped value at {path}")

    visit(list(rows), "")


def load_alias_population(path: Path, *, minimum_most_recent_season: int) -> dict[str, dict[str, Any]]:
    """Index the national spine alias payload by normalized display name.

    A normalized name that resolves to more than one canonical team is dropped
    rather than arbitrated, because arbitrating it would be exactly the fuzzy
    promotion the contract forbids.
    """

    by_name: dict[str, list[dict[str, Any]]] = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            seasons = [int(season) for season in row["observed_seasons"]]
            if not seasons or max(seasons) < int(minimum_most_recent_season):
                continue
            key = normalize_team_name(row["source_team_name"])
            if not key:
                continue
            by_name.setdefault(key, []).append(
                {
                    "canonical_team_id": str(row["canonical_team_id"]),
                    "spine_display_name": str(row["source_team_name"]),
                    "most_recent_observed_season": max(seasons),
                    "observed_season_count": len(seasons),
                }
            )
    return {
        key: candidates[0]
        for key, candidates in by_name.items()
        if len({candidate["canonical_team_id"] for candidate in candidates}) == 1
    }


def resolve_participant(
    participant: Mapping[str, Any], population: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    key = normalize_team_name(participant["source_display_name"])
    match = population.get(key)
    return {
        **dict(participant),
        "normalized_name_key": key,
        "canonical_team_id": match["canonical_team_id"] if match else None,
        "spine_display_name": match["spine_display_name"] if match else None,
        "most_recent_observed_season": match["most_recent_observed_season"] if match else None,
        "resolution_state": "EXACT_NORMALIZED_NAME_RESOLVED" if match else "UNRESOLVED_SOURCE_ENTITY",
    }


def kickoff_bound(
    *, game_date: str, clock_text: str, offset_seconds: int
) -> tuple[str | None, str]:
    """Convert a published local clock to its earliest possible UTC instant."""

    if not clock_text or clock_text.upper() == "TBA":
        return None, "KICKOFF_TIME_UNPUBLISHED"
    match = _CLOCK_PATTERN.match(clock_text.strip())
    if match is None:
        return None, "KICKOFF_TIME_UNRECOGNIZED"
    hour = int(match.group(1)) % 12
    if match.group(3).upper() == "PM":
        hour += 12
    local = datetime.strptime(game_date, "%Y-%m-%d").replace(
        hour=hour, minute=int(match.group(2)), tzinfo=timezone(timedelta(seconds=int(offset_seconds)))
    )
    return iso_utc(local), "KICKOFF_TIME_PUBLISHED"


def classify_game(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
    population: Mapping[str, Mapping[str, Any]],
    execution_time: datetime,
) -> dict[str, Any]:
    """Decide one contest's cohort state without ever consulting an outcome."""

    if record.get("parse_state") != "PARSED":
        return {
            **dict(record),
            "cohort_state": "FAIL_CLOSED_IDENTITY_MISMATCH",
            "state_reason": record.get("parse_reason", "PARSE_FAILED"),
            "participants": [dict(row) for row in record.get("participants", [])],
            "kickoff_utc_conservative_lower_bound": None,
            "kickoff_time_state": "KICKOFF_TIME_NOT_EVALUATED",
            "checkpoints": [],
            "snapshot_eligible": False,
        }
    offset = int(contract["kickoff_time_basis"]["declared_offset_seconds_for_window"])
    lower_bound, kickoff_state = kickoff_bound(
        game_date=record["source_published_game_date"],
        clock_text=record["source_published_clock_text"],
        offset_seconds=offset,
    )
    participants = [resolve_participant(row, population) for row in record["participants"]]
    away, home = participants[0], participants[1]
    neutral = bool(record["neutral_site_text"])
    checkpoints: list[dict[str, Any]] = []
    if lower_bound is not None:
        bound = parse_utc(lower_bound)
        for checkpoint in contract["eligibility"]["checkpoints"]:
            deadline = bound - timedelta(seconds=int(checkpoint["seconds_before_kickoff_lower_bound"]))
            checkpoints.append(
                {
                    "checkpoint_id": checkpoint["checkpoint_id"],
                    "deadline_utc": iso_utc(deadline),
                    "state": "OPEN" if execution_time <= deadline else "ELAPSED",
                }
            )
    unresolved = [row["source_display_name"] for row in participants if row["canonical_team_id"] is None]
    cutoff_id = contract["eligibility"]["snapshot_cutoff_checkpoint_id"]
    cutoff = next((row for row in checkpoints if row["checkpoint_id"] == cutoff_id), None)
    if unresolved:
        state, reason = "UNSUPPORTED_ENTITY", "PARTICIPANT_NOT_RESOLVED_IN_NATIONAL_SPINE_ALIAS_POPULATION"
    elif lower_bound is None:
        state, reason = "MISSING_REQUIRED_FEATURES_ABSTAIN", f"OFFICIAL_KICKOFF_TIME_{kickoff_state}"
    elif cutoff is None or cutoff["state"] == "ELAPSED":
        state, reason = "MISSED_CUTOFF_NO_BACKFILL", "EXECUTION_TIME_IS_AT_OR_PAST_THE_DECLARED_SNAPSHOT_CUTOFF"
    elif any(row["state"] == "ELAPSED" for row in checkpoints):
        state, reason = "SNAPSHOT_ELIGIBLE", "INSIDE_THE_FINAL_PREGAME_SNAPSHOT_WINDOW"
    else:
        state, reason = "PRECOMMITTED", "BEFORE_THE_FIRST_DECLARED_PREGAME_CHECKPOINT"
    return {
        "ncaa_contest_id": record["ncaa_contest_id"],
        "source_published_game_date": record["source_published_game_date"],
        "source_published_clock_text": record["source_published_clock_text"],
        "source_published_broadcast_text": record["source_published_broadcast_text"],
        "neutral_site_text": record["neutral_site_text"],
        "site_state": "NEUTRAL" if neutral else "HOME_TEAM_SITE",
        "away_team": away,
        "home_team": home,
        "participants": participants,
        "kickoff_time_state": kickoff_state,
        "kickoff_utc_conservative_lower_bound": lower_bound,
        "kickoff_utc_independently_confirmed": False,
        "checkpoints": checkpoints,
        "unresolved_participant_names": sorted(unresolved),
        "cohort_state": state,
        "state_reason": reason,
        "snapshot_eligible": state == "SNAPSHOT_ELIGIBLE",
        "outcome_fields_extracted": False,
        "parse_state": "PARSED",
        "parse_reason": "",
    }


def build_capture_inventory(captures: Sequence[Mapping[str, Any]], data_root: Path) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for capture in captures:
        path = Path(data_root) / capture["raw_relative_path"]
        inventory.append(
            {
                "game_date": capture["game_date"],
                "source_uri": capture["source_uri"],
                "request_identity_sha256": capture["request_identity_sha256"],
                "raw_relative_path": capture["raw_relative_path"],
                "raw_sha256": sha256_file(path),
                "raw_bytes": path.stat().st_size,
                "retrieved_at_utc": capture["retrieved_at_utc"],
                "route_id": capture["route_id"],
            }
        )
    inventory.sort(key=lambda row: row["game_date"])
    return inventory


def missingness_profile(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    fields = ("source_published_clock_text", "source_published_broadcast_text", "neutral_site_text")
    profile = {field: sum(1 for row in rows if not row.get(field)) for field in fields}
    profile["kickoff_utc_conservative_lower_bound"] = sum(
        1 for row in rows if row.get("kickoff_utc_conservative_lower_bound") is None
    )
    profile["unresolved_participant"] = sum(1 for row in rows if row.get("unresolved_participant_names"))
    return profile


def build_cohort(
    *,
    contract: Mapping[str, Any],
    captures: Sequence[Mapping[str, Any]],
    documents: Mapping[str, str],
    population: Mapping[str, Mapping[str, Any]],
    execution_time: datetime,
    data_root: Path,
) -> dict[str, Any]:
    declared_dates = list(contract["schedule_window"]["game_dates"])
    captured_dates = sorted({capture["game_date"] for capture in captures})
    if captured_dates != sorted(declared_dates):
        raise ValueError("captured schedule dates do not match the declared window")
    by_date = {capture["game_date"]: capture for capture in captures}
    rows: list[dict[str, Any]] = []
    date_observations: list[dict[str, Any]] = []
    for game_date in declared_dates:
        capture = by_date[game_date]
        admitted = bool(capture.get("cohort_rows_admitted", True))
        parsed = (
            parse_scoreboard_document(documents[game_date], game_date=game_date) if admitted else []
        )
        for record in parsed:
            rows.append(
                classify_game(
                    record, contract=contract, population=population, execution_time=execution_time
                )
            )
        date_observations.append(
            {
                "game_date": game_date,
                "date_observation_state": capture.get(
                    "date_observation_state", "OFFICIAL_CONTESTS_PRESENT"
                ),
                "source_echoed_game_date": capture.get("source_echoed_game_date", game_date),
                "cohort_rows_admitted": admitted,
                "official_contests_enumerated": len(parsed),
            }
        )
    duplicates = sorted(
        contest_id
        for contest_id, count in Counter(str(row.get("ncaa_contest_id")) for row in rows).items()
        if count > 1 and contest_id != "None"
    )
    if duplicates:
        raise ValueError(f"official contest identifiers repeated across the window: {duplicates}")
    rows.sort(key=lambda row: (row["source_published_game_date"], int(row["ncaa_contest_id"])))
    assert_no_outcome_evidence(rows)
    state_counts = dict(sorted(Counter(row["cohort_state"] for row in rows).items()))
    for state in COHORT_STATES:
        state_counts.setdefault(state, 0)
    eligible = [row for row in rows if row["snapshot_eligible"]]
    return {
        "rows": rows,
        "capture_inventory": build_capture_inventory(captures, data_root),
        "date_observations": date_observations,
        "state_counts": dict(sorted(state_counts.items())),
        "population_counts": {
            "declared_game_dates": len(declared_dates),
            "game_dates_carrying_official_contests": sum(
                1 for row in date_observations if row["official_contests_enumerated"]
            ),
            "game_dates_with_no_official_contest": sum(
                1
                for row in date_observations
                if row["date_observation_state"] == "NO_OFFICIAL_CONTESTS_ON_THIS_DATE"
            ),
            "game_dates_the_source_substituted": sum(
                1
                for row in date_observations
                if row["date_observation_state"] == "SOURCE_SUBSTITUTED_A_DIFFERENT_DATE"
            ),
            "official_contests_enumerated": len(rows),
            "snapshot_eligible_contests": len(eligible),
            "distinct_resolved_canonical_teams": len(
                {
                    participant["canonical_team_id"]
                    for row in rows
                    for participant in row["participants"]
                    if participant.get("canonical_team_id")
                }
            ),
            "spine_alias_population_size": len(population),
        },
        "missingness": missingness_profile(rows),
        "eligible_contest_ids": sorted((row["ncaa_contest_id"] for row in eligible), key=int),
        "execution_time_utc": iso_utc(execution_time),
    }


def build_gate(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    cohort: Mapping[str, Any],
    manifest_relative_path: str,
    manifest_sha256: str,
    dataset_identity: str,
    spine_gate_sha256: str,
    matrix_gate_sha256: str,
    baseline_gate_sha256: str,
) -> dict[str, Any]:
    rows = cohort["rows"]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "PROSPECTIVE_2026_NATIONAL_SHADOW_COHORT_GATE",
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "local_issue_id": contract["local_issue_id"],
        "jira_key": contract["jira_key"],
        "parent_jira_key": contract["parent_jira_key"],
        "classification": CLASSIFICATION,
        "protected_lane": PROTECTED_LANE,
        "lane": LANE,
        "result": PASS_RESULT,
        "contract_sha256": contract_sha256,
        "bound_predecessors": {
            "national_tiered_game_spine_gate_sha256": spine_gate_sha256,
            "national_chronological_development_matrix_gate_sha256": matrix_gate_sha256,
            "national_expectation_baselines_gate_sha256": baseline_gate_sha256,
        },
        "manifest": {
            "relative_path": manifest_relative_path,
            "sha256": manifest_sha256,
            "dataset_identity": dataset_identity,
            "bulk_payloads_in_git": False,
        },
        "schedule_window": dict(contract["schedule_window"]),
        "kickoff_time_basis": dict(contract["kickoff_time_basis"]),
        "population_counts": dict(cohort["population_counts"]),
        "state_counts": dict(cohort["state_counts"]),
        "missingness": dict(cohort["missingness"]),
        "eligible_contest_ids": list(cohort["eligible_contest_ids"]),
        "capture_inventory": list(cohort["capture_inventory"]),
        "date_observations": list(cohort["date_observations"]),
        "execution_time_utc": cohort["execution_time_utc"],
        "outcome_exclusion": {
            "outcome_fields_extracted": False,
            "prior_record_suffix_discarded": True,
            "forbidden_outcome_markers_absent": True,
            "outcome_accessible_before_forecast_freeze": False,
        },
        "eligibility_gate": {
            "retroactive_pregame_snapshot_created": False,
            "retroactive_forecast_created": False,
            "backfilled_after_cutoff": False,
            "games_already_started_forecast": False,
            "snapshot_cutoff_checkpoint_id": contract["eligibility"]["snapshot_cutoff_checkpoint_id"],
            "checkpoint_ids": [row["checkpoint_id"] for row in contract["eligibility"]["checkpoints"]],
        },
        "authority": dict(contract["authority"]),
        "negative_findings": {
            **dict(contract["negative_findings"]),
            "cohort_is_a_census_not_a_forecast": True,
            "official_source_substituted_some_requested_dates": bool(
                cohort["population_counts"]["game_dates_the_source_substituted"]
            ),
            "substituted_dates_contribute_no_rows_rather_than_another_dates_games": True,
            "unsupported_or_unpublished_games_remain_explicit": bool(
                cohort["state_counts"]["UNSUPPORTED_ENTITY"]
                or cohort["state_counts"]["MISSING_REQUIRED_FEATURES_ABSTAIN"]
            ),
            "no_eligible_game_is_not_a_failure": not cohort["eligible_contest_ids"],
        },
        "scientific_nonclaims": {
            "gap_002_resolved": False,
            "protected_evaluation_opened": False,
            "production_champion_declared": False,
            "tamu_specialization_lift_claimed": False,
            "bas_or_aggie_excess_claimed": False,
            "forecast_published": False,
            "entity_resolution_benchmark_claimed": False,
        },
        "row_count": len(rows),
    }


def dataset_manifest(
    *,
    contract: Mapping[str, Any],
    cohort: Mapping[str, Any],
    payload_relative_path: str,
    payload_sha256: str,
    payload_bytes: int,
    payload_rows: int,
) -> dict[str, Any]:
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "PROSPECTIVE_2026_NATIONAL_SHADOW_COHORT_MANIFEST",
        "contract_id": CONTRACT_ID,
        "decision_unit": contract["decision_unit"],
        "jira_key": contract["jira_key"],
        "classification": CLASSIFICATION,
        "lane": LANE,
        "schedule_window": dict(contract["schedule_window"]),
        "population_counts": dict(cohort["population_counts"]),
        "state_counts": dict(cohort["state_counts"]),
        "missingness": dict(cohort["missingness"]),
        "capture_inventory": list(cohort["capture_inventory"]),
        "date_observations": list(cohort["date_observations"]),
        "execution_time_utc": cohort["execution_time_utc"],
        "payloads": [
            {
                "name": "prospective_2026_shadow_cohort.jsonl",
                "relative_path": payload_relative_path,
                "role": "PROSPECTIVE_2026_SHADOW_COHORT_ROWS",
                "rows": payload_rows,
                "bytes": payload_bytes,
                "sha256": payload_sha256,
            }
        ],
        "authority": dict(contract["authority"]),
    }
    return {**core, "dataset_identity": stable_hash(core)}


def validate_artifact(repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Independently revalidate the published gate against external evidence."""

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    load_contract(repo_root)
    gate_path = repo_root / GATE_RELATIVE
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))
    findings: list[str] = []
    if gate.get("result") != PASS_RESULT:
        findings.append("gate result is not the declared pass result")
    if gate.get("contract_id") != CONTRACT_ID or gate.get("lane") != LANE:
        findings.append("gate contract identity or lane mismatch")
    if gate.get("contract_sha256") != sha256_file(repo_root / CONTRACT_RELATIVE):
        findings.append("contract hash drifted from the published gate")
    if binding_identity(gate, "gate_identity") != gate.get("gate_identity"):
        findings.append("gate identity does not recompute")
    manifest_path = data_root / gate["manifest"]["relative_path"]
    if not manifest_path.is_file():
        findings.append("dataset manifest is absent from the external data root")
        return {"result": "FAIL", "findings": findings}
    if sha256_file(manifest_path) != gate["manifest"]["sha256"]:
        findings.append("dataset manifest hash drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("dataset_identity") != gate["manifest"]["dataset_identity"]:
        findings.append("dataset identity disagrees with the gate binding")
    if manifest_authoritative_sha256(manifest) != stable_hash(
        {key: value for key, value in manifest.items() if key not in NON_AUTHORITATIVE_MANIFEST_KEYS}
    ):
        findings.append("manifest authoritative hash is not reproducible")
    for payload in manifest["payloads"]:
        payload_path = data_root / payload["relative_path"]
        if not payload_path.is_file():
            findings.append(f"payload absent: {payload['name']}")
            continue
        if sha256_file(payload_path) != payload["sha256"]:
            findings.append(f"payload hash drifted: {payload['name']}")
            continue
        rows = [json.loads(line) for line in payload_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(rows) != int(payload["rows"]):
            findings.append(f"payload row count drifted: {payload['name']}")
        assert_no_outcome_evidence(rows)
        observed = dict(sorted(Counter(row["cohort_state"] for row in rows).items()))
        expected = {key: value for key, value in gate["state_counts"].items() if value}
        if observed != expected:
            findings.append("payload state counts disagree with the gate")
        if sorted((row["ncaa_contest_id"] for row in rows if row["snapshot_eligible"]), key=int) != list(
            gate["eligible_contest_ids"]
        ):
            findings.append("payload eligible contests disagree with the gate")
    for capture in gate["capture_inventory"]:
        capture_path = data_root / capture["raw_relative_path"]
        if not capture_path.is_file():
            findings.append(f"immutable capture absent: {capture['game_date']}")
        elif sha256_file(capture_path) != capture["raw_sha256"]:
            findings.append(f"immutable capture hash drifted: {capture['game_date']}")
    if gate["authority"].get("protected_evaluation_admission") is not False:
        findings.append("gate opened protected evaluation")
    if gate["outcome_exclusion"].get("outcome_fields_extracted") is not False:
        findings.append("gate claimed outcome extraction")
    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "gate_identity": gate.get("gate_identity"),
        "row_count": gate.get("row_count"),
        "state_counts": gate.get("state_counts"),
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
    }
