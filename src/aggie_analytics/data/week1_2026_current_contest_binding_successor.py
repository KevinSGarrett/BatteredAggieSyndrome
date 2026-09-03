"""Current-contest Week 1 feature binding successor.

The Cycle #25 copy-terminal-historical-row successor remains immutable and
deprecated. Target rows are built from current contest authority only.
"""

from __future__ import annotations

from typing import Any, Mapping

DEPRECATE_PREDECESSOR = "week1_2026_forecast_input_binding_successor"
SHADOW_CLASSIFICATION = "UNTRUSTED_SHADOW"


def resolve_current_contest(
    team_key: str, contests: list[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    team = str(team_key or "").strip()
    if not team:
        return None
    matches: list[Mapping[str, Any]] = []
    for contest in contests:
        contest_id = str(contest.get("contest_id") or "").strip()
        home = str(contest.get("home_team_key") or "").strip()
        away = str(contest.get("away_team_key") or "").strip()
        if not contest_id or not home or not away:
            continue
        if team in {home, away}:
            matches.append(contest)
    if len(matches) != 1:
        return None
    return matches[0]


def build_current_contest_row(
    *,
    team_key: str,
    contests: list[Mapping[str, Any]],
    historical_priors: Mapping[str, Any],
    current_conference: str | None,
    current_subdivision: str | None,
    current_rank: str | None,
    rank_admitted: bool,
    official_2026_finals_known_before_cutoff: Mapping[str, Any] | None,
    trust_gate_open: bool,
) -> dict[str, Any]:
    contest = resolve_current_contest(team_key, contests)
    if not str(team_key or "").strip():
        return {
            "team_key": team_key,
            "row_state": "ABSTAIN_EMPTY_TEAM_ID",
            "copied_from_terminal_historical_row": False,
            "trust_classification": SHADOW_CLASSIFICATION,
        }
    if contest is None:
        multiple = [
            row
            for row in contests
            if str(team_key) in {
                str(row.get("home_team_key") or "").strip(),
                str(row.get("away_team_key") or "").strip(),
            }
            and str(row.get("contest_id") or "").strip()
        ]
        reason = (
            "ABSTAIN_AMBIGUOUS_CURRENT_CONTEST"
            if len(multiple) > 1
            else "ABSTAIN_CURRENT_CONTEST_UNRESOLVED"
        )
        return {
            "team_key": team_key,
            "row_state": reason,
            "copied_from_terminal_historical_row": False,
            "trust_classification": SHADOW_CLASSIFICATION,
        }
    opponent = (
        contest["away_team_key"]
        if team_key == contest["home_team_key"]
        else contest["home_team_key"]
    )
    season_to_date = official_2026_finals_known_before_cutoff or {}
    rank_value = current_rank if rank_admitted else None
    ready_fields = {
        "opponent_key": opponent,
        "conference": current_conference,
        "subdivision": current_subdivision,
        "prior_from_earlier_games": historical_priors.get(team_key),
        "opponent_prior_from_earlier_games": historical_priors.get(opponent),
    }
    missing = [name for name, value in ready_fields.items() if value in (None, "")]
    row_state = "FORECAST_INPUT_BOUND" if not missing else "ABSTAIN_MISSING_REQUIRED_FIELDS"
    if not trust_gate_open:
        row_state = "UNTRUSTED_SHADOW"
    return {
        "team_key": team_key,
        "opponent_key": opponent,
        "contest_id": contest.get("contest_id"),
        "conference": current_conference,
        "subdivision": current_subdivision,
        "rank": rank_value,
        "rank_admitted": rank_admitted,
        "season_to_date_from_official_2026_finals_only": season_to_date,
        "copied_from_terminal_historical_row": False,
        "historical_analogue_exists": bool(historical_priors.get(team_key)),
        "semantic_equivalence": False,
        "current_authority": True,
        "ood": bool(missing),
        "missing_fields": missing,
        "row_state": row_state,
        "trust_classification": SHADOW_CLASSIFICATION,
        "deprecated_predecessor": DEPRECATE_PREDECESSOR,
    }


def report_mismatches(
    original_rows: list[Mapping[str, Any]],
    corrected_rows: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    original_by_team = {str(row.get("team_key")): row for row in original_rows}
    mismatches = []
    for corrected in corrected_rows:
        team_key = str(corrected.get("team_key"))
        original = original_by_team.get(team_key) or {}
        for field in ("opponent_key", "conference", "subdivision", "rank"):
            if original.get(field) != corrected.get(field):
                mismatches.append(
                    {
                        "team_key": team_key,
                        "field": field,
                        "original": original.get(field),
                        "corrected": corrected.get(field),
                    }
                )
        if original.get("copied_from_terminal_historical_row") is True:
            mismatches.append(
                {
                    "team_key": team_key,
                    "field": "copied_from_terminal_historical_row",
                    "original": True,
                    "corrected": False,
                }
            )
    return mismatches
