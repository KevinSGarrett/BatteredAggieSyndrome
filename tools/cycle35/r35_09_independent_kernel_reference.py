"""R35-09: an independent, row-level reference for the 13,280 kernel rows.

Count agreement is not feature correctness. The Cycle #34 reconciliation
matched totals and game identities; this recomputes every `pit_prior_*`
VALUE from the raw game rows, using an implementation written from the
documented semantics rather than by importing the producer's accumulator,
and compares field by field at row grain.

What it checks, per (game, team):

* the prior set -- every completed game involving that team that started
  strictly before the target game's kickoff, so the target game itself and
  anything later cannot leak in;
* the eight emitted feature values, recomputed from those priors;
* game-pair coherence -- the home row and the away row of one contest must
  agree about the contest;
* the target-exclusion invariant, asserted from observed sets rather than
  from a producer flag.

Where the reference disagrees with the stored row, the disagreement is
reported with both values and a classified reason. Disagreement is not
automatically a producer defect: the producer deliberately defers priors
whose publication authority does not validate, so a stored value BELOW the
reference is the expected shape of that policy, while a stored value ABOVE
the reference would mean the producer saw something this reference cannot
justify from the raw data. The two directions are counted separately
because they mean opposite things.

This tool cannot and does not establish PIT. It establishes whether the
stored features are arithmetically reconstructible from the declared raw
inputs. Publication-time authority is a separate question, answered by the
feasibility table in `r35_09_pit_feasibility.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUTS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
KERNEL_ROWS = OUTPUTS / "PIT_KERNEL_ROWS.jsonl"
GAME_SOURCES = (
    OUTPUTS / "CFBD_GAMES_1963_2012.jsonl",
    OUTPUTS / "CFBD_GAMES_TRANCHE.jsonl",
    OUTPUTS / "CFBD_FCS_FCS_GAMES_1963_2012.jsonl",
    OUTPUTS / "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl",
)

TEAM_PREFIX = "SRC-002:TEAM:"
GAME_PREFIX = "SRC-002:GAME:"

#: The 2013-2022 kernel rows are NOT reconstructible from the public
#: `cycle30_work/outputs` game files -- their game identities appear nowhere
#: under ops/ except in the kernel artifact itself. They derive from the
#: private BAT-523 payloads, where the same identifiers appear as
#: `source_game_id`. The private lane is therefore a required input for any
#: honest reconstruction of the 8,216-row selected subset, and its absence
#: is itself a reportable provenance fact rather than a silent gap.
PRIVATE_PIT_STATE = Path(
    r"C:\BatteredAggieSyndrome.data\pit_state\historical_known_at\sha256"
    r"\cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
)
PRIVATE_OBSERVATIONS = PRIVATE_PIT_STATE / "team_outcome_observations.parquet"
CANONICAL_REGISTRY_GLOB = (
    r"C:\BatteredAggieSyndrome.data\canonical\BAT-387\sha256\*"
    r"\canonical_core_registry.csv"
)

FEATURE_FIELDS = (
    "pit_prior_games_played",
    "pit_prior_margin_mean",
    "pit_prior_points_against_mean",
    "pit_prior_points_for_mean",
    "pit_prior_season_win_rate",
    "pit_prior_win_rate",
    "pit_season_to_date_games",
    "pit_season_to_date_win_rate",
)

TOLERANCE = 1e-9

#: The producer's own declared estimand is
#: "2013-2023_FBS_FBS_BINARY_WIN_WITH_2006_2023_IN_WINDOW_PRIORS"
#: (PIT_KERNEL_POPULATION_MANIFEST.json), i.e. priors are restricted to
#: seasons from 2006 onward. An independent reference tests whether the
#: stored values are reconstructible under the DECLARED contract; using an
#: unbounded prior window instead would only prove that a different contract
#: yields different numbers, which is not a finding about this artifact.
PRIOR_WINDOW_FIRST_SEASON = 2006


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_start(text: Any) -> datetime | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _ratio(numerator: float, denominator: float) -> float | None:
    """Undefined over an empty prior set. Zero would be a fabricated value."""

    if not denominator:
        return None
    return numerator / denominator


def build_team_history() -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Per-team, chronologically ordered completed-game observations."""

    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_game: dict[str, dict[str, Any]] = {}
    # game_id -> why it was excluded. A kernel row whose game is missing is a
    # different finding depending on whether the raw sources never carried the
    # game at all or carried it and the loader filtered it out.
    filtered: dict[str, str] = {}
    stats = {"source_rows": 0, "usable_rows": 0, "sources": [], "skipped": Counter()}
    for source in GAME_SOURCES:
        rows = read_jsonl(source)
        stats["sources"].append(
            {
                "path": str(source),
                "exists": source.is_file(),
                "rows": len(rows),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest()
                if source.is_file()
                else None,
            }
        )
        for row in rows:
            stats["source_rows"] += 1
            start = parse_start(row.get("startDate"))
            if start is None:
                stats["skipped"]["UNPARSEABLE_START"] += 1
                filtered.setdefault(GAME_PREFIX + str(row.get("id")), "UNPARSEABLE_START")
                continue
            if not row.get("completed"):
                stats["skipped"]["NOT_COMPLETED"] += 1
                filtered.setdefault(GAME_PREFIX + str(row.get("id")), "NOT_COMPLETED")
                continue
            home_points = row.get("homePoints")
            away_points = row.get("awayPoints")
            if not isinstance(home_points, int) or not isinstance(away_points, int):
                stats["skipped"]["NON_INTEGER_SCORES"] += 1
                filtered.setdefault(GAME_PREFIX + str(row.get("id")), "NON_INTEGER_SCORES")
                continue
            game_id = GAME_PREFIX + str(row.get("id"))
            if game_id in by_game:
                stats["skipped"]["DUPLICATE_GAME_ID"] += 1
                continue
            season = int(row.get("season"))
            home_id = TEAM_PREFIX + str(row.get("homeId"))
            away_id = TEAM_PREFIX + str(row.get("awayId"))
            by_game[game_id] = {
                "game_id": game_id,
                "start": start,
                "season": season,
                "home_team": home_id,
                "away_team": away_id,
                "home_points": home_points,
                "away_points": away_points,
            }
            tie = home_points == away_points
            for team, points_for, points_against in (
                (home_id, home_points, away_points),
                (away_id, away_points, home_points),
            ):
                history[team].append(
                    {
                        "game_id": game_id,
                        "start": start,
                        "season": season,
                        "points_for": points_for,
                        "points_against": points_against,
                        "margin": points_for - points_against,
                        "tie": tie,
                        "won": (not tie) and points_for > points_against,
                    }
                )
            stats["usable_rows"] += 1
    for team in history:
        history[team].sort(key=lambda item: (item["start"], item["game_id"]))
    stats["skipped"] = dict(stats["skipped"])
    stats["distinct_teams"] = len(history)
    stats["distinct_games"] = len(by_game)
    return history, {"stats": stats, "by_game": by_game, "filtered": filtered}



