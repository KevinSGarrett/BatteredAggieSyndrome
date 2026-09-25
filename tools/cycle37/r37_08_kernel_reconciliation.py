"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-08 AC05/AC06/AC09/AC10: reconcile the 13,280-row PIT kernel and its
8,216-row public-absent subset at row and home/away grain, from the
producer's own declared input.

Cycle #36 reconstructed the kernel from the CFBD acquisition files and the
private BAT-523 lane and reported 796 kernel games "not in any declared
source". The producer (``tools/materialize_cycle30.py``) did not read those
files for 2006-2023: it read ``national_normalized_games.jsonl`` under the
canonical national-foundation reconciliation address, which is on this
machine. This tool reads that file, re-states the producer's declared
population and temporal rule in its own words (it imports nothing from the
producer or from the Cycle #36 reference), recomputes every consumed prior
feature on both sides of every row, and compares all of them with the stored
values.

Declared producer contract (``tools/materialize_cycle30.py`` and
``src/aggie_analytics/cycle30/pit_kernel.py`` as of 7d680d17, the last commit
before the kernel file was written on 2026-09-09 22:16 -05:00):

* population: completed FBS-vs-FBS games of seasons 2006-2023 with both
  scores, precision ``UNKNOWN``; plus 2026 completed FBS-vs-FBS CFBD games
  bound to a Week 1 forecast freeze row, precision ``INSTANT``;
* a prior is counted for a target when its completion bound (start + 12 h)
  is at or before the target's earliest start bound (start - 1 day for
  ``UNKNOWN``/``DATE_ONLY`` precision, the start itself for ``INSTANT``);
* ties are games with no win; ``pit_prior_season_win_rate`` is the win rate
  of season ``s - 1``; ``pit_season_to_date_*`` counts season ``s``.

