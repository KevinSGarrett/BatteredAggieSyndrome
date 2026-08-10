from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence

from .contracts import parse_time


STRICT_OUTCOME_DISPOSITION = "ELIGIBLE_CROSS_SOURCE_EXACT_OUTCOME"
HISTORICAL_OUTCOME_POLICY_VERSION = "bat523.team-outcome-context.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _stable_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = str(row.get(key) or "").strip()
    if not value:
        raise ValueError(f"{key} must be nonempty")
    return value


def _required_sha256(row: Mapping[str, Any], key: str) -> str:
    value = _required_text(row, key).lower()
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{key} must be a lowercase SHA-256 digest")
    return value


def _aware(value: str | datetime | None, key: str) -> datetime:
    parsed = parse_time(value)
    if parsed is None:
        raise ValueError(f"{key} must be present")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class HistoricalOutcome:
    observation_id: str
    source_game_id: str
    canonical_game_id: str
    season: int
    season_type: int
    game_start_utc: datetime
    completed_known_by_utc: datetime
    source_known_at_utc: datetime
    home_team_id: str
    away_team_id: str
    home_points: int
    away_points: int
    source_capture_id: str
    source_payload_sha256: str
    source_record_evidence_sha256: str
    reconciliation_disposition: str


@dataclass(frozen=True)
class TeamOutcomeObservation:
    observation_id: str
    canonical_game_id: str
    source_game_id: str
    season: int
    team_id: str
    opponent_id: str
    site: str
    points_for: int
    points_against: int
    result: str
    source_known_at_utc: datetime
    game_start_utc: datetime
    completed_known_by_utc: datetime
    source_capture_id: str
    source_payload_sha256: str
    source_record_evidence_sha256: str
    temporal_policy_version: str = HISTORICAL_OUTCOME_POLICY_VERSION


@dataclass(frozen=True)
class TargetGame:
    game_id: str
    season: int
    season_type: str
    week: int | None
    start_utc: datetime
    home_team_id: str
    away_team_id: str
    neutral_site: bool


@dataclass(frozen=True)
class PregamePriorRow:
    row_id: str
    target_game_id: str
    cutoff_utc: datetime
    target_start_utc: datetime
    season: int
    season_type: str
    week: int | None
    team_id: str
    opponent_id: str
    site: str
    eligible_observation_ids: tuple[str, ...]
    prior_games: int | None
    prior_win_rate: float | None
    prior_points_for_mean: float | None
    prior_points_against_mean: float | None
    missingness: str | None
    lineage_sha256: str


@dataclass(frozen=True)
class PregamePriorCell:
    cell_id: str
    row_id: str
    target_game_id: str
    cutoff_utc: datetime
    team_id: str
    feature_name: str
    value: int | float | None
    observation_ids: tuple[str, ...]
    missingness: str | None
    lineage_sha256: str


