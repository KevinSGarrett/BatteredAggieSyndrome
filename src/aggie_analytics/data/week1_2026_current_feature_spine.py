"""Timestamped national Week 1 2026 current-feature spine on the team-game grain.

Every contest the official Week 1 universe published contributes exactly two
oriented rows, and every row carries one cell per declared feature domain. A cell
is admitted only when its own evidence proves the value was knowable before the
target kickoff and no later than the snapshot issuance; otherwise the cell holds a
null value and an explicit reason. Nothing here defaults a missing value, promotes
a roster membership into an availability claim, or lets a contest's own outcome or
a later contest's outcome reach its features.
"""

from __future__ import annotations

import json
import platform
import re
import sys
from collections import Counter
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any, Mapping, Sequence

from aggie_analytics.data.national_foundation_reconciliation import (
    binding_identity,
    sha256_file,
    stable_hash,
)
from aggie_analytics.data.prospective_shadow_cohort import iso_utc, parse_utc

SCHEMA_VERSION = "aggie.shadow.week1_2026_current_feature_spine.v1"
CONTRACT_ID = "BAT-677-WEEK1-2026-CURRENT-FEATURE-SPINE-V1"
JIRA_KEY = "BAT-677"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-2026-WEEK1-CURRENT-FEATURE-SPINE-001"
CLASSIFICATION = "WEEK1_2026_NATIONAL_CURRENT_FEATURE_SPINE_AND_TEMPORAL_ADMISSION"
LANE = "PROSPECTIVE_SHADOW_OBSERVATION_ONLY"
PROTECTED_LANE = "RETAIN_PROTECTED_LANE_BLOCKED"
PASS_RESULT = "PASS_WEEK1_2026_CURRENT_FEATURE_SPINE"

CONTRACT_RELATIVE = "configs/week1_2026_current_feature_spine_contract.json"
GATE_RELATIVE = "artifacts/spine/week1_2026_current_feature_spine_gate.json"

ROW_PAYLOAD_NAME = "week1_2026_feature_spine_rows.jsonl"
CELL_PAYLOAD_NAME = "week1_2026_temporal_admission_cells.jsonl"
PAYLOAD_SLUG = "week1_2026_current_feature_spine"

TEAM_STRENGTH_PRIOR = "TEAM_STRENGTH_PRIOR"
WEEK_ZERO_CURRENT_RESULT = "WEEK_ZERO_CURRENT_RESULT"
CURRENT_RANKING = "CURRENT_RANKING"
CONFERENCE_AND_SUBDIVISION = "CONFERENCE_AND_SUBDIVISION"
VENUE_AND_SITE = "VENUE_AND_SITE"
WEATHER_VINTAGE = "WEATHER_VINTAGE"
ROSTER_MEMBERSHIP = "ROSTER_MEMBERSHIP"
PREGAME_AVAILABILITY = "PREGAME_AVAILABILITY"

FEATURE_DOMAINS = (
    TEAM_STRENGTH_PRIOR,
    WEEK_ZERO_CURRENT_RESULT,
    CURRENT_RANKING,
    CONFERENCE_AND_SUBDIVISION,
    VENUE_AND_SITE,
    WEATHER_VINTAGE,
    ROSTER_MEMBERSHIP,
    PREGAME_AVAILABILITY,
)

ADMITTED_PROSPECTIVE_PREKICKOFF = "ADMITTED_PROSPECTIVE_PREKICKOFF"
CANDIDATE_ONLY_NOT_CONSUMED = "CANDIDATE_ONLY_NOT_CONSUMED"
TEMPORALLY_INELIGIBLE = "TEMPORALLY_INELIGIBLE"
SOURCE_EVIDENCE_ABSENT = "SOURCE_EVIDENCE_ABSENT"
UNRESOLVED_ENTITY = "UNRESOLVED_ENTITY"
QUARANTINED_CONFLICT = "QUARANTINED_CONFLICT"
NOT_APPLICABLE = "NOT_APPLICABLE"

ADMISSION_DISPOSITIONS = (
    ADMITTED_PROSPECTIVE_PREKICKOFF,
    CANDIDATE_ONLY_NOT_CONSUMED,
    TEMPORALLY_INELIGIBLE,
    SOURCE_EVIDENCE_ABSENT,
    UNRESOLVED_ENTITY,
    QUARANTINED_CONFLICT,
    NOT_APPLICABLE,
)

SPINE_ROW_ADMITTED = "SPINE_ROW_ADMITTED"
SPINE_ROW_UNSUPPORTED_ENTITY = "SPINE_ROW_UNSUPPORTED_ENTITY"

UNRANKED_SENTINEL_FORBIDDEN = 26

_RANK_ROW = re.compile(
    r"<tr>\s*<td>\s*(?P<tie>T?)(?P<rank>\d+)\s*</td>\s*<td>\s*(?P<team>[^<]+?)\s*</td>",
    re.IGNORECASE,
)
_VOTES_SUFFIX = re.compile(r"\s*\(\d+\)\s*$")
_PUBLICATION_AUTHORITY = re.compile(
    r'rankings-last-updated"[^>]*>\s*(?P<text>[^<]+?)\s*</figure>', re.IGNORECASE
)


class Week1FeatureSpineViolation(RuntimeError):
    """Raised when Week 1 feature evidence fails a declared admission rule."""


def load_contract(repo_root: Path) -> dict[str, Any]:
    return validate_contract(
        json.loads((Path(repo_root) / CONTRACT_RELATIVE).read_text(encoding="utf-8-sig"))
    )