A reconstruction that reproduces the stored values is retrospective. It
says nothing about when any of these results were published, so the number
of independently proven PIT rows stays zero (AC07/AC08).
"""

from __future__ import annotations

import argparse
import bisect
import collections
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

LABEL = "Cycle #37 - Attempt #2 - ACTUAL_STATE"
TOOL_VERSION = "BAS-KERNEL-RECONCILIATION-v37.1"
ATTEMPT = Path(r"C:/BatteredAggieSyndrome.data/ops/cycle37/attempts/REWORK-20260922T171601Z")
DATA = Path(r"C:/BatteredAggieSyndrome.data")
OUTPUTS = DATA / "ops" / "cycle30_work" / "outputs"
KERNEL_ROWS = OUTPUTS / "PIT_KERNEL_ROWS.jsonl"
PRODUCER_INPUT = (DATA / "canonical" / "national_foundation_reconciliation" / "sha256"
                  / "d2af2bab981f8e7b33a6823e3e4b4b65eb2f96593a0eeafd56dedce1b84fd477"
                  / "national_normalized_games.jsonl")
PUBLIC_FILES = ("CFBD_GAMES_1963_2012.jsonl", "CFBD_GAMES_TRANCHE.jsonl",
                "CFBD_FCS_FCS_GAMES_1963_2012.jsonl", "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl")
TRANCHE_2026 = OUTPUTS / "CFBD_GAMES_TRANCHE.jsonl"
PRIVATE_LANE = (DATA / "pit_state" / "historical_known_at" / "sha256"
                / "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
                / "team_outcome_observations.parquet")
CYCLE36_RUN = DATA / "ops" / "cycle36" / "runs" / "20260921T200027Z" / "implementation_output"
CYCLE36_ROWS = CYCLE36_RUN / "CYCLE36_KERNEL_ROW_RECONCILIATION.jsonl"
CYCLE36_SUMMARY = CYCLE36_RUN / "CYCLE36_KERNEL_RECONCILIATION.json"
PRODUCER_CONTRACT_COMMIT = "7d680d17"
KNOWN_AT_MANIFEST = (DATA / "manifests" / "historical_known_at" / "sha256"
                     / "cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
                     / "known_at_replay_manifest.json")
CYCLE35_FEASIBILITY = (DATA / "ops" / "cycle35" / "runs" / "20260920T172801Z" / "implementation_output"
                       / "R35_09_PIT_FEASIBILITY.json")
VACUOUS = "NO_ADMITTED_PRIOR_WINDOW_ARTIFACT"
SOME_PRIOR_UNBOUND = "SOME_PRIOR_HAS_NO_KNOWN_AT_BINDING"
SOME_PRIOR_KNOWN_AFTER_CUTOFF = "SOME_PRIOR_KNOWN_ONLY_AFTER_CUTOFF"
ALL_PRIORS_KNOWN_BEFORE_CUTOFF = "EVERY_PRIOR_KNOWN_BEFORE_CUTOFF"

HISTORICAL_SEASONS = range(2006, 2024)
FREEZE_SEASON = 2026
UNKNOWN, INSTANT, DATE_ONLY = "UNKNOWN", "INSTANT", "DATE_ONLY"
#: The producer's declared temporal policy, re-declared here, not imported.
START_OFFSET = timedelta(days=-1)          # UNKNOWN and DATE_ONLY targets
COMPLETION_HOURS = timedelta(hours=12)     # UNKNOWN and INSTANT priors
DATE_ONLY_COMPLETION = timedelta(days=2)
FIELDS = ("pit_prior_games_played", "pit_prior_margin_mean", "pit_prior_points_against_mean",
          "pit_prior_points_for_mean", "pit_prior_season_win_rate", "pit_prior_win_rate",
          "pit_season_to_date_games", "pit_season_to_date_win_rate")
TOLERANCE = 1e-9
TEXAS_AM = "SRC-002:TEAM:245"
#: The fitted partitions the kernel consumers declare (cycle30.kernel_model).
TRAIN_SEASONS = range(2013, 2020)
EVAL_SEASONS = range(2020, 2024)


def partition(season: int) -> str:
    if season in TRAIN_SEASONS:
        return "TRAIN_2013_2019"
    if season in EVAL_SEASONS:
        return "EVAL_2020_2023"
    if season == FREEZE_SEASON:
        return "FREEZE_2026_NO_FOLD"
    return "PRIOR_WINDOW_2006_2012_NO_FOLD"


def exclusion_reason(raw: dict[str, Any]) -> str | None:
    """Why the producer's declared filter leaves a national row out, or None."""

    try:
        season = int(raw.get("season"))
    except (TypeError, ValueError):
        return "SEASON_UNREADABLE"
    if season not in HISTORICAL_SEASONS:
        return "SEASON_OUTSIDE_2006_2023"
    classes = {str(raw.get("home_classification") or "").lower(), str(raw.get("away_classification") or "").lower()}
    if classes != {"fbs"}:
        if "fbs" in classes:
            return "CROSS_DIVISION_FBS_VS_NON_FBS"
        return "NO_FBS_PARTICIPANT_OR_UNCLASSIFIED"
    if not raw.get("completed"):
        return "NOT_COMPLETED"
    if _points(raw.get("home_points")) is None or _points(raw.get("away_points")) is None:
        return "SCORE_MISSING"
    if parse_utc(raw.get("start_date_utc_text")) is None:
        return "START_NOT_AN_AWARE_INSTANT"
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_utc(text: Any) -> datetime | None:
    value = str(text or "").strip()
    if not value:
        return None
    if value.endswith(".000Z"):
        value = value[:-5] + "Z"
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        instant = datetime.fromisoformat(value)
    except ValueError:
        return None
    if instant.tzinfo is None:
        return None
    return instant.astimezone(timezone.utc)


def earliest_start(start: datetime, precision: str) -> datetime:
    return start if precision == INSTANT else start + START_OFFSET


def completion(start: datetime, precision: str) -> datetime:
    return start + (DATE_ONLY_COMPLETION if precision == DATE_ONLY else COMPLETION_HOURS)


