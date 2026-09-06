"""Cycle 27 remaining-checkpoint current-contest binding.

The Cycle 26 Week 1 materializer still copies Cycle 24 forecast rows and mutates
probability/interval. This module is the actual remaining-checkpoint execution
path: it calls ``build_current_contest_row`` for each participant and does not
issue a new FORECAST_FROZEN probability while the scientific-trust gate is
closed. Already-kicked-off contests are retrospective diagnostics only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from aggie_analytics.data.week1_2026_current_contest_binding_successor import (
    SHADOW_CLASSIFICATION,
    build_current_contest_row,
)

SCHEMA_VERSION = "aggie.data.cycle27_current_contest_checkpoint_binding.v1"
CONTRACT_ID = "CYCLE27-CURRENT-CONTEST-CHECKPOINT-BINDING-V1"
JIRA_KEY = "BAT-693"
PARENT_JIRA_KEY = "BAT-523"
LOCAL_ISSUE_ID = "POST-TASK-WEEK1-FORECAST-BINDING-AND-COHERENCE-SUCCESSOR-001"
ARTIFACT_TYPE = "CYCLE27_CURRENT_CONTEST_CHECKPOINT_BINDING"
GATE_RELATIVE = "artifacts/scientific_integrity/cycle27/CYCLE27_CURRENT_CONTEST_CHECKPOINT_BINDING.json"
C26_GATE_IDENTITY = "aa4ff84b16e9f00b1e68965cef7ea8730adc456ad16bda6ed1ff564b5bcdcb43"
C26_DATASET_IDENTITY = (
    "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
)
FOCUS_CONTEST_ID = "6607349"
FRIDAY_T90_CONTEST_ID = "6594366"
HELPER_SYMBOL = "build_current_contest_row"

BindFn = Callable[..., Mapping[str, Any]]


class CurrentContestCheckpointBindingError(ValueError):
    """Raised when remaining-checkpoint current-contest binding cannot proceed honestly."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def utc_now_label(now: datetime | None = None) -> str:
    stamp = now or datetime.now(timezone.utc)
    return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def contests_from_census_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        contest_id = str(row.get("ncaa_contest_id") or "").strip()
        canonical = str(row.get("canonical_team_id") or "").strip()
        source = str(row.get("source_team_id") or "").strip()
        team = canonical or (f"UNRESOLVED:{source}" if source else "")
        orientation = str(row.get("site_orientation") or "").strip()
        if not contest_id or not team or orientation not in {"HOME", "AWAY", "NEUTRAL"}:
            continue
        rec = by_id.setdefault(contest_id, {"contest_id": contest_id})
        person = {
            "canonical_team_id": team,
            "conference_name": row.get("conference_name"),
            "subdivision": row.get("subdivision"),
            "source_team_id": row.get("source_team_id"),
            "ncaa_listed_orientation": str(
                row.get("ncaa_listed_orientation") or ""
            ).strip(),
        }
        if orientation == "HOME":
            rec["home_team_key"] = team
            rec["home_conference"] = row.get("conference_name")
            rec["home_subdivision"] = row.get("subdivision")
            rec["home_source_team_id"] = row.get("source_team_id")
        elif orientation == "AWAY":
            rec["away_team_key"] = team
            rec["away_conference"] = row.get("conference_name")
            rec["away_subdivision"] = row.get("subdivision")
            rec["away_source_team_id"] = row.get("source_team_id")
        else:
            rec.setdefault("neutral_participants", []).append(person)
    contests = []
    for rec in by_id.values():
        neutrals = list(rec.get("neutral_participants") or [])
        if rec.get("home_team_key") and rec.get("away_team_key"):
            rec.setdefault("site", None)
            contests.append(rec)
            continue
        if (
            len(neutrals) == 2
            and not rec.get("home_team_key")
            and not rec.get("away_team_key")
        ):
            listed_home = [
                item
                for item in neutrals
                if str(item.get("ncaa_listed_orientation") or "").upper() == "HOME"
            ]
            listed_away = [
                item
                for item in neutrals
                if str(item.get("ncaa_listed_orientation") or "").upper() == "AWAY"
            ]
            if len(listed_home) != 1 or len(listed_away) != 1:
                rec["site"] = "NEUTRAL"
                rec["listed_home_authority"] = "ABSTAIN_NEUTRAL_LISTED_HOME_UNKNOWN"
                rec["orientation_abstained"] = True
                rec["neutral_participants"] = neutrals
                contests.append(rec)
                continue
            rec["home_team_key"] = listed_home[0]["canonical_team_id"]
            rec["away_team_key"] = listed_away[0]["canonical_team_id"]
            rec["home_conference"] = listed_home[0].get("conference_name")
            rec["away_conference"] = listed_away[0].get("conference_name")
            rec["home_subdivision"] = listed_home[0].get("subdivision")
            rec["away_subdivision"] = listed_away[0].get("subdivision")
            rec["home_source_team_id"] = listed_home[0].get("source_team_id")
            rec["away_source_team_id"] = listed_away[0].get("source_team_id")
            rec["site"] = "NEUTRAL"
            rec["listed_home_authority"] = (
                "NCAA_LISTED_HOME_ON_NEUTRAL_SITE_NOT_SORTED_CANONICAL_ID"
            )
            contests.append(rec)
    return sorted(contests, key=lambda item: str(item["contest_id"]))