def validate_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse a contract that relaxes a temporal, missingness, or lane protection."""

    if contract.get("contract_id") != CONTRACT_ID:
        raise Week1FeatureSpineViolation("contract identity mismatch")
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise Week1FeatureSpineViolation("contract schema mismatch")
    if contract.get("lane") != LANE:
        raise Week1FeatureSpineViolation("contract lane must remain observation only")
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
            raise Week1FeatureSpineViolation(
                f"contract authority field must remain {expected}: {field}"
            )
    temporal = contract["temporal_rules"]
    for field in (
        "source_known_at_must_not_exceed_snapshot_issuance",
        "snapshot_issuance_must_precede_target_kickoff_bound",
        "same_game_target_exclusion",
        "future_append_invariance_required",
    ):
        if temporal.get(field) is not True:
            raise Week1FeatureSpineViolation(f"contract must keep temporal rule enabled: {field}")
    for field in (
        "future_game_result_in_an_earlier_target",
        "capture_time_promoted_into_historical_known_at",
    ):
        if temporal.get(field) is not False:
            raise Week1FeatureSpineViolation(f"contract must keep temporal rule refused: {field}")
    if contract["missingness"].get("fabricated_default_permitted") is not False:
        raise Week1FeatureSpineViolation("contract must forbid fabricated defaults")
    if contract["missingness"].get("unranked_is_not_a_numeric_rank") is not True:
        raise Week1FeatureSpineViolation("contract must keep unranked non-numeric")
    rankings = contract["sources"]["current_rankings"]
    if int(rankings.get("unranked_sentinel_forbidden")) != UNRANKED_SENTINEL_FORBIDDEN:
        raise Week1FeatureSpineViolation("contract must forbid the unranked numeric sentinel")
    if contract["sources"]["weather_vintage"].get("observed_postgame_weather_permitted") is not False:
        raise Week1FeatureSpineViolation("contract must forbid observed postgame weather")
    if contract["sources"]["roster_membership"].get("membership_is_availability") is not False:
        raise Week1FeatureSpineViolation("contract must keep membership distinct from availability")
    availability = contract["sources"]["pregame_availability"]
    for field in ("membership_as_availability", "participation_as_availability"):
        if availability.get(field) is not False:
            raise Week1FeatureSpineViolation(f"contract must refuse availability promotion: {field}")
    if contract["sources"]["frozen_prior_domain"].get("retraining_permitted") is not False:
        raise Week1FeatureSpineViolation("contract must forbid retraining a frozen prior")
    if contract["tamu_policy"].get("tamu_specific_adjustment_applied") is not False:
        raise Week1FeatureSpineViolation("contract must forbid a Texas A&M specific adjustment")
    if tuple(contract["feature_domains"]) != FEATURE_DOMAINS:
        raise Week1FeatureSpineViolation("contract feature domain vocabulary mismatch")
    if tuple(contract["admission_dispositions"]) != ADMISSION_DISPOSITIONS:
        raise Week1FeatureSpineViolation("contract admission vocabulary mismatch")
    return dict(contract)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_ranking_document(document: str) -> dict[str, Any]:
    """Read the official poll table without inventing a rank for an absent school."""

    authority = _PUBLICATION_AUTHORITY.search(document)
    entries: list[dict[str, Any]] = []
    for match in _RANK_ROW.finditer(document):
        display = unescape(match.group("team")).strip()
        entries.append(
            {
                "rank": int(match.group("rank")),
                "rank_is_tied": bool(match.group("tie")),
                "poll_display_name": _VOTES_SUFFIX.sub("", display),
                "poll_display_name_raw": display,
            }
        )
    ranks = [entry["rank"] for entry in entries]
    if ranks != sorted(ranks):
        raise Week1FeatureSpineViolation("official poll table carried a non-monotone rank sequence")
    for rank, count in Counter(ranks).items():
        if count > 1 and not all(
            entry["rank_is_tied"] for entry in entries if entry["rank"] == rank
        ):
            raise Week1FeatureSpineViolation(
                "official poll table repeated a rank the source did not mark as tied"
            )
    if any(entry["rank"] < 1 for entry in entries):
        raise Week1FeatureSpineViolation("official poll table carried a non-positive rank")
    return {
        "publication_authority_text": (
            authority.group("text").strip() if authority else None
        ),
        "entries": entries,
    }


def index_rankings(
    entries: Sequence[Mapping[str, Any]],
    participants: Sequence[Mapping[str, Any]],
    aliases: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, Any]:
    """Bind poll entries to Week 1 participants by exact official publisher name.

    The join never resolves an entity: it attaches a poll attribute to a
    participant whose canonical identity was already established elsewhere. A poll
    name that matches more than one distinct source team is quarantined instead of
    arbitrated, and a poll name that matches none is preserved as evidence. When any
    poll entry stays unbound the poll's coverage is incomplete, and no participant
    may then be described as unranked, because the unbound entry could be that team.
    """

    alias_index = dict(aliases or {})
    by_name: dict[str, set[str]] = {}
    for participant in participants:
        names = list(participant["source_display_names"]) + list(
            alias_index.get(participant["source_team_id"], ())
        )
        for name in names:
            if name:
                by_name.setdefault(str(name), set()).add(participant["source_team_id"])

    bound: dict[str, dict[str, Any]] = {}
    unmatched: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for entry in entries:
        candidates = sorted(by_name.get(entry["poll_display_name"], ()))
        if not candidates:
            unmatched.append(dict(entry))
            continue
        if len(candidates) > 1:
            conflicts.append({**dict(entry), "source_team_ids": candidates})
            continue
        bound[candidates[0]] = {**dict(entry), "source_team_id": candidates[0]}
    return {
        "by_source_team_id": bound,
        "unmatched_poll_entries": unmatched,
        "conflicting_poll_entries": conflicts,
        "poll_coverage_complete": not unmatched and not conflicts,
    }


def index_week_zero_finals(proofs: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Index proven Week Zero finals by canonical team with their capture times."""

    indexed: dict[str, list[dict[str, Any]]] = {}
    for proof in proofs:
        if proof.get("proof_state") != "ORIENTATION_PROVEN":
            continue
        for orientation in ("away", "home"):
            team = proof.get(f"{orientation}_canonical_team_id")
            if not team:
                continue
            opponent = proof.get("home_canonical_team_id" if orientation == "away" else "away_canonical_team_id")
            points = int(proof[f"{orientation}_points"])
            opponent_points = int(
                proof["home_points" if orientation == "away" else "away_points"]
            )
            indexed.setdefault(team, []).append(
                {
                    "ncaa_contest_id": str(proof["ncaa_contest_id"]),
                    "orientation": orientation.upper(),
                    "points_for": points,
                    "points_against": opponent_points,
                    "won": int(points > opponent_points),
                    "opponent_canonical_team_id": opponent,
                    "kickoff_bound_utc": str(proof["kickoff_bound_utc"]),
                    "final_capture_retrieved_at_utc": str(proof["final_capture_retrieved_at_utc"]),
                    "official_capture_identity": str(proof["official_capture_identity"]),
                    "official_raw_response_sha256": str(proof["official_raw_response_sha256"]),
                    "contest_orientation_identity": str(proof["contest_orientation_identity"]),
                }
            )
    for records in indexed.values():
        records.sort(key=lambda record: record["ncaa_contest_id"])
    return indexed


def index_weather_vintages(captures: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(capture["canonical_team_id"]): dict(capture)
        for capture in captures
        if capture.get("state") == "CAPTURED"
    }


def select_forecast_period(
    periods: Sequence[Mapping[str, Any]], kickoff_bound_utc: str
) -> dict[str, Any] | None:
    """Return the hourly period whose valid interval contains the kickoff bound."""

    target = parse_utc(kickoff_bound_utc)
    for period in periods:
        start = parse_utc(str(period["startTime"]))
        end = parse_utc(str(period["endTime"]))
        if start <= target < end:
            return dict(period)
    return None