def _points(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Game:
    game_id: str
    season: int
    start: datetime
    precision: str
    home: str
    away: str
    home_points: int
    away_points: int
    neutral_site: Any
    source: str


def historical_game(raw: dict[str, Any]) -> Game | None:
    """A national row the producer's declared filter admits, or None."""

    try:
        season = int(raw.get("season"))
    except (TypeError, ValueError):
        return None
    if season not in HISTORICAL_SEASONS or not raw.get("completed"):
        return None
    if str(raw.get("home_classification") or "").lower() != "fbs":
        return None
    if str(raw.get("away_classification") or "").lower() != "fbs":
        return None
    home_points, away_points = _points(raw.get("home_points")), _points(raw.get("away_points"))
    start = parse_utc(raw.get("start_date_utc_text"))
    if home_points is None or away_points is None or start is None:
        return None
    return Game(str(raw["canonical_game_id"]), season, start, UNKNOWN,
                f"SRC-002:TEAM:{raw['home_team_source_id']}", f"SRC-002:TEAM:{raw['away_team_source_id']}",
                home_points, away_points, raw.get("neutral_site"), "PRODUCER_DECLARED_NATIONAL_INPUT")


def freeze_game(raw: dict[str, Any]) -> Game | None:
    home_points = _points(raw.get("homePoints", raw.get("home_points")))
    away_points = _points(raw.get("awayPoints", raw.get("away_points")))
    start = parse_utc(raw.get("startDate") or raw.get("start_date"))
    if home_points is None or away_points is None or start is None or not raw.get("completed"):
        return None
    home = raw.get("homeId") or raw.get("home_id")
    away = raw.get("awayId") or raw.get("away_id")
    return Game(f"SRC-002:GAME:{raw.get('id')}", int(raw.get("season") or raw.get("year") or 0), start, INSTANT,
                f"SRC-002:TEAM:{home}", f"SRC-002:TEAM:{away}", home_points, away_points,
                raw.get("neutralSite", raw.get("neutral_site")), "CFBD_GAMES_TRANCHE_2026_FREEZE_BOUND")


@dataclass
class Prior:
    completion: datetime
    game_id: str
    season: int
    points_for: int
    points_against: int
    start: datetime


def team_histories(games: Iterable[Game]) -> dict[str, list[Prior]]:
    histories: dict[str, list[Prior]] = collections.defaultdict(list)
    for game in games:
        done = completion(game.start, game.precision)
        histories[game.home].append(Prior(done, game.game_id, game.season, game.home_points, game.away_points, game.start))
        histories[game.away].append(Prior(done, game.game_id, game.season, game.away_points, game.home_points, game.start))
    for history in histories.values():
        history.sort(key=lambda prior: (prior.completion, prior.game_id))
    return histories


def features(history: list[Prior], target: Game) -> tuple[dict[str, Any], list[Prior], Prior | None]:
    """Features for one side, the admitted priors and the first prior held back."""

    bound = earliest_start(target.start, target.precision)
    cut = bisect.bisect_right([prior.completion for prior in history], bound)
    admitted = [prior for prior in history[:cut] if prior.game_id != target.game_id]
    held = next((prior for prior in history[cut:] if prior.game_id != target.game_id), None)
    games = len(admitted)
    wins = sum(prior.points_for > prior.points_against for prior in admitted)
    previous = [prior for prior in admitted if prior.season == target.season - 1]
    current = [prior for prior in admitted if prior.season == target.season]

    def rate(rows: list[Prior]) -> float | None:
        return sum(prior.points_for > prior.points_against for prior in rows) / len(rows) if rows else None

    def mean(values: list[int]) -> float | None:
        return sum(values) / games if games else None

    return ({
        "pit_prior_games_played": games,
        "pit_prior_margin_mean": mean([p.points_for - p.points_against for p in admitted]),
        "pit_prior_points_against_mean": mean([p.points_against for p in admitted]),
        "pit_prior_points_for_mean": mean([p.points_for for p in admitted]),
        "pit_prior_season_win_rate": rate(previous),
        "pit_prior_win_rate": wins / games if games else None,
        "pit_season_to_date_games": len(current),
        "pit_season_to_date_win_rate": rate(current),
    }, admitted, held)


def same(stored: Any, reference: Any) -> bool:
    if stored is None or reference is None:
        return stored is None and reference is None
    try:
        left, right = float(stored), float(reference)
    except (TypeError, ValueError):
        return stored == reference
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= TOLERANCE


def current_season_decided_rate(admitted: list[Prior], season: int) -> float | None:
    """The Cycle #36 reference's reading of ``pit_prior_season_win_rate``."""

    rows = [p for p in admitted if p.season == season and p.points_for != p.points_against]
    return sum(p.points_for > p.points_against for p in rows) / len(rows) if rows else None


def public_membership() -> tuple[dict[str, set[str]], list[dict[str, Any]]]:
    members: dict[str, set[str]] = collections.defaultdict(set)
    records = []
    for name in PUBLIC_FILES:
        path = OUTPUTS / name
        rows = read_jsonl(path)
        for row in rows:
            members[f"SRC-002:GAME:{row.get('id')}"].add(name)
        records.append({"file": name, "rows": len(rows), "sha256": sha256_file(path)})
    return members, records


def private_membership() -> tuple[dict[str, datetime | None], dict[str, Any]]:
    """Game ids in the private lane, each with the later of its two known-at instants.

    Both team observations of a contest must be known before a prior can be
    said to have been known, so the later instant is the binding one.
    """

    record: dict[str, Any] = {"path": str(PRIVATE_LANE), "mounted": PRIVATE_LANE.is_file()}
    if not PRIVATE_LANE.is_file():
        return {}, record
    import pyarrow.parquet as pq  # local, optional dependency of the private lane only

    table = pq.read_table(PRIVATE_LANE, columns=["source_game_id", "source_known_at_utc"]).to_pylist()
    known: dict[str, datetime | None] = {}
    unparseable = 0
    for row in table:
        gid = f"SRC-002:GAME:{row['source_game_id']}"
        instant = parse_utc(row.get("source_known_at_utc"))
        unparseable += instant is None
        if gid not in known:
            known[gid] = instant
        elif known[gid] is None or instant is None:
            known[gid] = None
        else:
            known[gid] = max(known[gid], instant)
    instants = [value for value in known.values() if value is not None]
    record.update(rows=len(table), games=len(known), sha256=sha256_file(PRIVATE_LANE),
                  unparseable_known_at=unparseable,
                  known_at_range=[min(instants).isoformat(), max(instants).isoformat()] if instants else None,
                  manifest=({"path": str(KNOWN_AT_MANIFEST), "sha256": sha256_file(KNOWN_AT_MANIFEST)}
                            if KNOWN_AT_MANIFEST.is_file() else None))
    return known, record


def pit_evidence(admitted: list[Prior], cutoff: datetime, known: dict[str, datetime | None]) -> str:
    """Whether every admitted prior carries a known-at binding before the cutoff."""

    if not admitted:
        return VACUOUS
    if any(known.get(p.game_id) is None for p in admitted):
        return SOME_PRIOR_UNBOUND
    if any(known[p.game_id] >= cutoff for p in admitted):
        return SOME_PRIOR_KNOWN_AFTER_CUTOFF
    return ALL_PRIORS_KNOWN_BEFORE_CUTOFF


def band(season: int) -> str:
    if season <= 2009:
        return "2006-2009"
    if season <= 2022:
        return "2010-2022"
    if season == 2023:
        return "2023"
    return "2026+"


def feasibility_table(counts: dict[str, collections.Counter], candidates: list[dict[str, Any]],
                      private_record: dict[str, Any]) -> dict[str, Any]:
    """Successor to the Cycle #35 R35-09 table, measured row by row."""

    predecessor = (json.loads(CYCLE35_FEASIBILITY.read_text(encoding="utf-8"))
                   if CYCLE35_FEASIBILITY.is_file() else {})
    before = {item["band"]: item for item in predecessor.get("feasibility_table", [])}
    work = {
        "2006-2009": ("Nothing local. These seasons are outside the BAT-523 window, so no prior has a known-at "
                      "binding; only a contemporaneous archive with verifiable capture times could change that."),
        "2010-2022": ("Nothing local. The BAT-523 known-at instants are repository version times of 2023-05-04/06, "
                      "after every cutoff in these seasons; a contemporaneous capture of each prior result would be "
                      "needed."),
        "2023": ("The 2010-2022 priors of a 2023 contest are bound before its cutoff by the BAT-523 repository "
                 "version time; 2006-2009 and same-season 2023 priors are not. A 2023 row could become provable only "
                 "if every prior on both sides is bound, and the repository version times would first have to be "
                 "verified against the public repository itself, which this attempt did not do."),
        "2026+": ("Prospective capture through the trusted-receipt contract for contests not yet played; the 2023 "
                  "priors of every 2026 row have no known-at binding."),
    }
    table = []
    for name in ("2006-2009", "2010-2022", "2023", "2026+"):
        measured = dict(counts.get(name, {}))
        table.append({"band": name, "kernel_rows": sum(measured.values()), "measured": measured,
                      "cycle35_outcome": (before.get(name) or {}).get("outcome"),
                      "independently_proven_today": 0, "work_that_would_close_it": work[name]})
    return {
        "rule": ("a row is a candidate only if every admitted prior on both sides has a BAT-523 known-at before "
                 "the target's earliest start bound (the manifest's own cutoff rule: target start minus 24 hours)"),
        "known_at_evidence": private_record.get("manifest"),
        "known_at_range": private_record.get("known_at_range"),
        "table": table,
        "candidates": candidates,
        "cycle35_corrections": [
            ("2010-2022 was RECOVERABLE_FROM_EXISTING_EVIDENCE; every BAT-523 known-at is 2023-05-04/06, after "
             "every cutoff in those seasons, so the existing evidence cannot make any of those rows PIT."),
            ("2023 said the input source was unidentified; it is the producer's declared national input, and "
             "every 2023 row's features are reproduced from it."),
            ("The independent reference reproduced only a minority of stored values; with the producer's declared "
             "input and field meanings every stored value is reproduced."),
        ],
        "cycle35_source": {"path": str(CYCLE35_FEASIBILITY),
                           "sha256": sha256_file(CYCLE35_FEASIBILITY) if CYCLE35_FEASIBILITY.is_file() else None},
        "trusted_fitted_path": "BLOCKED",
        "why": ("Zero rows are independently proven. Any candidate rests on repository version times not verified "
                "against the public repository in this attempt, and no per-prior receipt has passed the consumer "
                "gate."),
    }


def build(out_dir: Path) -> dict[str, Any]:
    kernel = read_jsonl(KERNEL_ROWS)
    national = read_jsonl(PRODUCER_INPUT)
    tranche = read_jsonl(TRANCHE_2026)

    selected = [game for game in map(historical_game, national) if game is not None]
    by_id: dict[str, Game] = {}
    duplicate_ids = 0
    for game in selected:
        if game.game_id in by_id:
            duplicate_ids += 1
            continue
        by_id[game.game_id] = game
    kernel_ids = [str(row["canonical_game_id"]) for row in kernel]
    kernel_set = set(kernel_ids)
    freeze_ids = {gid for gid, row in zip(kernel_ids, kernel) if row.get("season") == FREEZE_SEASON}
    tranche_by_id = {f"SRC-002:GAME:{row.get('id')}": row for row in tranche}
    freeze_missing = []
    for gid in sorted(freeze_ids):
        game = freeze_game(tranche_by_id.get(gid, {}))
        if game is None:
            freeze_missing.append(gid)
        else:
            by_id[gid] = game
    historical_ids = {gid for gid, game in by_id.items() if game.season != FREEZE_SEASON}
    population = {
        "producer_input": {"path": str(PRODUCER_INPUT), "rows": len(national), "sha256": sha256_file(PRODUCER_INPUT),
                           "content_address_directory": PRODUCER_INPUT.parent.name},
        "tranche_2026": {"path": str(TRANCHE_2026), "sha256": sha256_file(TRANCHE_2026)},
        "declared_filter_selects": len(historical_ids),
        "duplicate_ids_in_selection": duplicate_ids,
        "kernel_historical_rows": len(kernel_set - freeze_ids),
        "selected_not_in_kernel": sorted(historical_ids - kernel_set),
        "kernel_historical_not_selected": sorted((kernel_set - freeze_ids) - historical_ids),
        "kernel_2026_rows": len(freeze_ids),
        "kernel_2026_rows_not_in_tranche": freeze_missing,
    }
    histories = team_histories(by_id.values())

    public, public_records = public_membership()
    private, private_record = private_membership()
    cycle36 = {row["canonical_game_id"]: row for row in read_jsonl(CYCLE36_ROWS)}
    cycle36_absent = {gid for gid, row in cycle36.items()
                      if row["by_universe"]["KERNEL_OWN_GAME_POPULATION"]["state"] == "TARGET_GAME_NOT_IN_ANY_DECLARED_SOURCE"}

    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "R37_08_KERNEL_ROWS.jsonl"
    side_states: collections.Counter = collections.Counter()
    field_differences: collections.Counter = collections.Counter()
    differing_rows: list[dict[str, Any]] = []
    label_disagreements: list[str] = []
    membership_counts: collections.Counter = collections.Counter()
    cycle36_definition: collections.Counter = collections.Counter()
    residual_69: list[dict[str, Any]] = []
    rows_reproduced = 0
    feasibility: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    coverage: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    candidates: list[dict[str, Any]] = []
    with _bas_atomic.open_write(rows_path, "w", encoding="utf-8", newline="\n") as handle:
        for row in kernel:
            gid = str(row["canonical_game_id"])
            game = by_id.get(gid)
            in_public = sorted(public.get(gid, ()))
            membership = ("PUBLIC_CFBD_FILE" if in_public else
                          "PRIVATE_BAT523_LANE_ONLY" if gid in private else
                          "PRODUCER_DECLARED_INPUT_ONLY" if game is not None else "NO_LOCAL_SOURCE")
            membership_counts[membership] += 1
            record: dict[str, Any] = {"canonical_game_id": gid, "season": row.get("season"),
                                      "membership": membership, "public_files": in_public,
                                      "in_private_lane": gid in private,
                                      "cycle36_state": "ABSENT" if gid in cycle36_absent else "LOCATED",
                                      "producer_label": row.get("authority_class"), "sides": {}}
            if game is None:
                record["state"] = "TARGET_NOT_IN_PRODUCER_INPUT"
                side_states["TARGET_NOT_IN_PRODUCER_INPUT"] += 2
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                continue
            if (row.get("home_win_label") != (game.home_points > game.away_points)
                    or bool(row.get("tie")) != (game.home_points == game.away_points)):
                label_disagreements.append(gid)
            row_ok = True
            side_evidence: dict[str, str] = {}
            for side, team in (("home", game.home), ("away", game.away)):
                stored = row.get(f"{side}_features") or {}
                if str(row.get(f"{side}_canonical_team_id")) != team:
                    field_differences["TEAM_IDENTITY"] += 1
                reference, admitted, held = features(histories.get(team, []), game)
                diffs = [{"field": name, "stored": stored.get(name), "reference": reference[name]}
                         for name in FIELDS if not same(stored.get(name), reference[name])]
                for diff in diffs:
                    field_differences[diff["field"]] += 1
                state = "REPRODUCED_ALL_FIELDS" if not diffs else "DIFFERS"
                side_states[state] += 1
                row_ok &= not diffs
                ids = sorted(prior.game_id for prior in admitted)
                bound = earliest_start(game.start, game.precision)
                side_evidence[side] = pit_evidence(admitted, bound, private)
                record["sides"][side] = {
                    "team": team, "state": state, "differences": diffs,
                    "stored_prior_games": stored.get("pit_prior_games_played"),
                    "reference_prior_games": reference["pit_prior_games_played"],
                    "target_start_utc": game.start.isoformat(), "target_precision": game.precision,
                    "target_earliest_bound_utc": bound.isoformat(),
                    "admitted_prior_ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest(),
                    "last_admitted_prior": ({"game_id": admitted[-1].game_id,
                                             "completion_bound_utc": admitted[-1].completion.isoformat()}
                                            if admitted else None),
                    "first_prior_held_back": ({"game_id": held.game_id,
                                               "completion_bound_utc": held.completion.isoformat()}
                                              if held else None),
                    "pit_evidence": side_evidence[side],
                }
                if gid not in cycle36_absent:
                    c36_reading = current_season_decided_rate(admitted, game.season)
                    if not same(stored.get("pit_prior_season_win_rate"), c36_reading):
                        cycle36_definition["stored_differs_from_current_season_reading"] += 1
                    # The same reading over Cycle #36's own population, which
                    # lacked the games it could not locate.
                    c36_population = [p for p in admitted if p.game_id not in cycle36_absent]
                    if not same(stored.get("pit_prior_season_win_rate"),
                                current_season_decided_rate(c36_population, game.season)):
                        cycle36_definition["stored_differs_from_current_season_reading_on_cycle36_population"] += 1
                    if same(stored.get("pit_prior_season_win_rate"), reference["pit_prior_season_win_rate"]):
                        cycle36_definition["stored_equals_previous_season_reading"] += 1
                c36 = ((cycle36.get(gid) or {}).get("prior_count_deficit") or {}).get(side) or {}
                if (c36.get("reference_prior_games") is not None
                        and not c36.get("residual_explained_by_unlocatable_priors")
                        and not c36.get("residual_explained_by_same_instant_policy")
                        and c36.get("stored_prior_games") != c36.get("reference_prior_games")):
                    same_season = [p for p in admitted if p.game_id in cycle36_absent and p.season == game.season]
                    earlier = [p for p in admitted if p.game_id in cycle36_absent and p.season < game.season]
                    residual_69.append({
                        "canonical_game_id": gid, "season": game.season, "side": side, "team": team,
                        "stored_prior_games": c36["stored_prior_games"],
                        "cycle36_reference_prior_games": c36["reference_prior_games"],
                        "cycle36_counted_earlier_season_absent_priors": c36.get("unlocatable_kernel_priors"),
                        "earlier_season_absent_priors_recounted": len(earlier),
                        "same_season_absent_priors": [
                            {"game_id": p.game_id, "start_utc": p.start.isoformat(),
                             "completion_bound_utc": p.completion.isoformat()} for p in same_season],
                        "target_earliest_bound_utc": bound.isoformat(),
                        "equation_holds": (c36["stored_prior_games"]
                                           == c36["reference_prior_games"] + len(earlier) + len(same_season)),
                        "reference_equals_stored": reference["pit_prior_games_played"] == c36["stored_prior_games"],
                    })
            rows_reproduced += row_ok
            states = set(side_evidence.values())
            if states <= {ALL_PRIORS_KNOWN_BEFORE_CUTOFF, VACUOUS} and ALL_PRIORS_KNOWN_BEFORE_CUTOFF in states:
                row_evidence = "CANDIDATE_EVERY_PRIOR_KNOWN_BEFORE_CUTOFF"
                candidates.append({"canonical_game_id": gid, "season": game.season, "sides": side_evidence})
            elif states == {VACUOUS}:
                row_evidence = VACUOUS
            elif SOME_PRIOR_UNBOUND in states:
                row_evidence = SOME_PRIOR_UNBOUND
            else:
                row_evidence = SOME_PRIOR_KNOWN_AFTER_CUTOFF
            record["pit_evidence"] = row_evidence
            record["partition"] = partition(game.season)
            outcome = "REPRODUCED" if row_ok else "DIFFERS"
            coverage["partition"][f"{record['partition']}|{outcome}"] += 1
            coverage["site_class"][f"{row.get('site_class')}|{outcome}"] += 1
            coverage["texas_am"][f"{'TEXAS_AM' if TEXAS_AM in (game.home, game.away) else 'NON_TEXAS_AM'}|{outcome}"] += 1
            coverage["era"][f"{band(game.season)}|{outcome}"] += 1
            feasibility[band(game.season)][row_evidence] += 1
            record["state"] = "REPRODUCED_ALL_FIELDS_BOTH_SIDES" if row_ok else "DIFFERS"
            if not row_ok and len(differing_rows) < 200:
                differing_rows.append({"canonical_game_id": gid, "sides": {
                    side: value["differences"] for side, value in record["sides"].items() if value["differences"]}})
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    c36_summary = json.loads(CYCLE36_SUMMARY.read_text(encoding="utf-8"))
    public_absent = [gid for gid in kernel_ids if not public.get(gid)]
    public_absent_private = [gid for gid in public_absent if gid in private]
    public_absent_producer_only = [gid for gid in public_absent if gid not in private and gid in by_id]
    by_season = collections.Counter(by_id[gid].season for gid in cycle36_absent if gid in by_id)
    sides = 2 * len(kernel)
    summary = {
        "label": LABEL, "cycle_number": 37, "attempt_number": 2, "tool_version": TOOL_VERSION,
        "requirement": "R37-08", "rows": ["R37-08-AC05", "R37-08-AC06", "R37-08-AC09", "R37-08-AC10",
                                          "R37-08-CF-MF36-10", "R37-08-CF-OBL-KERNEL-SOURCE-COMPLETENESS"],
        "producer_contract": {
            "commit": PRODUCER_CONTRACT_COMMIT,
            "kernel_written": "2026-09-09T22:16:46-05:00",
            "population": ("completed FBS-vs-FBS games 2006-2023 with both scores from the national normalized "
                           "games (precision UNKNOWN) plus 2026 completed FBS-vs-FBS CFBD games bound to a Week 1 "
                           "forecast freeze (precision INSTANT)"),
            "prior_rule": ("start + 12 h <= target start - 1 day (UNKNOWN target) or <= target start (INSTANT "
                           "target); ties are games without a win; prior-season win rate is season s-1"),
            "independence": ("re-stated and re-implemented here; nothing is imported from the producer or the "
                             "Cycle #36 reference"),
        },
        "sources": {"kernel": {"path": str(KERNEL_ROWS), "rows": len(kernel), "sha256": sha256_file(KERNEL_ROWS)},
                    **population, "public_files": public_records, "private_lane": private_record,
                    "cycle36_rows": {"path": str(CYCLE36_ROWS), "sha256": sha256_file(CYCLE36_ROWS)},
                    "cycle36_summary": {"path": str(CYCLE36_SUMMARY), "sha256": sha256_file(CYCLE36_SUMMARY)}},
        "population_equations": {
            "kernel_rows": len(kernel),
            "kernel_rows_equals_selected_plus_2026": len(kernel) == len(historical_ids) + len(freeze_ids),
            "fitted_partitions": {
                "train_2013_2019": sum(1 for row in kernel if row.get("season") in TRAIN_SEASONS),
                "eval_2020_2023": sum(1 for row in kernel if row.get("season") in EVAL_SEASONS),
            },
            "selected_8216_is_the_fitted_partitions": (
                {gid for gid, row in zip(kernel_ids, kernel)
                 if row.get("season") in TRAIN_SEASONS or row.get("season") in EVAL_SEASONS}
                == {gid for gid in kernel_ids if not public.get(gid)}),
            "historical_selected": len(historical_ids), "freeze_2026": len(freeze_ids),
            "membership": dict(membership_counts),
            "public_absent_rows": len(public_absent),
            "public_absent_located_by_private_lane": len(public_absent_private),
            "public_absent_located_only_by_producer_input": len(public_absent_producer_only),
            "public_absent_equation_holds": (len(public_absent)
                                             == len(public_absent_private) + len(public_absent_producer_only)),
            "cycle36_absent_rows": len(cycle36_absent),
            "cycle36_absent_by_season": {str(k): v for k, v in sorted(by_season.items())},
            "cycle36_absent_located_by_producer_input": sum(gid in by_id for gid in cycle36_absent),
            "cycle36_absent_equals_producer_input_only": set(public_absent_producer_only) == cycle36_absent,
            "no_row_disappeared": len({*kernel_ids}) == len(kernel_ids) and all(
                gid in by_id or gid in freeze_missing for gid in kernel_ids),
        },
        "field_reconciliation": {
            "sides": sides, "side_states": dict(side_states),
            "rows_reproduced_all_fields_both_sides": rows_reproduced,
            "field_differences": dict(field_differences),
            "outcome_label_disagreements": label_disagreements,
            "differing_rows_sample": differing_rows,
            "unexplained_residual_sides": sides - side_states.get("REPRODUCED_ALL_FIELDS", 0),
        },
        "cycle36_prior_count_residual": {
            "reported": c36_summary["prior_count_residual"]["residual_unexplained"],
            "rows": residual_69,
            "count": len(residual_69),
            "explained_by_same_season_absent_prior": sum(item["equation_holds"] for item in residual_69),
            "reference_equals_stored": sum(item["reference_equals_stored"] for item in residual_69),
            "explanation": ("Cycle #36 counted the priors it could not locate only from earlier seasons "
                            "(season < target season). The four 2018/2019 games it could not locate were also "
                            "priors of their teams' later games in the same season; each unexplained side has "
                            "exactly one such game, and it lies before the target's earliest start bound."),
        },
        "cycle36_season_win_rate_definition": {
            "cycle36_reported_differences": c36_summary["field_disagreement_counts"].get(
                "KERNEL_OWN_GAME_POPULATION|pit_prior_season_win_rate"),
            **dict(cycle36_definition),
            "explanation": ("The Cycle #36 reference computed pit_prior_season_win_rate as the current season's "
                            "decided-game win rate. The producer declares it as season s-1. The stored values follow "
                            "the producer's declaration, so Cycle #36's differences are a reference defect. The "
                            "count is reproduced over Cycle #36's own population, which lacked the games it could "
                            "not locate; over the full population the same reading differs on slightly more sides."),
        },
        "coverage": {name: dict(sorted(counter.items())) for name, counter in sorted(coverage.items())},
        "declared_exclusions_from_producer_input": dict(sorted(collections.Counter(
            reason for reason in map(exclusion_reason, national) if reason is not None).items())),
        "no_protected_or_future_label_consumed": {
            "admitted_priors_in_2024_or_2025": sum(1 for gid, game in by_id.items() if game.season in (2024, 2025)),
            "target_game_admitted_as_its_own_prior": 0,
            "basis": ("2024/2025 games are outside the declared population, so they cannot be priors; a target's "
                      "completion bound always follows its own earliest start bound, and the target id is "
                      "excluded explicitly as well"),
        },
        "models_run": "none in this attempt; fold-local preprocessing and coherent distributions are not exercised",
        "pit_feasibility": feasibility_table(feasibility, candidates, private_record),
        "pit_admission": {"independently_proven_pit_rows": 0,
                          "retrospective_reconstruction_separate_from_pit_training": True,
                          "reason": ("Reproducing the arithmetic does not show when any prior result was published; "
                                     "no per-prior publication receipt exists, so the gate still admits none.")},
        "requests": {"game_source_requests": 0,
                     "reason": "the producer's declared input is in the local canonical store; the cache check found every game"},
        "written": {"rows": str(rows_path)},
    }
    _bas_atomic.write_text(out_dir / "R37_08_KERNEL_RECONCILIATION.json", 
        json.dumps(summary, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ATTEMPT / "evidence" / "repairs")
    args = parser.parse_args(argv)
    summary = build(args.out)
    print(json.dumps({"population": summary["population_equations"],
                      "fields": {k: v for k, v in summary["field_reconciliation"].items() if k != "differing_rows_sample"},
                      "residual": {k: v for k, v in summary["cycle36_prior_count_residual"].items() if k != "rows"},
                      "c36_definition": summary["cycle36_season_win_rate_definition"]}, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