def issuance_for_row(*, kicked_off: bool, trust_gate_open: bool) -> dict[str, Any]:
    if kicked_off:
        return {
            "forecast_issuance": "RETROSPECTIVE_DIAGNOSTIC_NOT_PROSPECTIVE_FREEZE",
            "new_prospective_freeze": False,
            "publication_label": SHADOW_CLASSIFICATION,
        }
    if not trust_gate_open:
        return {
            "forecast_issuance": "ABSTAIN_SCIENTIFIC_TRUST_GATE_BLOCKED",
            "new_prospective_freeze": False,
            "publication_label": SHADOW_CLASSIFICATION,
        }
    return {
        "forecast_issuance": "ELIGIBLE_ONLY_IF_FITTED_PATH_ACCEPTED",
        "new_prospective_freeze": False,
        "publication_label": SHADOW_CLASSIFICATION,
    }


def bind_team_for_checkpoint(
    *,
    team_key: str,
    contests: Sequence[Mapping[str, Any]],
    current_conference: str | None,
    current_subdivision: str | None,
    current_rank: str | None = None,
    rank_admitted: bool = False,
    historical_priors: Mapping[str, Any] | None = None,
    official_2026_finals_known_before_cutoff: Mapping[str, Any] | None = None,
    trust_gate_open: bool = False,
    kicked_off: bool = False,
    terminal_historical_opponent: str | None = None,
    site: str | None = None,
    venue: str | None = None,
    coordinates: tuple[float, float] | None = None,
    helper: BindFn | None = None,
    helper_calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Bind one participant through the current-contest helper.

    ``helper`` is injectable so purity tests can prove the real call executed.
    Missing site/venue/coordinates stay missing; no fake defaults are inserted.
    Rank is admitted only when ``rank_admitted`` is true. Historical priors are
    optional earlier-game evidence, never a current-opponent transplant.
    """

    fn = helper or build_current_contest_row
    contest_list = [dict(item) for item in contests]
    if helper_calls is not None:
        helper_calls.append(
            {
                "symbol": HELPER_SYMBOL,
                "team_key": team_key,
                "executed": True,
            }
        )
    bound = dict(
        fn(
            team_key=team_key,
            contests=contest_list,
            historical_priors=dict(historical_priors or {}),
            current_conference=current_conference,
            current_subdivision=current_subdivision,
            current_rank=current_rank,
            rank_admitted=rank_admitted,
            official_2026_finals_known_before_cutoff=official_2026_finals_known_before_cutoff,
            trust_gate_open=trust_gate_open,
        )
    )
    if bound.get("copied_from_terminal_historical_row") is True:
        raise CurrentContestCheckpointBindingError(
            "terminal historical row transplant is forbidden"
        )
    opponent = bound.get("opponent_key")
    if (
        terminal_historical_opponent
        and opponent
        and str(terminal_historical_opponent) != str(opponent)
    ):
        bound["row_state"] = "ABSTAIN_STALE_HISTORICAL_CURRENT_FIELDS"
        bound["stale_historical_opponent_rejected"] = str(terminal_historical_opponent)
    bound["site"] = site
    bound["venue"] = venue
    bound["coordinates"] = None if coordinates is None else list(coordinates)
    bound["fake_site_or_venue_default"] = False
    bound["missingness_is_not_availability"] = True
    bound["rank_admitted"] = bool(rank_admitted and bound.get("rank") is not None)
    if not rank_admitted:
        bound["rank"] = None
    bound.update(
        issuance_for_row(kicked_off=kicked_off, trust_gate_open=trust_gate_open)
    )
    bound["helper_symbol"] = HELPER_SYMBOL
    bound["consumed_by_cycle27_remaining_checkpoint_binder"] = True
    bound["consumed_by_c26_week1_materializer"] = False
    return bound


def bind_contest(
    contest: Mapping[str, Any],
    *,
    now_utc: datetime,
    trust_gate_open: bool = False,
    helper: BindFn | None = None,
    helper_calls: list[dict[str, Any]] | None = None,
    historical_priors: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contest_id = str(contest.get("contest_id") or "").strip()
    home = str(contest.get("home_team_key") or "").strip()
    away = str(contest.get("away_team_key") or "").strip()
    if not contest_id or not home or not away:
        raise CurrentContestCheckpointBindingError(
            "contest requires contest_id, home_team_key, and away_team_key"
        )
    kickoff = contest.get("kickoff_bound_utc")
    kicked_off = False
    if isinstance(kickoff, str) and kickoff:
        kicked_off = datetime.fromisoformat(kickoff.replace("Z", "+00:00")) <= now_utc
    contests = [dict(contest)]
    home_row = bind_team_for_checkpoint(
        team_key=home,
        contests=contests,
        current_conference=contest.get("home_conference"),
        current_subdivision=contest.get("home_subdivision"),
        trust_gate_open=trust_gate_open,
        kicked_off=kicked_off,
        helper=helper,
        helper_calls=helper_calls,
        historical_priors=historical_priors,
        site=contest.get("site"),
        venue=contest.get("venue"),
    )
    away_row = bind_team_for_checkpoint(
        team_key=away,
        contests=contests,
        current_conference=contest.get("away_conference"),
        current_subdivision=contest.get("away_subdivision"),
        trust_gate_open=trust_gate_open,
        kicked_off=kicked_off,
        helper=helper,
        helper_calls=helper_calls,
        historical_priors=historical_priors,
        site=contest.get("site"),
        venue=contest.get("venue"),
    )
    return {
        "contest_id": contest_id,
        "kickoff_bound_utc": kickoff,
        "kicked_off_at_bind": kicked_off,
        "home": home_row,
        "away": away_row,
        "copied_from_terminal_historical_row": False,
        "new_forecast_frozen": False,
        "publication_label": SHADOW_CLASSIFICATION,
    }


def build_binding(
    *,
    contests: Sequence[Mapping[str, Any]],
    now_utc: datetime,
    trust_gate_open: bool = False,
    helper: BindFn | None = None,
    historical_priors: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    helper_calls: list[dict[str, Any]] = []
    bound_rows = []
    for contest in contests:
        if contest.get("orientation_abstained"):
            bound_rows.append(
                {
                    "contest_id": contest.get("contest_id"),
                    "site": "NEUTRAL",
                    "listed_home_authority": contest.get("listed_home_authority"),
                    "kicked_off_at_bind": False,
                    "new_forecast_frozen": False,
                    "publication_label": SHADOW_CLASSIFICATION,
                    "forecast_issuance": "ABSTAIN_NEUTRAL_LISTED_HOME_UNKNOWN",
                    "copied_from_terminal_historical_row": False,
                }
            )
            continue
        bound_rows.append(
            bind_contest(
                contest,
                now_utc=now_utc,
                trust_gate_open=trust_gate_open,
                helper=helper,
                helper_calls=helper_calls,
                historical_priors=historical_priors,
            )
        )
    if not helper_calls:
        raise CurrentContestCheckpointBindingError(
            "current-contest helper was never executed"
        )
    payload = {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "jira_key": JIRA_KEY,
        "parent_jira_key": PARENT_JIRA_KEY,
        "local_issue_id": LOCAL_ISSUE_ID,
        "issued_at_utc": utc_now_label(now_utc),
        "publication_label": SHADOW_CLASSIFICATION,
        "scientific_trust_gate_open": trust_gate_open,
        "c26_week1_materializer_still_copies_c24": True,
        "c26_gate_identity_preserved": C26_GATE_IDENTITY,
        "c26_dataset_identity_preserved": C26_DATASET_IDENTITY,
        "helper_module": (
            "src/aggie_analytics/data/week1_2026_current_contest_binding_successor.py"
        ),
        "helper_symbol": HELPER_SYMBOL,
        "helper_call_count": len(helper_calls),
        "helper_was_executed": True,
        "contest_count": len(bound_rows),
        "new_forecast_frozen_count": 0,
        "focus_contest_id": FOCUS_CONTEST_ID,
        "friday_t90_contest_id": FRIDAY_T90_CONTEST_ID,
        "contests": bound_rows,
        "no_new_cold_start_average_invented": True,
        "no_fake_site_or_venue_defaults": True,
        "no_terminal_historical_transplant": True,
        "r26_22_status": "BLOCKED",
        "primary_trust_recovery": "PRIMARY_TRUST_RECOVERY_INCOMPLETE",
    }
    payload["binding_identity"] = sha256_bytes(
        canonical_json_bytes(
            {key: value for key, value in payload.items() if key != "binding_identity"}
        )
    )
    return payload


def materialize(
    *,
    repo_root: Path,
    census: Mapping[str, Any],
    now_utc: datetime,
    trust_gate_open: bool = False,
) -> dict[str, Any]:
    rows = (
        census.get("team_seasons")
        or census.get("team_contest_universe")
        or census.get("team_contest_rows")
        or []
    )
    if not isinstance(rows, list):
        raise CurrentContestCheckpointBindingError("census team-contest rows missing")
    contests = contests_from_census_rows(rows)
    kickoffs = {
        str(item.get("ncaa_contest_id")): item.get("kickoff_bound_utc")
        for item in (census.get("contest_kickoffs") or [])
        if isinstance(item, Mapping)
    }
    ledger_path = (
        repo_root
        / "artifacts/scientific_integrity/cycle27/CYCLE27_CONTEST_CHECKPOINT_LEDGER.json"
    )
    if ledger_path.is_file():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        for item in ledger.get("contests") or []:
            kickoffs[str(item.get("ncaa_contest_id"))] = item.get("kickoff_bound_utc")
    for contest in contests:
        contest["kickoff_bound_utc"] = kickoffs.get(str(contest["contest_id"]))
    payload = build_binding(
        contests=contests,
        now_utc=now_utc,
        trust_gate_open=trust_gate_open,
    )
    path = repo_root / GATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload
