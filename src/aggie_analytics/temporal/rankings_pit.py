from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


UTC = timezone.utc
CLASSIFICATION = "HISTORICAL_PIT_DOMAIN_ELIGIBLE_DEVELOPMENT_ONLY"
POLICY_VERSION = "historical-ap-rankings-pit-date-only-upper-bound-v1"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timezone-aware timestamp required: {value}")
    return parsed.astimezone(UTC)


def format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def conservative_date_interval(poll_date: str) -> tuple[str, str]:
    parsed = date.fromisoformat(poll_date)
    named_date_utc = datetime(parsed.year, parsed.month, parsed.day, tzinfo=UTC)
    # The archive provides a calendar date, not a timestamp or timezone. This
    # deliberately wide interval contains the named date under every civil
    # UTC offset. Only its conservative upper bound is used for eligibility;
    # neither endpoint is asserted as the actual publication instant.
    lower = named_date_utc - timedelta(days=1)
    upper = named_date_utc + timedelta(days=2)
    return format_utc(lower), format_utc(upper)


def poll_admission_reason(row: Mapping[str, Any]) -> str | None:
    if row.get("cpa_poll_phase") != "DATED_WEEKLY" or not row.get("cpa_poll_date"):
        return "UNDATED_PRESEASON_OR_FINAL"
    if row.get("alignment_state") != "EXACT_HIGH_COVERAGE_UNIQUE":
        return "DATED_POLL_NOT_EXACT_HIGH_COVERAGE_UNIQUE"
    return None


def team_row_admission_reason(row: Mapping[str, Any]) -> str | None:
    if row.get("identity_resolution_state") != "EXACT_VERIFIED_ALIAS_CANDIDATE":
        return "TEAM_IDENTITY_NOT_EXACT_VERIFIED"
    if not row.get("candidate_canonical_team_id"):
        return "CANONICAL_TEAM_ID_MISSING"
    return None


def build_state_row(row: Mapping[str, Any]) -> dict[str, Any]:
    poll_date = str(row["poll_date"])
    interval_start, eligible_at = conservative_date_interval(poll_date)
    payload = {
        "schema_version": "1.0.0",
        "classification": CLASSIFICATION,
        "temporal_policy_version": POLICY_VERSION,
        "poll": "AP",
        "season": int(row["season"]),
        "poll_id": int(row["poll_id"]),
        "poll_order": int(row["poll_order"]),
        "poll_label": str(row["poll_label"]),
        "poll_date": poll_date,
        "publication_time_state": "DATE_ONLY_INTERVAL_EXACT_TIME_UNKNOWN",
        "publication_interval_start_utc": interval_start,
        "publication_interval_end_exclusive_utc": eligible_at,
        "first_eligible_at_utc": eligible_at,
        "canonical_team_id": str(row["candidate_canonical_team_id"]),
        "source_team_id": int(row["source_team_id"]),
        "school": str(row["school"]),
        "rank": int(row["rank"]) if row.get("rank") is not None else None,
        "rank_state": str(row["rank_state"]),
        "points_decimal": row.get("points_decimal"),
        "first_place_votes_decimal": row.get("first_place_votes_decimal"),
        "source_capture_id": str(row["source_capture_id"]),
        "source_response_sha256": str(row["source_response_sha256"]),
        "source_url": str(row["source_url"]),
        "source_record_sha256": str(row["record_sha256"]),
        "admission_disposition": "PIT_ELIGIBLE_CONSERVATIVE_DATE_UPPER_BOUND_EXACT_POLL_AND_TEAM_IDENTITY",
    }
    payload["observation_id"] = "ap_rank_" + stable_hash(payload)[:24]
    return payload


@dataclass(frozen=True)
class PollSnapshot:
    season: int
    poll_id: int
    poll_date: str
    first_eligible_at_utc: str
    teams: Mapping[str, Mapping[str, Any]]


