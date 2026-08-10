from __future__ import annotations
from dataclasses import dataclass
from .contracts import ForecastCutoff, TemporalObservation
from .eligibility import evaluate_eligibility, knowledge_time
from aggie_analytics.lineage import LineageRecord, make_lineage
@dataclass(frozen=True)
class PitState:
    state_id:str; cutoff_id:str; observations:tuple[TemporalObservation,...]; lineage:LineageRecord

def build_pit_state(observations, cutoff:ForecastCutoff)->PitState:
    eligible=[]
    for obs in observations:
        result=evaluate_eligibility(obs,cutoff)
        if result.eligible: eligible.append(obs)
    eligible.sort(key=lambda o:(knowledge_time(o),o.observation_id))
    parent_ids=[o.observation_id for o in eligible]
    lineage=make_lineage('PIT_STATE',f'state_{cutoff.cutoff_id}',parent_ids,'w19.pit.fail_closed',{'cutoff':cutoff.cutoff_id})
    return PitState(f'state_{cutoff.cutoff_id}',cutoff.cutoff_id,tuple(eligible),lineage)


import hashlib
import json
from enum import Enum
from typing import Any, Iterable, Mapping

from .eligibility import select_latest_eligible


class MissingnessClass(str, Enum):
    """Mutually exclusive reason a pregame matrix cell has no value."""

    STRUCTURAL = "STRUCTURAL"
    NOT_KNOWN_AT_CUTOFF = "NOT_KNOWN_AT_CUTOFF"
    SOURCE_MISSING = "SOURCE_MISSING"
    RESOLUTION_MISSING = "RESOLUTION_MISSING"
    PIPELINE_MISSING = "PIPELINE_MISSING"


@dataclass(frozen=True)
class MatrixCell:
    feature_name: str
    value: Any
    observation_id: str | None
    missingness: MissingnessClass | None
    lineage: LineageRecord


@dataclass(frozen=True)
class PregameMatrixRow:
    row_id: str
    game_id: str
    cutoff_id: str
    team_id: str
    opponent_id: str
    site: str
    lower_division_opponent: bool
    cells: tuple[MatrixCell, ...]
    lineage: LineageRecord


def classify_game_site(
    *, team_id: str, home_team_id: str, away_team_id: str, neutral_site: bool
) -> str:
    """Return a deterministic team-relative game-site label."""

    if not team_id or team_id not in {home_team_id, away_team_id}:
        raise ValueError("team_id must be the home or away team")
    if not home_team_id or not away_team_id or home_team_id == away_team_id:
        raise ValueError("home and away teams must be distinct nonempty identities")
    if neutral_site:
        return "NEUTRAL"
    return "HOME" if team_id == home_team_id else "AWAY"


def classify_missingness(
    *,
    structurally_applicable: bool,
    observations_exist: bool,
    source_available: bool,
    resolution_complete: bool,
    pipeline_complete: bool,
) -> MissingnessClass:
    """Classify a missing value without conflating independent failure modes.

    Inputs describe evidence that has already failed to yield an eligible value.
    The precedence is intentional and fail-closed: structural non-applicability,
    pipeline failure, identity resolution, source absence, then cutoff knowledge.
    """

    if not structurally_applicable:
        return MissingnessClass.STRUCTURAL
    if not pipeline_complete:
        return MissingnessClass.PIPELINE_MISSING
    if not resolution_complete:
        return MissingnessClass.RESOLUTION_MISSING
    if not source_available or not observations_exist:
        return MissingnessClass.SOURCE_MISSING
    return MissingnessClass.NOT_KNOWN_AT_CUTOFF


def _stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    ).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:24]}"