def _cell(
    *,
    domain: str,
    value: Any,
    source_id: str | None,
    source_observation_identity: str | None,
    raw_capture_sha256: str | None,
    observed_at_utc: str | None,
    published_at_utc: str | None,
    snapshot_issuance_utc: str,
    target_kickoff_bound_utc: str | None,
    known_at_classification: str,
    admission_disposition: str,
    missingness_reason: str | None,
    conflict_state: str,
) -> dict[str, Any]:
    if admission_disposition not in ADMISSION_DISPOSITIONS:
        raise Week1FeatureSpineViolation(f"undeclared admission disposition: {admission_disposition}")
    if value is None and admission_disposition == ADMITTED_PROSPECTIVE_PREKICKOFF:
        raise Week1FeatureSpineViolation(f"domain {domain} admitted an absent value")
    if value is not None and missingness_reason is not None:
        raise Week1FeatureSpineViolation(f"domain {domain} carried a value and a missingness reason")
    if admission_disposition == ADMITTED_PROSPECTIVE_PREKICKOFF:
        if observed_at_utc is None or target_kickoff_bound_utc is None:
            raise Week1FeatureSpineViolation(f"domain {domain} admitted a value without timing proof")
        if parse_utc(observed_at_utc) > parse_utc(snapshot_issuance_utc):
            raise Week1FeatureSpineViolation(
                f"domain {domain} known-at time exceeds the snapshot issuance"
            )
        if parse_utc(snapshot_issuance_utc) >= parse_utc(target_kickoff_bound_utc):
            raise Week1FeatureSpineViolation(
                f"domain {domain} snapshot issuance is not before the target kickoff bound"
            )
    return {
        "domain": domain,
        "value": value,
        "source_id": source_id,
        "source_observation_identity": source_observation_identity,
        "raw_capture_sha256": raw_capture_sha256,
        "observed_at_utc": observed_at_utc,
        "published_at_utc": published_at_utc,
        "snapshot_issuance_utc": snapshot_issuance_utc,
        "target_kickoff_bound_utc": target_kickoff_bound_utc,
        "known_at_classification": known_at_classification,
        "admission_disposition": admission_disposition,
        "missingness_reason": missingness_reason,
        "conflict_state": conflict_state,
    }


def _prior_cell(
    *,
    prior_evidence: Mapping[str, Any],
    snapshot: str,
    kickoff: str | None,
) -> dict[str, Any]:
    return _cell(
        domain=TEAM_STRENGTH_PRIOR,
        value=None,
        source_id="BAT-655-NATIONAL-EXPECTATION-BASELINES-AND-PEERS-V1",
        source_observation_identity=str(prior_evidence["candidate_gate_identity"]),
        raw_capture_sha256=None,
        observed_at_utc=None,
        published_at_utc=None,
        snapshot_issuance_utc=snapshot,
        target_kickoff_bound_utc=kickoff,
        known_at_classification="NO_PRIOR_STRENGTH_VALUE_IS_KNOWABLE_FOR_THIS_TEAM_BEFORE_KICKOFF",
        admission_disposition=SOURCE_EVIDENCE_ABSENT,
        missingness_reason=str(prior_evidence["absence_reason"]),
        conflict_state="NONE",
    )


def _week_zero_cell(
    *,
    records: Sequence[Mapping[str, Any]],
    snapshot: str,
    kickoff: str | None,
    target_contest_id: str,
) -> dict[str, Any]:
    admissible: list[dict[str, Any]] = []
    ineligible: list[str] = []
    for record in records:
        if record["ncaa_contest_id"] == target_contest_id:
            raise Week1FeatureSpineViolation(
                "a target contest cannot supply its own completed result"
            )
        capture = parse_utc(record["final_capture_retrieved_at_utc"])
        if capture > parse_utc(snapshot):
            ineligible.append(record["ncaa_contest_id"])
            continue
        if kickoff is None or capture >= parse_utc(kickoff):
            ineligible.append(record["ncaa_contest_id"])
            continue
        admissible.append(dict(record))
    if not admissible:
        return _cell(
            domain=WEEK_ZERO_CURRENT_RESULT,
            value=None,
            source_id="BAT-674-WEEK-ZERO-OFFICIAL-FINAL-SCORING",
            source_observation_identity=None,
            raw_capture_sha256=None,
            observed_at_utc=None,
            published_at_utc=None,
            snapshot_issuance_utc=snapshot,
            target_kickoff_bound_utc=kickoff,
            known_at_classification=(
                "NO_OFFICIAL_FINAL_FOR_THIS_TEAM_WAS_CAPTURED_BEFORE_THE_SNAPSHOT"
            ),
            admission_disposition=(
                TEMPORALLY_INELIGIBLE if ineligible else SOURCE_EVIDENCE_ABSENT
            ),
            missingness_reason=(
                "AN_OFFICIAL_FINAL_EXISTS_BUT_ITS_CAPTURE_IS_NOT_EARLIER_THAN_THE_TARGET_BOUND"
                if ineligible
                else "THIS_TEAM_DID_NOT_PLAY_A_CAPTURED_WEEK_ZERO_CONTEST"
            ),
            conflict_state="NONE",
        )
    latest = max(admissible, key=lambda record: parse_utc(record["final_capture_retrieved_at_utc"]))
    value = {
        "completed_contest_count": len(admissible),
        "wins": sum(record["won"] for record in admissible),
        "losses": sum(1 - record["won"] for record in admissible),
        "points_for": sum(record["points_for"] for record in admissible),
        "points_against": sum(record["points_against"] for record in admissible),
        "contest_ids": [record["ncaa_contest_id"] for record in admissible],
        "contest_orientation_identities": [
            record["contest_orientation_identity"] for record in admissible
        ],
    }
    return _cell(
        domain=WEEK_ZERO_CURRENT_RESULT,
        value=value,
        source_id="BAT-674-WEEK-ZERO-OFFICIAL-FINAL-SCORING",
        source_observation_identity=str(latest["official_capture_identity"]),
        raw_capture_sha256=str(latest["official_raw_response_sha256"]),
        observed_at_utc=str(latest["final_capture_retrieved_at_utc"]),
        published_at_utc=None,
        snapshot_issuance_utc=snapshot,
        target_kickoff_bound_utc=kickoff,
        known_at_classification="KNOWN_AT_THE_OFFICIAL_FINAL_CAPTURE_OF_THE_COMPLETED_CONTEST",
        admission_disposition=ADMITTED_PROSPECTIVE_PREKICKOFF,
        missingness_reason=None,
        conflict_state="NONE",
    )


def _ranking_cell(
    *,
    ranking: Mapping[str, Any] | None,
    ranking_capture: Mapping[str, Any],
    publication_authority_text: str | None,
    conflicted: bool,
    poll_coverage_complete: bool,
    snapshot: str,
    kickoff: str | None,
) -> dict[str, Any]:
    if conflicted:
        return _cell(
            domain=CURRENT_RANKING,
            value=None,
            source_id=str(ranking_capture["poll_id"]),
            source_observation_identity=str(ranking_capture["capture_identity"]),
            raw_capture_sha256=str(ranking_capture["raw_sha256"]),
            observed_at_utc=str(ranking_capture["retrieved_at_utc"]),
            published_at_utc=publication_authority_text,
            snapshot_issuance_utc=snapshot,
            target_kickoff_bound_utc=kickoff,
            known_at_classification="POLL_NAME_MATCHED_MORE_THAN_ONE_SOURCE_TEAM",
            admission_disposition=QUARANTINED_CONFLICT,
            missingness_reason="THE_POLL_LABEL_DOES_NOT_IDENTIFY_A_SINGLE_PARTICIPANT",
            conflict_state="POLL_LABEL_AMBIGUOUS",
        )
    if ranking is None and not poll_coverage_complete:
        return _cell(
            domain=CURRENT_RANKING,
            value=None,
            source_id=str(ranking_capture["poll_id"]),
            source_observation_identity=str(ranking_capture["capture_identity"]),
            raw_capture_sha256=str(ranking_capture["raw_sha256"]),
            observed_at_utc=str(ranking_capture["retrieved_at_utc"]),
            published_at_utc=publication_authority_text,
            snapshot_issuance_utc=snapshot,
            target_kickoff_bound_utc=kickoff,
            known_at_classification="POLL_LABEL_COVERAGE_IS_INCOMPLETE_FOR_THIS_POPULATION",
            admission_disposition=SOURCE_EVIDENCE_ABSENT,
            missingness_reason=(
                "AT_LEAST_ONE_POLL_ENTRY_DID_NOT_BIND_SO_UNRANKED_CANNOT_BE_ASSERTED_HERE"
            ),
            conflict_state="NONE",
        )
    value = {
        "is_ranked": ranking is not None,
        "poll_rank": int(ranking["rank"]) if ranking else None,
        "poll_rank_is_tied": bool(ranking["rank_is_tied"]) if ranking else False,
        "poll_display_name": ranking["poll_display_name"] if ranking else None,
        "unranked_indicator": ranking is None,
        "unranked_numeric_sentinel_used": False,
    }
    if value["poll_rank"] is not None and int(value["poll_rank"]) >= UNRANKED_SENTINEL_FORBIDDEN:
        raise Week1FeatureSpineViolation("a poll rank reached the forbidden unranked sentinel")
    return _cell(
        domain=CURRENT_RANKING,
        value=value,
        source_id=str(ranking_capture["poll_id"]),
        source_observation_identity=str(ranking_capture["capture_identity"]),
        raw_capture_sha256=str(ranking_capture["raw_sha256"]),
        observed_at_utc=str(ranking_capture["retrieved_at_utc"]),
        published_at_utc=publication_authority_text,
        snapshot_issuance_utc=snapshot,
        target_kickoff_bound_utc=kickoff,
        known_at_classification=(
            "KNOWN_BY_THIS_CAPTURE_THE_ORIGINAL_PUBLICATION_INSTANT_IS_NOT_INDEPENDENTLY_AVAILABLE"
        ),
        admission_disposition=CANDIDATE_ONLY_NOT_CONSUMED,
        missingness_reason=None,
        conflict_state="NONE",
    )


def _weather_cell(
    *,
    vintage: Mapping[str, Any] | None,
    period: Mapping[str, Any] | None,
    snapshot: str,
    kickoff: str | None,
    coordinate_authority: str,
) -> dict[str, Any]:
    if vintage is None or kickoff is None:
        return _cell(
            domain=WEATHER_VINTAGE,
            value=None,
            source_id="SRC-NWS-OFFICIAL-API",
            source_observation_identity=None,
            raw_capture_sha256=None,
            observed_at_utc=None,
            published_at_utc=None,
            snapshot_issuance_utc=snapshot,
            target_kickoff_bound_utc=kickoff,
            known_at_classification="NO_FORECAST_GRID_RESOLVED_FOR_THIS_SITE",
            admission_disposition=SOURCE_EVIDENCE_ABSENT,
            missingness_reason="THE_SITE_COORDINATE_OR_FORECAST_GRID_DID_NOT_RESOLVE",
            conflict_state="NONE",
        )
    if period is None:
        return _cell(
            domain=WEATHER_VINTAGE,
            value=None,
            source_id="SRC-NWS-OFFICIAL-API",
            source_observation_identity=str(vintage["forecast_raw_sha256"]),
            raw_capture_sha256=str(vintage["forecast_raw_sha256"]),
            observed_at_utc=None,
            published_at_utc=str(vintage["forecast_update_time_utc"]),
            snapshot_issuance_utc=snapshot,
            target_kickoff_bound_utc=kickoff,
            known_at_classification="NO_FORECAST_PERIOD_COVERS_THE_TARGET_KICKOFF_BOUND",
            admission_disposition=SOURCE_EVIDENCE_ABSENT,
            missingness_reason="THE_FORECAST_VALID_INTERVAL_DOES_NOT_REACH_THE_TARGET_KICKOFF",
            conflict_state="NONE",
        )
    value = {
        "period_start_utc": iso_utc(parse_utc(str(period["startTime"]))),
        "period_end_utc": iso_utc(parse_utc(str(period["endTime"]))),
        "temperature": period.get("temperature"),
        "temperature_unit": period.get("temperatureUnit"),
        "probability_of_precipitation_percent": (period.get("probabilityOfPrecipitation") or {}).get(
            "value"
        ),
        "relative_humidity_percent": (period.get("relativeHumidity") or {}).get("value"),
        "wind_speed_text": period.get("windSpeed"),
        "wind_direction_text": period.get("windDirection"),
        "short_forecast_text": period.get("shortForecast"),
        "grid_office": vintage["grid_office"],
        "grid_x": vintage["grid_x"],
        "grid_y": vintage["grid_y"],
        "forecast_valid_interval": vintage["forecast_valid_interval"],
        "venue_coordinate_authority": coordinate_authority,
        "observed_postgame_weather_used": False,
    }
    return _cell(
        domain=WEATHER_VINTAGE,
        value=value,
        source_id="SRC-NWS-OFFICIAL-API",
        source_observation_identity=str(vintage["forecast_raw_sha256"]),
        raw_capture_sha256=str(vintage["forecast_raw_sha256"]),
        observed_at_utc=str(vintage["retrieved_at_utc"]),
        published_at_utc=str(vintage["forecast_update_time_utc"]),
        snapshot_issuance_utc=snapshot,
        target_kickoff_bound_utc=kickoff,
        known_at_classification="ISSUED_BY_THE_OFFICIAL_FORECAST_OFFICE_BEFORE_THE_SNAPSHOT",
        admission_disposition=CANDIDATE_ONLY_NOT_CONSUMED,
        missingness_reason=None,
        conflict_state="NONE",
    )