class RankingsIndex:
    def __init__(self, rows: Sequence[Mapping[str, Any]]) -> None:
        grouped: dict[tuple[int, int], list[Mapping[str, Any]]] = {}
        for row in rows:
            grouped.setdefault((int(row["season"]), int(row["poll_id"])), []).append(row)
        by_season: dict[int, list[PollSnapshot]] = {}
        for (season, poll_id), items in grouped.items():
            eligible = str(items[0]["first_eligible_at_utc"])
            poll_date = str(items[0]["poll_date"])
            if any(str(item["first_eligible_at_utc"]) != eligible for item in items):
                raise ValueError(f"poll {poll_id} has inconsistent eligibility bounds")
            teams = {str(item["canonical_team_id"]): item for item in items}
            if len(teams) != len(items):
                raise ValueError(f"poll {poll_id} has duplicate canonical teams")
            by_season.setdefault(season, []).append(
                PollSnapshot(season, poll_id, poll_date, eligible, teams)
            )
        self._snapshots: dict[int, tuple[PollSnapshot, ...]] = {}
        self._eligible_times: dict[int, tuple[datetime, ...]] = {}
        for season, snapshots in by_season.items():
            ordered = tuple(sorted(snapshots, key=lambda item: (item.first_eligible_at_utc, item.poll_id)))
            self._snapshots[season] = ordered
            self._eligible_times[season] = tuple(parse_utc(item.first_eligible_at_utc) for item in ordered)

    def latest(self, season: int, cutoff_utc: str) -> PollSnapshot | None:
        times = self._eligible_times.get(season, ())
        index = bisect_right(times, parse_utc(cutoff_utc)) - 1
        if index < 0:
            return None
        return self._snapshots[season][index]


def build_feature_rows(
    games: Iterable[Mapping[str, Any]], state_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    index = RankingsIndex(state_rows)
    output: list[dict[str, Any]] = []
    for game in sorted(games, key=lambda item: (str(item["start_utc"]), str(item["game_id"]))):
        cutoff = format_utc(parse_utc(str(game["start_utc"])) - timedelta(hours=24))
        snapshot = index.latest(int(game["season"]), cutoff)
        for side in ("home", "away"):
            team_id = str(game[f"{side}_team_id"])
            state = snapshot.teams.get(team_id) if snapshot else None
            payload = {
                "schema_version": "1.0.0",
                "classification": CLASSIFICATION,
                "temporal_policy_version": POLICY_VERSION,
                "target_game_id": str(game["game_id"]),
                "season": int(game["season"]),
                "season_type": str(game["season_type"]),
                "start_utc": str(game["start_utc"]),
                "cutoff_utc": cutoff,
                "team_side": side.upper(),
                "canonical_team_id": team_id,
                "poll_available": snapshot is not None,
                "team_listed_in_poll": state is not None,
                "poll_id": snapshot.poll_id if snapshot else None,
                "poll_date": snapshot.poll_date if snapshot else None,
                "poll_first_eligible_at_utc": snapshot.first_eligible_at_utc if snapshot else None,
                "rank": state.get("rank") if state else None,
                "rank_state": state.get("rank_state") if state else "NOT_LISTED_OR_NO_ELIGIBLE_POLL",
                "points_decimal": state.get("points_decimal") if state else None,
                "first_place_votes_decimal": state.get("first_place_votes_decimal") if state else None,
                "source_observation_id": state.get("observation_id") if state else None,
                "missingness_disposition": (
                    "OBSERVED_SOURCE_ROW"
                    if state
                    else "TEAM_NOT_LISTED_IN_LATEST_ELIGIBLE_POLL"
                    if snapshot
                    else "NO_POLL_ELIGIBLE_AT_TARGET_CUTOFF"
                ),
            }
            if snapshot and parse_utc(snapshot.first_eligible_at_utc) > parse_utc(cutoff):
                raise ValueError("future poll crossed target cutoff")
            payload["feature_row_id"] = "ap_rank_feature_" + stable_hash(payload)[:24]
            output.append(payload)
    return output