def admit_strict_cross_source_outcomes(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[HistoricalOutcome, ...]:
    """Admit only completed, identity-matched, exact cross-source outcomes.

    Repository-versioned single-source rows intentionally require a different
    admission call and cannot be silently promoted by this strict lane.
    """

    accepted: list[HistoricalOutcome] = []
    seen_games: set[str] = set()
    for row in rows:
        disposition = _required_text(row, "reconciliation_disposition")
        if disposition != STRICT_OUTCOME_DISPOSITION:
            continue
        if row.get("completed") is not True:
            raise ValueError("strict historical outcomes must be completed")
        if row.get("canonical_team_pair_match") is not True:
            raise ValueError("strict historical outcomes require canonical team-pair match")
        if row.get("normalized_outcome_exact_match") is not True:
            raise ValueError("strict historical outcomes require exact normalized outcome match")

        canonical_game_id = _required_text(row, "canonical_game_id")
        if canonical_game_id in seen_games:
            raise ValueError(f"duplicate canonical game in strict outcome lane: {canonical_game_id}")
        seen_games.add(canonical_game_id)

        known_at = _aware(row.get("source_known_at_utc"), "source_known_at_utc")
        game_start = _aware(row.get("start_at_utc"), "start_at_utc")
        if known_at <= game_start:
            raise ValueError("versioned completed outcome evidence must postdate game start")
        home_team_id = _required_text(row, "canonical_home_team_id")
        away_team_id = _required_text(row, "canonical_away_team_id")
        if home_team_id == away_team_id:
            raise ValueError("historical outcome teams must be distinct")
        home_points = int(row["home_points"])
        away_points = int(row["away_points"])
        if home_points < 0 or away_points < 0:
            raise ValueError("historical outcome scores must be nonnegative")

        evidence_sha = _required_sha256(row, "source_record_evidence_sha256")
        observation_id = "hist_outcome_" + _stable_hash(
            {
                "canonical_game_id": canonical_game_id,
                "source_known_at_utc": known_at.isoformat(),
                "source_record_evidence_sha256": evidence_sha,
            }
        )[:24]
        accepted.append(
            HistoricalOutcome(
                observation_id=observation_id,
                source_game_id=_required_text(row, "source_game_id"),
                canonical_game_id=canonical_game_id,
                season=int(row["season"]),
                season_type=int(row["season_type"]),
                game_start_utc=game_start,
                completed_known_by_utc=known_at,
                source_known_at_utc=known_at,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_points=home_points,
                away_points=away_points,
                source_capture_id=_required_sha256(row, "source_capture_id"),
                source_payload_sha256=_required_sha256(row, "source_payload_sha256"),
                source_record_evidence_sha256=evidence_sha,
                reconciliation_disposition=disposition,
            )
        )
    return tuple(sorted(accepted, key=lambda x: (x.game_start_utc, x.canonical_game_id)))


def materialize_team_outcome_observations(
    outcomes: Iterable[HistoricalOutcome],
) -> tuple[TeamOutcomeObservation, ...]:
    observations: list[TeamOutcomeObservation] = []
    for outcome in outcomes:
        for site, team_id, opponent_id, points_for, points_against in (
            (
                "HOME",
                outcome.home_team_id,
                outcome.away_team_id,
                outcome.home_points,
                outcome.away_points,
            ),
            (
                "AWAY",
                outcome.away_team_id,
                outcome.home_team_id,
                outcome.away_points,
                outcome.home_points,
            ),
        ):
            result = "WIN" if points_for > points_against else "LOSS"
            if points_for == points_against:
                result = "TIE"
            observation_id = "team_outcome_" + _stable_hash(
                {
                    "parent": outcome.observation_id,
                    "team_id": team_id,
                    "site": site,
                }
            )[:24]
            observations.append(
                TeamOutcomeObservation(
                    observation_id=observation_id,
                    canonical_game_id=outcome.canonical_game_id,
                    source_game_id=outcome.source_game_id,
                    season=outcome.season,
                    team_id=team_id,
                    opponent_id=opponent_id,
                    site=site,
                    points_for=points_for,
                    points_against=points_against,
                    result=result,
                    source_known_at_utc=outcome.source_known_at_utc,
                    game_start_utc=outcome.game_start_utc,
                    completed_known_by_utc=outcome.completed_known_by_utc,
                    source_capture_id=outcome.source_capture_id,
                    source_payload_sha256=outcome.source_payload_sha256,
                    source_record_evidence_sha256=outcome.source_record_evidence_sha256,
                )
            )
    return tuple(
        sorted(observations, key=lambda x: (x.game_start_utc, x.canonical_game_id, x.team_id))
    )


def target_game_from_mapping(row: Mapping[str, Any]) -> TargetGame:
    game_id = _required_text(row, "canonical_id")
    home_team_id = _required_text(row, "home_team_id")
    away_team_id = _required_text(row, "away_team_id")
    if home_team_id == away_team_id:
        raise ValueError("target game teams must be distinct")
    return TargetGame(
        game_id=game_id,
        season=int(row["season"]),
        season_type=_required_text(row, "season_type"),
        week=int(row["week"]) if row.get("week") is not None else None,
        start_utc=_aware(row.get("start_time_utc"), "start_time_utc"),
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        neutral_site=bool(row.get("neutral_site", False)),
    )


def build_pregame_team_priors(
    observations: Sequence[TeamOutcomeObservation],
    target_games: Iterable[TargetGame],
    *,
    cutoff_lead: timedelta = timedelta(hours=24),
) -> tuple[PregamePriorRow, ...]:
    if cutoff_lead <= timedelta(0):
        raise ValueError("cutoff_lead must be positive")
    by_team: dict[str, list[TeamOutcomeObservation]] = {}
    for observation in observations:
        by_team.setdefault(observation.team_id, []).append(observation)
    for team_observations in by_team.values():
        team_observations.sort(
            key=lambda x: (x.source_known_at_utc, x.game_start_utc, x.observation_id)
        )

    result: list[PregamePriorRow] = []
    for target in sorted(target_games, key=lambda x: (x.start_utc, x.game_id)):
        cutoff = target.start_utc - cutoff_lead
        for team_id, opponent_id, site in (
            (
                target.home_team_id,
                target.away_team_id,
                "NEUTRAL" if target.neutral_site else "HOME",
            ),
            (
                target.away_team_id,
                target.home_team_id,
                "NEUTRAL" if target.neutral_site else "AWAY",
            ),
        ):
            eligible = tuple(
                obs
                for obs in by_team.get(team_id, ())
                if obs.canonical_game_id != target.game_id
                and obs.game_start_utc < cutoff
                and obs.completed_known_by_utc <= cutoff
                and obs.source_known_at_utc <= cutoff
            )
            ids = tuple(obs.observation_id for obs in eligible)
            row_basis = {
                "target_game_id": target.game_id,
                "cutoff_utc": cutoff.isoformat(),
                "team_id": team_id,
                "eligible_observation_ids": ids,
                "policy": HISTORICAL_OUTCOME_POLICY_VERSION,
            }
            lineage_sha = _stable_hash(row_basis)
            row_id = "pregame_prior_" + lineage_sha[:24]
            if not eligible:
                result.append(
                    PregamePriorRow(
                        row_id=row_id,
                        target_game_id=target.game_id,
                        cutoff_utc=cutoff,
                        target_start_utc=target.start_utc,
                        season=target.season,
                        season_type=target.season_type,
                        week=target.week,
                        team_id=team_id,
                        opponent_id=opponent_id,
                        site=site,
                        eligible_observation_ids=(),
                        prior_games=None,
                        prior_win_rate=None,
                        prior_points_for_mean=None,
                        prior_points_against_mean=None,
                        missingness="SOURCE_MISSING",
                        lineage_sha256=lineage_sha,
                    )
                )
                continue

            games = len(eligible)
            wins = sum(obs.result == "WIN" for obs in eligible)
            result.append(
                PregamePriorRow(
                    row_id=row_id,
                    target_game_id=target.game_id,
                    cutoff_utc=cutoff,
                    target_start_utc=target.start_utc,
                    season=target.season,
                    season_type=target.season_type,
                    week=target.week,
                    team_id=team_id,
                    opponent_id=opponent_id,
                    site=site,
                    eligible_observation_ids=ids,
                    prior_games=games,
                    prior_win_rate=wins / games,
                    prior_points_for_mean=sum(obs.points_for for obs in eligible) / games,
                    prior_points_against_mean=sum(obs.points_against for obs in eligible) / games,
                    missingness=None,
                    lineage_sha256=lineage_sha,
                )
            )
    return tuple(result)


def materialize_prior_cells(
    rows: Iterable[PregamePriorRow],
) -> tuple[PregamePriorCell, ...]:
    """Expand aggregate rows into independently lineaged feature cells."""

    cells: list[PregamePriorCell] = []
    for row in rows:
        values = (
            ("prior_games", row.prior_games),
            ("prior_win_rate", row.prior_win_rate),
            ("prior_points_for_mean", row.prior_points_for_mean),
            ("prior_points_against_mean", row.prior_points_against_mean),
        )
        for feature_name, value in values:
            lineage_sha = _stable_hash(
                {
                    "row_lineage_sha256": row.lineage_sha256,
                    "feature_name": feature_name,
                    "value": value,
                    "observation_ids": row.eligible_observation_ids,
                    "missingness": row.missingness,
                    "policy": HISTORICAL_OUTCOME_POLICY_VERSION,
                }
            )
            cells.append(
                PregamePriorCell(
                    cell_id="pregame_cell_" + lineage_sha[:24],
                    row_id=row.row_id,
                    target_game_id=row.target_game_id,
                    cutoff_utc=row.cutoff_utc,
                    team_id=row.team_id,
                    feature_name=feature_name,
                    value=value,
                    observation_ids=row.eligible_observation_ids,
                    missingness=row.missingness,
                    lineage_sha256=lineage_sha,
                )
            )
    return tuple(cells)


def record_for_storage(value: Any) -> dict[str, Any]:
    """Convert a recovery dataclass to a deterministic, storage-safe mapping."""

    record = asdict(value)
    for key, item in tuple(record.items()):
        if isinstance(item, datetime):
            record[key] = item.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        elif isinstance(item, tuple):
            record[key] = list(item)
    return record