def build_pregame_matrix_row(
    *,
    game_id: str,
    cutoff: ForecastCutoff,
    team_id: str,
    home_team_id: str,
    away_team_id: str,
    lower_division_team_ids: Iterable[str],
    game_status: str,
    feature_observations: Mapping[str, Iterable[TemporalObservation]],
    structurally_applicable: Mapping[str, bool] | None = None,
    source_available: Mapping[str, bool] | None = None,
    resolution_complete: Mapping[str, bool] | None = None,
    pipeline_complete: Mapping[str, bool] | None = None,
    fallback_features: Mapping[str, Iterable[str]] | None = None,
    neutral_site: bool = False,
) -> PregameMatrixRow | None:
    """Build one leakage-safe, row/cell-lineaged pregame matrix row.

    Cancelled games produce no row. Feature fallbacks are tried in declared
    order but may only contribute an observation independently eligible at the
    same cutoff. Missing values retain one explicit missingness class.
    """

    if game_status.strip().upper() in {"CANCELLED", "CANCELED"}:
        return None
    if cutoff.target_game_id and cutoff.target_game_id != game_id:
        raise ValueError("cutoff target_game_id does not match game_id")

    structural = structurally_applicable or {}
    sources = source_available or {}
    resolutions = resolution_complete or {}
    pipelines = pipeline_complete or {}
    fallbacks = fallback_features or {}
    opponent_id = away_team_id if team_id == home_team_id else home_team_id
    site = classify_game_site(
        team_id=team_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        neutral_site=neutral_site,
    )
    row_key = {
        "cutoff_id": cutoff.cutoff_id,
        "game_id": game_id,
        "team_id": team_id,
    }
    row_id = _stable_id("matrix_row", row_key)

    cells: list[MatrixCell] = []
    for feature_name in sorted(feature_observations):
        primary = tuple(feature_observations[feature_name])
        candidate_sets = [(feature_name, primary)]
        for fallback_name in fallbacks.get(feature_name, ()):
            candidate_sets.append(
                (fallback_name, tuple(feature_observations.get(fallback_name, ())))
            )

        selected: TemporalObservation | None = None
        selected_feature = feature_name
        for candidate_name, candidates in candidate_sets:
            selected = select_latest_eligible(candidates, cutoff)
            if selected is not None:
                selected_feature = candidate_name
                break

        cell_id = _stable_id(
            "matrix_cell", {**row_key, "feature_name": feature_name}
        )
        if selected is not None:
            value = (selected.attributes or {}).get("value")
            if value is None:
                selected = None
            else:
                lineage = make_lineage(
                    "PREGAME_MATRIX_CELL",
                    cell_id,
                    [selected.observation_id],
                    "w25.pregame_matrix.eligible_only",
                    {
                        "cutoff_id": cutoff.cutoff_id,
                        "feature_name": feature_name,
                        "selected_feature": selected_feature,
                    },
                )
                cells.append(
                    MatrixCell(feature_name, value, selected.observation_id, None, lineage)
                )
                continue

        observations_exist = any(candidates for _, candidates in candidate_sets)
        missingness = classify_missingness(
            structurally_applicable=structural.get(feature_name, True),
            observations_exist=observations_exist,
            source_available=sources.get(feature_name, True),
            resolution_complete=resolutions.get(feature_name, True),
            pipeline_complete=pipelines.get(feature_name, True),
        )
        lineage = make_lineage(
            "PREGAME_MATRIX_CELL",
            cell_id,
            [],
            "w25.pregame_matrix.fail_closed_missingness",
            {
                "cutoff_id": cutoff.cutoff_id,
                "feature_name": feature_name,
                "missingness": missingness.value,
            },
        )
        cells.append(MatrixCell(feature_name, None, None, missingness, lineage))

    row_lineage = make_lineage(
        "PREGAME_MATRIX_ROW",
        row_id,
        [cell.lineage.lineage_id for cell in cells],
        "w25.pregame_matrix.row_assembly",
        {
            "cutoff_id": cutoff.cutoff_id,
            "game_id": game_id,
            "site": site,
            "team_id": team_id,
        },
    )
    return PregameMatrixRow(
        row_id=row_id,
        game_id=game_id,
        cutoff_id=cutoff.cutoff_id,
        team_id=team_id,
        opponent_id=opponent_id,
        site=site,
        lower_division_opponent=opponent_id in set(lower_division_team_ids),
        cells=tuple(cells),
        lineage=row_lineage,
    )