def build_spine_rows(
    *,
    contract: Mapping[str, Any],
    contests: Sequence[Mapping[str, Any]],
    participants: Sequence[Mapping[str, Any]],
    rankings: Mapping[str, Any],
    ranking_capture: Mapping[str, Any],
    publication_authority_text: str | None,
    week_zero: Mapping[str, Sequence[Mapping[str, Any]]],
    weather: Mapping[str, Mapping[str, Any]],
    forecast_periods: Mapping[str, Sequence[Mapping[str, Any]]],
    prior_evidence: Mapping[str, Any],
    snapshot_issuance: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Emit two oriented rows per contest and one admission cell per domain."""

    snapshot = iso_utc(snapshot_issuance)
    coordinate_authority = str(
        contract["sources"]["weather_vintage"]["venue_coordinate_authority"]
    )
    conflicting_team_ids = {
        team_id
        for entry in rankings["conflicting_poll_entries"]
        for team_id in entry["source_team_ids"]
    }

    rows: list[dict[str, Any]] = []
    cells: list[dict[str, Any]] = []
    for contest in contests:
        kickoff = contest["kickoff_utc_conservative_lower_bound"]
        if kickoff is not None and parse_utc(kickoff) <= snapshot_issuance:
            raise Week1FeatureSpineViolation(
                f"contest {contest['ncaa_contest_id']} kickoff bound is not after the snapshot"
            )
        oriented = list(contest["participants"])
        if len(oriented) != 2:
            raise Week1FeatureSpineViolation(
                f"contest {contest['ncaa_contest_id']} does not carry two oriented participants"
            )
        if [item["orientation"] for item in oriented] != ["AWAY", "HOME"]:
            raise Week1FeatureSpineViolation(
                f"contest {contest['ncaa_contest_id']} carries a swapped participant orientation"
            )
        for position, side in ((0, "away_team"), (1, "home_team")):
            declared = contest.get(side) or {}
            if str(declared.get("source_team_id")) != str(oriented[position]["source_team_id"]):
                raise Week1FeatureSpineViolation(
                    f"contest {contest['ncaa_contest_id']} disagrees with its own {side} binding"
                )
        for index, participant in enumerate(oriented):
            opponent = oriented[1 - index]
            team_id = str(participant["source_team_id"])
            canonical = participant["canonical_team_id"]
            is_home = participant["orientation"] == "HOME"
            site_orientation = (
                "NEUTRAL"
                if contest["site_state"] == "NEUTRAL"
                else ("HOME" if is_home else "AWAY")
            )
            row_state = (
                SPINE_ROW_ADMITTED
                if contest["disposition"] == "ADMITTED_MODEL_ELIGIBLE"
                else SPINE_ROW_UNSUPPORTED_ENTITY
            )

            weather_key = None
            if contest["site_state"] != "NEUTRAL":
                weather_key = oriented[1]["canonical_team_id"]
            vintage = weather.get(str(weather_key)) if weather_key else None
            period = (
                select_forecast_period(forecast_periods.get(str(weather_key), ()), kickoff)
                if vintage is not None and kickoff is not None
                else None
            )

            row_cells = [
                _prior_cell(
                    prior_evidence=prior_evidence,
                    snapshot=snapshot,
                    kickoff=kickoff,
                ),
                _week_zero_cell(
                    records=week_zero.get(str(canonical), ()) if canonical else (),
                    snapshot=snapshot,
                    kickoff=kickoff,
                    target_contest_id=str(contest["ncaa_contest_id"]),
                ),
                _ranking_cell(
                    ranking=rankings["by_source_team_id"].get(team_id),
                    ranking_capture=ranking_capture,
                    publication_authority_text=publication_authority_text,
                    conflicted=team_id in conflicting_team_ids,
                    poll_coverage_complete=bool(rankings["poll_coverage_complete"]),
                    snapshot=snapshot,
                    kickoff=kickoff,
                ),
                _cell(
                    domain=CONFERENCE_AND_SUBDIVISION,
                    value=(
                        {
                            "subdivision": participant["subdivision"],
                            "division_code": participant["division_code"],
                            "conference_id": participant["conference_id"],
                            "conference_name": participant["conference_name"],
                            "season_authority": "OFFICIAL_2026_27_INSTITUTION_LIST",
                            "inherited_from_a_historical_row": False,
                        }
                        if participant["season_authority_state"]
                        == "OFFICIAL_2026_SEASON_AUTHORITY_BOUND"
                        else None
                    ),
                    source_id="SRC-NCAA-OFFICIAL-STATS",
                    source_observation_identity=participant["season_authority_capture_sha256"],
                    raw_capture_sha256=participant["season_authority_capture_sha256"],
                    observed_at_utc=participant["season_authority_retrieved_at_utc"],
                    published_at_utc=None,
                    snapshot_issuance_utc=snapshot,
                    target_kickoff_bound_utc=kickoff,
                    known_at_classification=(
                        "OFFICIAL_2026_SEASON_MEMBERSHIP_OBSERVED_AT_CAPTURE"
                        if participant["season_authority_state"]
                        == "OFFICIAL_2026_SEASON_AUTHORITY_BOUND"
                        else "NO_OFFICIAL_2026_SEASON_MEMBERSHIP_WAS_PUBLISHED_FOR_THIS_TEAM"
                    ),
                    admission_disposition=(
                        ADMITTED_PROSPECTIVE_PREKICKOFF
                        if participant["season_authority_state"]
                        == "OFFICIAL_2026_SEASON_AUTHORITY_BOUND"
                        and kickoff is not None
                        else SOURCE_EVIDENCE_ABSENT
                    ),
                    missingness_reason=(
                        None
                        if participant["season_authority_state"]
                        == "OFFICIAL_2026_SEASON_AUTHORITY_BOUND"
                        and kickoff is not None
                        else "THE_OFFICIAL_2026_INSTITUTION_LISTS_DO_NOT_CARRY_THIS_TEAM"
                    ),
                    conflict_state="NONE",
                ),
                _cell(
                    domain=VENUE_AND_SITE,
                    value={
                        "site_state": contest["site_state"],
                        "site_orientation": site_orientation,
                        "neutral_site_text": contest["neutral_site_text"],
                        "venue_identity": contest["venue_identity"],
                        "venue_identity_state": contest["venue_identity_state"],
                        "venue_attributes_are_candidate_only": True,
                        "attendance_or_postgame_field_present": False,
                    },
                    source_id="SRC-NCAA-OFFICIAL-STATS",
                    source_observation_identity=contest["contest_identity"],
                    raw_capture_sha256=contest["source_capture_sha256"],
                    observed_at_utc=contest["retrieved_at_utc"],
                    published_at_utc=None,
                    snapshot_issuance_utc=snapshot,
                    target_kickoff_bound_utc=kickoff,
                    known_at_classification="PUBLISHED_SITE_ANNOTATION_OBSERVED_AT_CAPTURE",
                    admission_disposition=(
                        ADMITTED_PROSPECTIVE_PREKICKOFF
                        if kickoff is not None
                        else SOURCE_EVIDENCE_ABSENT
                    ),
                    missingness_reason=(
                        None if kickoff is not None else "THE_TARGET_KICKOFF_BOUND_IS_UNRESOLVED"
                    ),
                    conflict_state="NONE",
                ),
                _weather_cell(
                    vintage=vintage,
                    period=period,
                    snapshot=snapshot,
                    kickoff=kickoff,
                    coordinate_authority=coordinate_authority,
                ),
                _cell(
                    domain=ROSTER_MEMBERSHIP,
                    value=None,
                    source_id=None,
                    source_observation_identity=None,
                    raw_capture_sha256=None,
                    observed_at_utc=None,
                    published_at_utc=None,
                    snapshot_issuance_utc=snapshot,
                    target_kickoff_bound_utc=kickoff,
                    known_at_classification="NO_ROSTER_CAPTURE_EXISTS_FOR_THE_2026_WEEK_1_POPULATION",
                    admission_disposition=SOURCE_EVIDENCE_ABSENT,
                    missingness_reason=str(contract["sources"]["roster_membership"]["reason"]),
                    conflict_state="NONE",
                ),
                _cell(
                    domain=PREGAME_AVAILABILITY,
                    value=None,
                    source_id=None,
                    source_observation_identity=None,
                    raw_capture_sha256=None,
                    observed_at_utc=None,
                    published_at_utc=None,
                    snapshot_issuance_utc=snapshot,
                    target_kickoff_bound_utc=kickoff,
                    known_at_classification="NO_INDEPENDENT_PREGAME_AVAILABILITY_AUTHORITY_EXISTS",
                    admission_disposition=SOURCE_EVIDENCE_ABSENT,
                    missingness_reason=str(contract["sources"]["pregame_availability"]["reason"]),
                    conflict_state="NONE",
                ),
            ]
            if [cell["domain"] for cell in row_cells] != list(FEATURE_DOMAINS):
                raise Week1FeatureSpineViolation("row cells do not cover every declared domain")

            ranking_cell = row_cells[2]
            row: dict[str, Any] = {
                "contest_identity": contest["contest_identity"],
                "ncaa_contest_id": str(contest["ncaa_contest_id"]),
                "season": int(contest["season"]),
                "week_label": str(contest["week_label"]),
                "requested_game_date": contest["requested_game_date"],
                "source_published_game_date": contest["source_published_game_date"],
                "kickoff_utc_conservative_lower_bound": kickoff,
                "kickoff_time_state": contest["kickoff_time_state"],
                "kickoff_utc_independently_confirmed": bool(
                    contest["kickoff_utc_independently_confirmed"]
                ),
                "snapshot_issuance_utc": snapshot,
                "contest_disposition": contest["disposition"],
                "spine_row_state": row_state,
                "orientation": participant["orientation"],
                "site_orientation": site_orientation,
                "is_home": is_home and contest["site_state"] != "NEUTRAL",
                "is_neutral_site": contest["site_state"] == "NEUTRAL",
                "source_team_id": team_id,
                "source_display_name": participant["source_display_name"],
                "canonical_team_id": canonical,
                "team_identity_state": participant["resolution_state"],
                "team_identity_evidence": participant["resolution_evidence"],
                "opponent_source_team_id": str(opponent["source_team_id"]),
                "opponent_canonical_team_id": opponent["canonical_team_id"],
                "opponent_display_name": opponent["source_display_name"],
                "subdivision": participant["subdivision"],
                "conference_id": participant["conference_id"],
                "conference_name": participant["conference_name"],
                "venue_identity": contest["venue_identity"],
                "venue_identity_state": contest["venue_identity_state"],
                "prior_feature_state": row_cells[0]["admission_disposition"],
                "week_zero_result_state": row_cells[1]["admission_disposition"],
                "current_ranking_state": ranking_cell["admission_disposition"],
                "ranked_state": (
                    "RANKED"
                    if (ranking_cell["value"] or {}).get("is_ranked")
                    else ("UNRANKED" if ranking_cell["value"] is not None else "NOT_ESTABLISHED")
                ),
                "poll_rank": (ranking_cell["value"] or {}).get("poll_rank"),
                "poll_rank_is_tied": bool((ranking_cell["value"] or {}).get("poll_rank_is_tied")),
                "weather_vintage_state": row_cells[5]["admission_disposition"],
                "roster_membership_state": row_cells[6]["admission_disposition"],
                "availability_state": "NOT_ESTABLISHED",
                "availability_feature_count": 0,
                "membership_as_availability": False,
                "participation_as_availability": False,
                "admitted_domain_count": sum(
                    1
                    for cell in row_cells
                    if cell["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
                ),
                "candidate_only_domain_count": sum(
                    1
                    for cell in row_cells
                    if cell["admission_disposition"] == CANDIDATE_ONLY_NOT_CONSUMED
                ),
                "missing_domain_count": sum(
                    1
                    for cell in row_cells
                    if cell["admission_disposition"]
                    in (SOURCE_EVIDENCE_ABSENT, TEMPORALLY_INELIGIBLE, UNRESOLVED_ENTITY)
                ),
                "conflicted_domain_count": sum(
                    1
                    for cell in row_cells
                    if cell["admission_disposition"] == QUARANTINED_CONFLICT
                ),
                "missing_domains": [
                    cell["domain"]
                    for cell in row_cells
                    if cell["admission_disposition"]
                    in (SOURCE_EVIDENCE_ABSENT, TEMPORALLY_INELIGIBLE, UNRESOLVED_ENTITY)
                ],
                "tamu_specific_adjustment_applied": False,
                "target_outcome_fields_present": False,
            }
            row["row_identity"] = stable_hash(
                {
                    "contest_identity": row["contest_identity"],
                    "source_team_id": row["source_team_id"],
                    "orientation": row["orientation"],
                    "snapshot_issuance_utc": snapshot,
                    "cells": row_cells,
                }
            )
            rows.append(row)
            for cell in row_cells:
                cells.append(
                    {
                        "row_identity": row["row_identity"],
                        "contest_identity": row["contest_identity"],
                        "ncaa_contest_id": row["ncaa_contest_id"],
                        "source_team_id": row["source_team_id"],
                        "canonical_team_id": row["canonical_team_id"],
                        "orientation": row["orientation"],
                        **cell,
                    }
                )

    _assert_pair_coherence(rows)
    rows.sort(key=lambda row: (row["ncaa_contest_id"], row["orientation"]))
    cells.sort(key=lambda cell: (cell["ncaa_contest_id"], cell["orientation"], cell["domain"]))
    return rows, cells


def _assert_pair_coherence(rows: Sequence[Mapping[str, Any]]) -> None:
    by_contest: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_contest.setdefault(row["ncaa_contest_id"], []).append(row)
    for contest_id, pair in by_contest.items():
        if len(pair) != 2:
            raise Week1FeatureSpineViolation(f"contest {contest_id} does not carry exactly two rows")
        away = next((row for row in pair if row["orientation"] == "AWAY"), None)
        home = next((row for row in pair if row["orientation"] == "HOME"), None)
        if away is None or home is None:
            raise Week1FeatureSpineViolation(f"contest {contest_id} lost its away/home orientation")
        if away["source_team_id"] != home["opponent_source_team_id"] or (
            home["source_team_id"] != away["opponent_source_team_id"]
        ):
            raise Week1FeatureSpineViolation(f"contest {contest_id} pair is incoherent")
        if away["is_home"] or (home["is_home"] == home["is_neutral_site"]):
            raise Week1FeatureSpineViolation(f"contest {contest_id} carries a home/away swap")
        if away["kickoff_utc_conservative_lower_bound"] != home[
            "kickoff_utc_conservative_lower_bound"
        ]:
            raise Week1FeatureSpineViolation(f"contest {contest_id} pair disagrees on kickoff")
    identities = [row["row_identity"] for row in rows]
    if len(set(identities)) != len(identities):
        raise Week1FeatureSpineViolation("spine row identities are not unique")


def summarize(
    rows: Sequence[Mapping[str, Any]], cells: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    domain_admission: dict[str, dict[str, int]] = {
        domain: {disposition: 0 for disposition in ADMISSION_DISPOSITIONS}
        for domain in FEATURE_DOMAINS
    }
    for cell in cells:
        domain_admission[cell["domain"]][cell["admission_disposition"]] += 1
    return {
        "row_count": len(rows),
        "cell_count": len(cells),
        "contest_count": len({row["ncaa_contest_id"] for row in rows}),
        "admitted_contest_count": len(
            {row["ncaa_contest_id"] for row in rows if row["spine_row_state"] == SPINE_ROW_ADMITTED}
        ),
        "unsupported_contest_count": len(
            {
                row["ncaa_contest_id"]
                for row in rows
                if row["spine_row_state"] == SPINE_ROW_UNSUPPORTED_ENTITY
            }
        ),
        "rows_with_canonical_identity": sum(1 for row in rows if row["canonical_team_id"]),
        "rows_by_orientation": dict(sorted(Counter(row["orientation"] for row in rows).items())),
        "rows_by_requested_date": dict(
            sorted(Counter(row["requested_game_date"] for row in rows).items())
        ),
        "rows_by_subdivision": dict(
            sorted(Counter(str(row["subdivision"]) for row in rows).items())
        ),
        "rows_by_ranked_state": dict(
            sorted(Counter(row["ranked_state"] for row in rows).items())
        ),
        "ranked_row_count": sum(1 for row in rows if row["ranked_state"] == "RANKED"),
        "rows_with_week_zero_result": sum(
            1
            for row in rows
            if row["week_zero_result_state"] == ADMITTED_PROSPECTIVE_PREKICKOFF
        ),
        "rows_with_weather_vintage": sum(
            1 for row in rows if row["weather_vintage_state"] == CANDIDATE_ONLY_NOT_CONSUMED
        ),
        "rows_with_official_season_authority": sum(
            1
            for row in rows
            if row["prior_feature_state"] and row["conference_name"] is not None
        ),
        "verified_availability_count": sum(row["availability_feature_count"] for row in rows),
        "domain_admission_counts": domain_admission,
    }


def build_gate(
    *,
    contract: Mapping[str, Any],
    contract_sha256: str,
    rows: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    ranking_evidence: Mapping[str, Any],
    weather_evidence: Mapping[str, Any],
    prior_evidence: Mapping[str, Any],
    manifest_relative_path: str,
    manifest_sha256: str,
    dataset_identity: str,
    payloads: Sequence[Mapping[str, Any]],
    bound_predecessors: Mapping[str, Any],
    snapshot_issuance: datetime,
    execution_time: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_CURRENT_FEATURE_SPINE_GATE",
        "contract_id": CONTRACT_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "protected_lane": PROTECTED_LANE,
        "result": PASS_RESULT,
        "contract_sha256": contract_sha256,
        "season": int(contract["season"]),
        "week_label": str(contract["week_label"]),
        "grain": str(contract["grain"]),
        "snapshot_issuance_utc": iso_utc(snapshot_issuance),
        "feature_domains": list(FEATURE_DOMAINS),
        "admission_dispositions": list(ADMISSION_DISPOSITIONS),
        "temporal_rules": dict(contract["temporal_rules"]),
        "missingness": dict(contract["missingness"]),
        "ranking_evidence": dict(ranking_evidence),
        "weather_evidence": dict(weather_evidence),
        "prior_domain_evidence": dict(prior_evidence),
        "roster_membership_evidence": dict(contract["sources"]["roster_membership"]),
        "availability_evidence": {
            **dict(contract["sources"]["pregame_availability"]),
            "availability_feature_count": 0,
            "verified_availability_count": 0,
        },
        "bound_predecessors": dict(bound_predecessors),
        "manifest": {
            "relative_path": manifest_relative_path,
            "sha256": manifest_sha256,
            "dataset_identity": dataset_identity,
            "bulk_payloads_in_git": False,
        },
        "payloads": [dict(payload) for payload in payloads],
        "payload_root_sha256": stable_hash(
            [
                {"name": payload["name"], "rows": payload["rows"], "sha256": payload["sha256"]}
                for payload in payloads
            ]
        ),
        "summary": summarize(rows, cells),
        "authority": {**dict(contract["authority"]), "protected_lane_admission": False},
        "predecessor_identity": str(bound_predecessors["week1_schedule_identity_gate_identity"]),
        "outcome_exclusion": {
            "target_outcome_fields_present": False,
            "future_contest_result_in_an_earlier_target": False,
            "week_zero_result_precedes_its_official_final_capture": False,
        },
        "tamu_policy": dict(contract["tamu_policy"]),
        "scientific_nonclaims": {
            "bas_or_aggie_excess": False,
            "champion_or_production_selection": False,
            "forecast_published": False,
            "model_tuning_or_promotion": False,
            "protected_performance": False,
            "specialization_lift": False,
            "tamu_specific_adjustment_applied": False,
        },
        "declared_nonclaims": list(contract["scientific_nonclaims"]),
        "execution_time_utc": iso_utc(execution_time),
    }


def dataset_manifest(
    *,
    contract: Mapping[str, Any],
    summary: Mapping[str, Any],
    source_inventory: Sequence[Mapping[str, Any]],
    payloads: Sequence[Mapping[str, Any]],
    snapshot_issuance: datetime,
    execution_time: datetime,
) -> dict[str, Any]:
    core = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "WEEK1_2026_CURRENT_FEATURE_SPINE_MANIFEST",
        "contract_id": CONTRACT_ID,
        "jira_key": JIRA_KEY,
        "classification": CLASSIFICATION,
        "lane": LANE,
        "season": int(contract["season"]),
        "grain": str(contract["grain"]),
        "snapshot_issuance_utc": iso_utc(snapshot_issuance),
        "summary": dict(summary),
        "source_inventory": [dict(row) for row in source_inventory],
        "payloads": [dict(payload) for payload in payloads],
        "authority": dict(contract["authority"]),
        "execution_time_utc": iso_utc(execution_time),
    }
    return {**core, "dataset_identity": stable_hash(core)}


def assert_future_append_invariance(
    rows: Sequence[Mapping[str, Any]], cells: Sequence[Mapping[str, Any]]
) -> None:
    """A later target's evidence must never reach an earlier target's row."""

    by_row = {row["row_identity"]: row for row in rows}
    for cell in cells:
        row = by_row[cell["row_identity"]]
        bound = row["kickoff_utc_conservative_lower_bound"]
        if cell["observed_at_utc"] is None or bound is None:
            continue
        if parse_utc(cell["observed_at_utc"]) >= parse_utc(bound):
            raise Week1FeatureSpineViolation(
                f"cell {cell['domain']} for contest {cell['ncaa_contest_id']} was observed"
                " at or after its own target kickoff bound"
            )
        if cell["domain"] == WEEK_ZERO_CURRENT_RESULT and cell["value"] is not None:
            if str(cell["ncaa_contest_id"]) in set(cell["value"]["contest_ids"]):
                raise Week1FeatureSpineViolation(
                    "a target contest supplied its own completed result"
                )


def validate_artifact(*, repo_root: Path, data_root: Path) -> dict[str, Any]:
    """Revalidate the published spine gate against external evidence without writing."""

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    contract = load_contract(repo_root)
    gate_path = repo_root / GATE_RELATIVE
    findings: list[str] = []
    if not gate_path.is_file():
        return {"result": "FAIL", "findings": ["gate artifact is absent"]}
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    if gate.get("result") != PASS_RESULT:
        findings.append("gate result is not the declared pass result")
    if gate.get("contract_id") != CONTRACT_ID or gate.get("lane") != LANE:
        findings.append("gate contract identity or lane mismatch")
    if gate.get("contract_sha256") != sha256_file(repo_root / CONTRACT_RELATIVE):
        findings.append("contract hash drifted from the published gate")
    if binding_identity(gate, "gate_identity") != gate.get("gate_identity"):
        findings.append("gate identity does not recompute")
    if list(gate.get("feature_domains", ())) != list(FEATURE_DOMAINS):
        findings.append("gate feature domain vocabulary drifted")
    if gate.get("temporal_rules") != dict(contract["temporal_rules"]):
        findings.append("gate temporal rules disagree with the contract")
    if gate.get("missingness") != dict(contract["missingness"]):
        findings.append("gate missingness policy disagrees with the contract")

    manifest_path = data_root / gate["manifest"]["relative_path"]
    if not manifest_path.is_file():
        return {"result": "FAIL", "findings": findings + ["dataset manifest is absent"]}
    if sha256_file(manifest_path) != gate["manifest"]["sha256"]:
        findings.append("dataset manifest hash drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("dataset_identity") != gate["manifest"]["dataset_identity"]:
        findings.append("dataset identity disagrees with the gate binding")

    payload_rows: dict[str, list[dict[str, Any]]] = {}
    for payload in manifest["payloads"]:
        payload_path = data_root / payload["relative_path"]
        if not payload_path.is_file():
            findings.append(f"payload absent: {payload['name']}")
            continue
        if sha256_file(payload_path) != payload["sha256"]:
            findings.append(f"payload hash drifted: {payload['name']}")
            continue
        rows = read_jsonl(payload_path)
        if len(rows) != int(payload["rows"]):
            findings.append(f"payload row count drifted: {payload['name']}")
        payload_rows[payload["name"]] = rows

    rows = payload_rows.get(ROW_PAYLOAD_NAME, [])
    cells = payload_rows.get(CELL_PAYLOAD_NAME, [])
    if rows and cells:
        try:
            _assert_pair_coherence(rows)
            assert_future_append_invariance(rows, cells)
        except Week1FeatureSpineViolation as exc:
            findings.append(str(exc))
        if summarize(rows, cells) != gate["summary"]:
            findings.append("payload summary disagrees with the gate")
        snapshot = gate["snapshot_issuance_utc"]
        for row in rows:
            if row["snapshot_issuance_utc"] != snapshot:
                findings.append(f"row {row['row_identity']} carries a foreign snapshot issuance")
            if row["target_outcome_fields_present"] or row["tamu_specific_adjustment_applied"]:
                findings.append(f"row {row['row_identity']} claimed a forbidden field")
            if row["availability_feature_count"] != 0 or row["availability_state"] != "NOT_ESTABLISHED":
                findings.append(f"row {row['row_identity']} claimed an unverified availability")
            if row["poll_rank"] is not None and int(row["poll_rank"]) >= UNRANKED_SENTINEL_FORBIDDEN:
                findings.append(f"row {row['row_identity']} encoded unranked as a numeric rank")
            if row["poll_rank"] is None and row["ranked_state"] == "RANKED":
                findings.append(f"row {row['row_identity']} claims a rank it does not carry")
            if row["ranked_state"] not in ("RANKED", "UNRANKED", "NOT_ESTABLISHED"):
                findings.append(f"row {row['row_identity']} carries an undeclared ranked state")
            bound = row["kickoff_utc_conservative_lower_bound"]
            if bound is not None and parse_utc(snapshot) >= parse_utc(bound):
                findings.append(f"row {row['row_identity']} snapshot is not before its kickoff")
        for cell in cells:
            if cell["admission_disposition"] not in ADMISSION_DISPOSITIONS:
                findings.append(f"cell {cell['domain']} carries an undeclared disposition")
            if cell["value"] is None and cell["missingness_reason"] is None:
                findings.append(f"cell {cell['domain']} is absent without a reason")
            if (
                cell["admission_disposition"] == ADMITTED_PROSPECTIVE_PREKICKOFF
                and cell["observed_at_utc"] is None
            ):
                findings.append(f"cell {cell['domain']} was admitted without a known-at time")
            if cell["observed_at_utc"] is not None and parse_utc(
                cell["observed_at_utc"]
            ) > parse_utc(cell["snapshot_issuance_utc"]):
                findings.append(f"cell {cell['domain']} known-at exceeds the snapshot issuance")

    for evidence_key, digest_key in (
        ("ranking_evidence", "raw_sha256"),
        ("weather_evidence", "manifest_sha256"),
    ):
        evidence = gate.get(evidence_key, {})
        relative = evidence.get("manifest_relative_path")
        if relative and not (data_root / relative).is_file():
            findings.append(f"{evidence_key} manifest is absent from the data root")
        elif relative and digest_key in evidence:
            observed = sha256_file(data_root / relative)
            if evidence_key == "weather_evidence" and observed != evidence[digest_key]:
                findings.append("weather capture manifest hash drifted")

    if gate["authority"].get("protected_evaluation_admission") is not False:
        findings.append("gate opened protected evaluation")
    if gate["scientific_nonclaims"].get("model_tuning_or_promotion") is not False:
        findings.append("gate claimed model tuning or promotion")
    if gate["tamu_policy"].get("tamu_specific_adjustment_applied") is not False:
        findings.append("gate claimed a Texas A&M specific adjustment")

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "gate_identity": gate.get("gate_identity"),
        "summary": gate.get("summary"),
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
    }


__all__ = [
    "ADMISSION_DISPOSITIONS",
    "CELL_PAYLOAD_NAME",
    "CONTRACT_RELATIVE",
    "FEATURE_DOMAINS",
    "GATE_RELATIVE",
    "PASS_RESULT",
    "PAYLOAD_SLUG",
    "ROW_PAYLOAD_NAME",
    "Week1FeatureSpineViolation",
    "assert_future_append_invariance",
    "build_gate",
    "build_spine_rows",
    "dataset_manifest",
    "index_rankings",
    "index_weather_vintages",
    "index_week_zero_finals",
    "load_contract",
    "parse_ranking_document",
    "read_jsonl",
    "select_forecast_period",
    "summarize",
    "validate_contract",
]