def load_team_crosswalk() -> tuple[dict[str, str], dict[str, Any]]:
    """`team_<hash>` -> `SRC-002:TEAM:<id>`, from the canonical registry.

    A hash that maps to more than one source key is dropped rather than
    guessed; an ambiguous identity is not an identity.
    """

    import csv
    import glob as _glob

    paths = sorted(_glob.glob(CANONICAL_REGISTRY_GLOB))
    if not paths:
        return {}, {"registry_found": False, "mappings": 0, "ambiguous": 0}
    candidates: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        with open(path, encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("entity_type") != "team":
                    continue
                canonical = str(row.get("canonical_id") or "")
                source_key = str(row.get("source_entity_key") or "").strip()
                if not canonical.startswith("team_") or not source_key:
                    continue
                if str(row.get("source_system_id") or "") != "SRC-002":
                    continue
                candidates[canonical].add(TEAM_PREFIX + source_key)
    mapping = {k: next(iter(v)) for k, v in candidates.items() if len(v) == 1}
    return mapping, {
        "registry_found": True,
        "registry_paths": paths,
        "mappings": len(mapping),
        "ambiguous": sum(1 for v in candidates.values() if len(v) > 1),
    }


def load_private_observations(
    crosswalk: dict[str, str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Team-game observations from the mounted private BAT-523 payload."""

    stats: dict[str, Any] = {
        "path": str(PRIVATE_OBSERVATIONS),
        "mounted": PRIVATE_OBSERVATIONS.is_file(),
        "rows": 0,
        "unmapped_team_ids": 0,
        "unparseable_starts": 0,
    }
    if not PRIVATE_OBSERVATIONS.is_file():
        stats["state"] = "PRIVATE_PAYLOAD_NOT_MOUNTED"
        return [], stats
    try:
        import polars as pl
    except ImportError:
        stats["state"] = "POLARS_UNAVAILABLE"
        return [], stats
    frame = pl.read_parquet(PRIVATE_OBSERVATIONS)
    stats["rows"] = frame.height
    stats["sha256"] = hashlib.sha256(PRIVATE_OBSERVATIONS.read_bytes()).hexdigest()
    stats["seasons"] = sorted({int(v) for v in frame["season"].to_list()})
    out: list[dict[str, Any]] = []
    for row in frame.iter_rows(named=True):
        team = crosswalk.get(str(row.get("team_id") or ""))
        if team is None:
            stats["unmapped_team_ids"] += 1
            continue
        start = parse_start(row.get("game_start_utc"))
        if start is None:
            stats["unparseable_starts"] += 1
            continue
        points_for = row.get("points_for")
        points_against = row.get("points_against")
        if not isinstance(points_for, int) or not isinstance(points_against, int):
            continue
        tie = points_for == points_against
        out.append(
            {
                "team": team,
                "game_id": GAME_PREFIX + str(row.get("source_game_id")),
                "start": start,
                "season": int(row.get("season")),
                "points_for": points_for,
                "points_against": points_against,
                "margin": points_for - points_against,
                "tie": tie,
                "won": (not tie) and points_for > points_against,
            }
        )
    stats["state"] = "PRIVATE_PAYLOAD_INGESTED"
    stats["usable_observations"] = len(out)
    return out, stats


def reference_features(
    priors: list[dict[str, Any]], season: int
) -> dict[str, Any]:
    """Recompute the eight emitted values from an explicit prior set."""

    games = len(priors)
    wins = sum(1 for item in priors if item["won"])
    points_for = sum(item["points_for"] for item in priors)
    points_against = sum(item["points_against"] for item in priors)
    margin = sum(item["margin"] for item in priors)
    previous = [item for item in priors if item["season"] == season - 1]
    current = [item for item in priors if item["season"] == season]
    return {
        "pit_prior_games_played": games,
        "pit_prior_margin_mean": _ratio(margin, games),
        "pit_prior_points_against_mean": _ratio(points_against, games),
        "pit_prior_points_for_mean": _ratio(points_for, games),
        "pit_prior_season_win_rate": _ratio(
            sum(1 for item in previous if item["won"]), len(previous)
        ),
        "pit_prior_win_rate": _ratio(wins, games),
        "pit_season_to_date_games": len(current),
        "pit_season_to_date_win_rate": _ratio(
            sum(1 for item in current if item["won"]), len(current)
        ),
    }


def values_agree(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    try:
        return abs(float(left) - float(right)) <= TOLERANCE
    except (TypeError, ValueError):
        return left == right


def _delta_summary(deltas: list[int]) -> dict[str, Any]:
    """How far apart the reference and the stored priors actually are.

    "Disagrees" is a weak statement on its own: a one-game difference and a
    five-hundred-game difference mean completely different things about
    whether the artifact is reconstructible. The distribution is what makes
    the residual interpretable.
    """

    if not deltas:
        return {"count": 0}
    ordered = sorted(deltas)
    buckets: Counter = Counter()
    for value in deltas:
        if value == 0:
            buckets["exact"] += 1
        elif abs(value) <= 5:
            buckets["within_5"] += 1
        elif abs(value) <= 20:
            buckets["within_20"] += 1
        elif abs(value) <= 100:
            buckets["within_100"] += 1
        else:
            buckets["over_100"] += 1
    return {
        "count": len(deltas),
        "min": ordered[0],
        "median": ordered[len(ordered) // 2],
        "max": ordered[-1],
        "mean": sum(deltas) / len(deltas),
        "buckets": dict(buckets),
        "interpretation": (
            "A positive delta means the independent reference admitted MORE "
            "priors than the producer stored, which is the expected shape of "
            "the producer's authority-deferral policy: priors whose "
            "publication authority does not validate are held back. That "
            "policy's per-prior receipts are not present in the artifact, so "
            "the residual is precisely the part that cannot be independently "
            "verified. A negative delta would be the opposite and more "
            "serious problem -- the producer counting priors the declared "
            "inputs do not justify."
        ),
    }


def residual_disposition(
    comparison: dict[str, Any], by_game: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Give each residual a definite disposition instead of a count.

    Both residuals turn out to be the same acquisition gap seen from two
    sides, and saying so requires checking what the declared sources actually
    cover rather than asserting it.
    """

    acquired_seasons = {
        int(game["season"]) for game in by_game.values() if game.get("season")
    }

    absent_by_disposition: Counter = Counter()
    for row in comparison.get("absent_game_rows", []):
        season = int(row.get("season") or 0)
        row["disposition"] = (
            "SEASON_NOT_ACQUIRED_AT_ALL"
            if season not in acquired_seasons
            else "SEASON_ACQUIRED_BUT_THIS_GAME_IS_NOT_IN_THE_PULL"
        )
        absent_by_disposition[row["disposition"]] += 1

    unjustified_by_disposition: Counter = Counter()
    for row in comparison.get("unjustified_rows", []):
        season = int(row.get("season") or 0)
        # A row's priors reach back through earlier seasons, so a season
        # missing from the declared sources between the last acquired one and
        # this row is exactly what would let the producer count priors this
        # reference cannot see.
        missing_before = sorted(
            year
            for year in range(min(acquired_seasons, default=season), season)
            if year not in acquired_seasons
        )
        row["seasons_missing_from_declared_sources_before_this_row"] = missing_before
        row["disposition"] = (
            "EXPLAINED_BY_UNACQUIRED_PRIOR_SEASONS"
            if missing_before
            else "UNEXPLAINED_PRODUCER_COUNTED_PRIORS_THE_RAW_DATA_DOES_NOT_SUPPLY"
        )
        unjustified_by_disposition[row["disposition"]] += 1

    return {
        "declared_source_seasons": sorted(acquired_seasons),
        "seasons_missing_from_declared_sources": sorted(
            year
            for year in range(
                min(acquired_seasons, default=0), max(acquired_seasons, default=0) + 1
            )
            if year not in acquired_seasons
        ),
        "absent_game_rows_by_disposition": dict(absent_by_disposition),
        "unjustified_rows_by_disposition": dict(unjustified_by_disposition),
        "every_residual_has_a_disposition": (
            sum(absent_by_disposition.values())
            == len(comparison.get("absent_game_rows", []))
            and sum(unjustified_by_disposition.values())
            == len(comparison.get("unjustified_rows", []))
        ),
        "reading": (
            "Both residuals are the same acquisition gap seen from two sides. "
            "Rows whose own game was never pulled cannot be compared at all; "
            "rows whose PRIOR seasons were never pulled show a stored prior "
            "count above what this reference can justify. Neither is an "
            "implementation gap, and neither is evidence of a producer defect "
            "-- but nor is either resolved, because the missing games are "
            "genuinely not in the declared sources."
        ),
    }


def compare(
    kernel: list[dict[str, Any]],
    history: dict[str, list[dict[str, Any]]],
    by_game: dict[str, dict[str, Any]],
    filtered: dict[str, str] | None = None,
) -> dict[str, Any]:
    field_agreement: Counter = Counter()
    field_disagreement: Counter = Counter()
    direction: Counter = Counter()
    row_states: Counter = Counter()
    disagreement_examples: list[dict[str, Any]] = []
    target_leaks: list[dict[str, Any]] = []
    pair_incoherence: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    prior_deltas: list[int] = []
    # Both residuals are inventoried in full, not sampled. Fifteen rows the
    # reference cannot justify is a short list; leaving it as a count is what
    # made it look like a rounding error instead of an open question.
    unjustified_rows: list[dict[str, Any]] = []
    absent_game_rows: list[dict[str, Any]] = []
    absent_reasons: Counter = Counter()
    filtered = filtered or {}

    seen_pairs: dict[str, dict[str, Any]] = {}

    for row in kernel:
        game_id = str(row.get("canonical_game_id"))
        season = int(row.get("season"))
        game = by_game.get(game_id)
        if game is None:
            row_states["GAME_NOT_IN_DECLARED_RAW_SOURCES"] += 1
            reason = filtered.get(
                game_id, "GAME_ID_NEVER_APPEARED_IN_ANY_DECLARED_SOURCE"
            )
            absent_reasons[reason] += 1
            absent_game_rows.append(
                {
                    "canonical_game_id": game_id,
                    "season": season,
                    "team_id": row.get("canonical_team_id"),
                    "reason": reason,
                }
            )
            continue

        # Game-pair coherence: both sides must describe the same contest.
        previous = seen_pairs.get(game_id)
        if previous is None:
            seen_pairs[game_id] = row
        elif (
            previous.get("home_canonical_team_id") != row.get("home_canonical_team_id")
            or previous.get("away_canonical_team_id") != row.get("away_canonical_team_id")
            or previous.get("season") != row.get("season")
            or previous.get("home_win_label") != row.get("home_win_label")
        ):
            pair_incoherence.append({"canonical_game_id": game_id})

        cutoff = game["start"]
        row_state = "COMPARED"
        any_side_compared = False
        for side in ("home", "away"):
            team_id = str(row.get(side + "_canonical_team_id") or "")
            stored = row.get(side + "_features") or {}
            if not team_id or not stored:
                row_states["MISSING_SIDE_FEATURES"] += 1
                continue
            any_side_compared = True
            # MF35-09 (Cycle #35 manager follow-up, 20260920T224700Z): target
            # exclusion was previously tested against `priors`, a list that
            # had ALREADY had `item["game_id"] != game_id` applied in its own
            # construction -- checking whether that same filtered list still
            # contains the target is tautological, since the filter step
            # immediately above it made that structurally impossible. That is
            # "testing target exclusion only on an independently filtered
            # reference," exactly as named: a check that can never fail
            # proves nothing.
            #
            # It cannot be fixed into a genuine per-row producer audit: the
            # target game's own entry in this team's history necessarily has
            # start == cutoff (both are read from the identical raw row), so
            # `start < cutoff` is false for it by construction regardless of
            # which list it is tested against -- there is no independently
            # derived signal in this artifact's schema (no per-row producer-
            # declared prior list) that could show the PRODUCER leaked the
            # target; testing the reference's own re-derived history can only
            # ever validate the reference's own arithmetic, not the producer.
            #
            # What CAN be tested meaningfully here is a real invariant of the
            # UPSTREAM loaders (build_team_history's by_game dedup and the
            # private-observation merge's game_id dedup in main()): the
            # target's game_id must appear in this team's raw history EXACTLY
            # ONCE. A second entry would be a genuine data-integrity defect
            # (e.g. a regression removing one of those dedup guards) and is
            # the one way a leak could actually occur underneath this check.
            raw_team_history = history.get(team_id, [])
            target_entries = [
                item for item in raw_team_history if item["game_id"] == game_id
            ]
            if len(target_entries) > 1:
                target_leaks.append(
                    {
                        "canonical_game_id": game_id,
                        "team_id": team_id,
                        "duplicate_entry_count": len(target_entries),
                        "reason": "DUPLICATE_GAME_ID_IN_TEAM_HISTORY",
                    }
                )
            priors = [
                item
                for item in raw_team_history
                if item["start"] < cutoff
                and item["game_id"] != game_id
                and item["season"] >= PRIOR_WINDOW_FIRST_SEASON
            ]
            expected = reference_features(priors, season)
            row_disagreements: list[dict[str, Any]] = []
            for field in FEATURE_FIELDS:
                if values_agree(stored.get(field), expected[field]):
                    field_agreement[field] += 1
                else:
                    field_disagreement[field] += 1
                    row_disagreements.append(
                        {
                            "field": field,
                            "stored": stored.get(field),
                            "independent_reference": expected[field],
                        }
                    )
            stored_games = stored.get("pit_prior_games_played")
            expected_games = expected["pit_prior_games_played"]
            if isinstance(stored_games, int):
                delta = expected_games - stored_games
                prior_deltas.append(delta)
                if delta > 0:
                    direction["STORED_BELOW_REFERENCE_DEFERRED_PRIORS"] += 1
                elif delta < 0:
                    direction["STORED_ABOVE_REFERENCE_UNJUSTIFIED"] += 1
                    # The direction that cannot be explained by the producer's
                    # authority-deferral policy: the stored row counts priors
                    # the raw data does not supply. Every one is listed.
                    unjustified_rows.append(
                        {
                            "canonical_game_id": game_id,
                            "team_id": team_id,
                            "side": side,
                            "season": season,
                            "cutoff_utc": cutoff.isoformat(),
                            "stored_prior_games": stored_games,
                            "reference_prior_games": expected_games,
                            "excess_priors": -delta,
                        }
                    )
                else:
                    direction["PRIOR_COUNT_EXACT_MATCH"] += 1
            if row_disagreements:
                row_state = "DISAGREES"
                if len(disagreement_examples) < 40:
                    disagreement_examples.append(
                        {
                            "canonical_game_id": game_id,
                            "team_id": team_id,
                            "side": side,
                            "season": season,
                            "cutoff_utc": cutoff.isoformat(),
                            "stored_prior_games": stored_games,
                            "reference_prior_games": expected_games,
                            "fields": row_disagreements,
                        }
                    )
            if len(traces) < 25:
                traces.append(
                    {
                        "canonical_game_id": game_id,
                        "team_id": team_id,
                        "side": side,
                        "target_cutoff_utc": cutoff.isoformat(),
                        "admissible_prior_game_ids": [
                            item["game_id"] for item in priors[-5:]
                        ],
                        "admissible_prior_count": len(priors),
                        "most_recent_prior_start_utc": (
                            priors[-1]["start"].isoformat() if priors else None
                        ),
                        "target_game_excluded_from_priors": all(
                            item["game_id"] != game_id for item in priors
                        ),
                        "every_prior_strictly_before_cutoff": all(
                            item["start"] < cutoff for item in priors
                        ),
                        "reference_features": reference_features(priors, season),
                        "stored_features": stored,
                    }
                )
        # MF35-09: `row_state` was initialized to "COMPARED" and only ever
        # changed to "DISAGREES"; a row whose BOTH sides were missing
        # features never touched either branch and fell through to the
        # unchanged default, so it was counted as "COMPARED" despite zero
        # actual comparisons -- the same absent-comparisons-counted-as-
        # successful pattern as rows_compared's own bug, one level deeper.
        if any_side_compared:
            row_states[row_state] += 1
        else:
            row_states["NO_SIDE_HAD_STORED_FEATURES"] += 1

    # MF35-09 (Cycle #35 manager follow-up, 20260920T224700Z): this
    # previously summed every row_states bucket except MISSING_SIDE_
    # FEATURES, which still counted GAME_NOT_IN_DECLARED_RAW_SOURCES rows
    # as "compared" -- an absent comparison is not a successful one. Only
    # COMPARED and DISAGREES represent a row that actually went through
    # per-side feature reconstruction; every other state is a reason a row
    # was NOT comparable, not a variant of being compared.
    _ACTUALLY_COMPARED_STATES = ("COMPARED", "DISAGREES")
    return {
        "rows_compared": sum(
            row_states.get(state, 0) for state in _ACTUALLY_COMPARED_STATES
        ),
        "rows_not_comparable": sum(
            count for state, count in row_states.items()
            if state not in _ACTUALLY_COMPARED_STATES
        ),
        "row_states": dict(row_states),
        "field_agreement": dict(field_agreement),
        "field_disagreement": dict(field_disagreement),
        "prior_count_direction": dict(direction),
        "prior_count_delta_distribution": _delta_summary(prior_deltas),
        "target_exclusion_violations": target_leaks,
        "target_exclusion_violation_count": len(target_leaks),
        "target_exclusion_check_scope": (
            "This detects a DUPLICATE game_id in a team's own raw history "
            "(an upstream loader regression), not an independent audit of "
            "whether the PRODUCER's stored features leaked the target game. "
            "The kernel artifact carries no per-row producer-declared prior "
            "list, so that stronger claim is not testable from this schema; "
            "the target's own single legitimate history entry necessarily "
            "has start == cutoff by construction and can never itself "
            "trigger this check."
        ),
        "game_pair_incoherence": pair_incoherence,
        "game_pair_incoherence_count": len(pair_incoherence),
        "disagreement_examples": disagreement_examples,
        "unjustified_rows": unjustified_rows,
        "unjustified_row_count": len(unjustified_rows),
        "absent_game_rows": absent_game_rows,
        "absent_game_reasons": dict(absent_reasons),
        "residuals_are_inventoried_in_full": True,
        "deterministic_raw_to_feature_traces": traces,
    }


def authority_audit(kernel: list[dict[str, Any]]) -> dict[str, Any]:
    """Every producer 'proven' label, with what actually backs it."""

    proven = [
        row
        for row in kernel
        if row.get("authority_class") == "PROVEN_PIT_TRAINING_ROW"
        or row.get("row_verdict") == "PROVEN_PIT_TRAINING_ROW"
    ]
    by_season: Counter = Counter(int(row["season"]) for row in proven)
    receipt_bearing = [
        row
        for row in proven
        if any(
            str(key).endswith("receipt_sha256") and row.get(key)
            for key in row
        )
    ]
    return {
        "proven_label_count": len(proven),
        "proven_by_season": dict(by_season),
        "proven_rows_carrying_a_receipt_field": len(receipt_bearing),
        "proven_row_game_ids": sorted(
            {str(row.get("canonical_game_id")) for row in proven}
        ),
        "finding": (
            "The PROVEN_PIT_TRAINING_ROW label is carried on the row without "
            "a per-row publication receipt in this artifact. Every one of "
            "these rows therefore requires receipt-level disposition before "
            "any of them may be treated as independently proven PIT; the "
            "label alone is a producer assertion, not evidence."
        ),
        "independent_pit_proof_count": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    kernel = read_jsonl(KERNEL_ROWS)
    history, extra = build_team_history()
    crosswalk, crosswalk_stats = load_team_crosswalk()
    private_rows, private_stats = load_private_observations(crosswalk)
    by_game = extra["by_game"]
    # Merge WITHOUT double counting. The private payload's `source_game_id`
    # is the same identifier the public files use, so for overlapping
    # seasons the two sources describe the same contest; appending both
    # would inflate every prior count and manufacture disagreement that is
    # an artifact of this tool rather than of the data.
    merged_private = 0
    duplicate_private = 0
    for item in private_rows:
        team_rows = history[item["team"]]
        if any(existing["game_id"] == item["game_id"] for existing in team_rows):
            duplicate_private += 1
            continue
        team_rows.append(item)
        merged_private += 1
        by_game.setdefault(
            item["game_id"],
            {
                "game_id": item["game_id"],
                "start": item["start"],
                "season": item["season"],
                "home_team": None,
                "away_team": None,
            },
        )
    private_stats["merged_new_observations"] = merged_private
    private_stats["already_present_in_public_sources"] = duplicate_private
    for team in history:
        history[team].sort(key=lambda row: (row["start"], row["game_id"]))
    comparison = compare(kernel, history, by_game, extra.get("filtered"))
    comparison["residual_disposition"] = residual_disposition(comparison, by_game)
    authority = authority_audit(kernel)

    result = {
        "artifact_type": "CYCLE35_R35_09_INDEPENDENT_KERNEL_REFERENCE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "kernel_source": {
            "path": str(KERNEL_ROWS),
            "rows": len(kernel),
            "sha256": hashlib.sha256(KERNEL_ROWS.read_bytes()).hexdigest()
            if KERNEL_ROWS.is_file()
            else None,
        },
        "raw_game_sources": extra["stats"],
        "team_crosswalk": crosswalk_stats,
        "private_bat523_observations": private_stats,
        "comparison": comparison,
        "producer_authority_labels": authority,
        "reference_is_independently_implemented": True,
        "count_agreement_is_not_feature_correctness": True,
        "this_tool_does_not_establish_pit": True,
        "pit_admitted": False,
    }
    (out_dir / "R35_09_INDEPENDENT_KERNEL_REFERENCE.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "kernel_rows": len(kernel),
            "row_states": comparison["row_states"],
            "field_disagreement": comparison["field_disagreement"],
            "prior_count_direction": comparison["prior_count_direction"],
            "target_exclusion_violations": comparison["target_exclusion_violation_count"],
            "game_pair_incoherence": comparison["game_pair_incoherence_count"],
            "proven_labels": authority["proven_label_count"],
            "independent_pit_proof_count": authority["independent_pit_proof_count"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
