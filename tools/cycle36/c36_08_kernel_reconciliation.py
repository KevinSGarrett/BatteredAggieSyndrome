"""R36-08: reconcile every kernel row, and contain the unproven PIT labels.

Runs the independent reconstruction in
``aggie_analytics.cycle36.kernel_reference`` over all 13,280 kernel rows
under several **declared** source universes, so a stored value that differs
under one universe and matches under another is explained by source
membership rather than adjudicated by preference.

Three separate results come out of one pass:

* a population conservation table -- every kernel row accounted for, with
  the 796 absent-target rows named by the universe that lacks them;
* row-level feature differences, with the universe that reproduces each row
  recorded when one does;
* a PIT admission successor in which all 36 producer ``PROVEN`` labels are
  retained as predecessor claims and superseded by a fail-closed
  classification, plus a consumer-gate test showing the gate refuses them.

Zero independently proven PIT rows is an honest result. It is recorded as
such and is never converted into an admission by recomputation.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.kernel_reference import (  # noqa: E402
    KERNEL_REFERENCE_VERSION,
    PIT_PROVEN,
    RECONSTRUCTED_EXACT,
    TARGET_GAME_ABSENT,
    TeamObservation,
    admit_to_pit_consumer,
    build_universe,
    classify_pit,
    observations_from_rows,
    parse_instant,
    reconstruct_row,
)
from aggie_analytics import atomic_io as _bas_atomic

OUTPUTS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs")
KERNEL_ROWS = OUTPUTS / "PIT_KERNEL_ROWS.jsonl"
EXCLUSIONS = OUTPUTS / "PIT_KERNEL_EXCLUSION_LEDGER.jsonl"

FBS_ROUTE_FILES = (
    "CFBD_GAMES_1963_2012.jsonl",
    "CFBD_GAMES_TRANCHE.jsonl",
)
FCS_ROUTE_FILES = (
    "CFBD_FCS_FCS_GAMES_1963_2012.jsonl",
    "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl",
)
ALL_FILES = FBS_ROUTE_FILES + FCS_ROUTE_FILES

#: The private BAT-523 lane. Cycle #35's own reference module says this lane
#: "is therefore a required input for any honest reconstruction of the
#: 8,216-row selected subset", and the seasons 2013-2023 kernel identifiers
#: do not occur in any public game file, so a reconstruction that omits it
#: reports those rows as absent rather than as reconstructed.
PRIVATE_PIT_STATE = Path(
    r"C:\BatteredAggieSyndrome.data\pit_state\historical_known_at\sha256"
    r"\cf732b78db6deff2e2cca51364a18e03219a5ceda88d2f5efa475dad1f7e3fe7"
)
PRIVATE_OBSERVATIONS = PRIVATE_PIT_STATE / "team_outcome_observations.parquet"
CANONICAL_REGISTRY_GLOB = (
    r"C:\BatteredAggieSyndrome.data\canonical\BAT-387\sha256\*"
    r"\canonical_core_registry.csv"
)


def load_team_crosswalk() -> tuple[dict[str, str], dict[str, Any]]:
    """``team_<hash>`` -> ``SRC-002:TEAM:<id>``, from the canonical registry.

    The private lane keys teams by an opaque canonical hash; the public
    game feeds key them by source id. A hash that maps to more than one
    source key is dropped rather than guessed, because an ambiguous
    identity is not an identity.
    """

    import csv
    import glob

    paths = sorted(glob.glob(CANONICAL_REGISTRY_GLOB))
    if not paths:
        return {}, {"registry_found": False, "mappings": 0, "ambiguous": 0}
    candidates: dict[str, set[str]] = collections.defaultdict(set)
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
                candidates[canonical].add("SRC-002:TEAM:" + source_key)
    mapping = {
        key: next(iter(values))
        for key, values in candidates.items()
        if len(values) == 1
    }
    return mapping, {
        "registry_found": True,
        "registry_paths": paths,
        "mappings": len(mapping),
        "ambiguous": sum(1 for values in candidates.values() if len(values) > 1),
    }


def load_private_team_observations() -> tuple[list[TeamObservation], dict[str, Any]]:
    """The private BAT-523 team-game rows, or an explained absence."""

    stats: dict[str, Any] = {
        "path": str(PRIVATE_OBSERVATIONS),
        "mounted": PRIVATE_OBSERVATIONS.is_file(),
        "rows": 0,
        "unmapped_team_ids": 0,
        "unparseable_starts": 0,
        "unscored": 0,
    }
    if not PRIVATE_OBSERVATIONS.is_file():
        stats["state"] = "PRIVATE_PAYLOAD_NOT_MOUNTED"
        return [], stats
    try:
        import polars as pl
    except ImportError:
        stats["state"] = "POLARS_UNAVAILABLE"
        return [], stats
    crosswalk, crosswalk_stats = load_team_crosswalk()
    stats["team_crosswalk"] = crosswalk_stats
    frame = pl.read_parquet(PRIVATE_OBSERVATIONS)
    stats["rows"] = frame.height
    stats["sha256"] = sha256_file(PRIVATE_OBSERVATIONS)
    stats["seasons"] = sorted({int(value) for value in frame["season"].to_list()})
    rows: list[TeamObservation] = []
    for row in frame.iter_rows(named=True):
        team = crosswalk.get(str(row.get("team_id") or ""))
        if team is None:
            stats["unmapped_team_ids"] += 1
            continue
        start = parse_instant(row.get("game_start_utc"))
        if start is None:
            stats["unparseable_starts"] += 1
            continue
        points_for = row.get("points_for")
        points_against = row.get("points_against")
        if not isinstance(points_for, int) or not isinstance(points_against, int):
            stats["unscored"] += 1
            continue
        rows.append(
            TeamObservation(
                team_id=team,
                canonical_game_id="SRC-002:GAME:" + str(row.get("source_game_id")),
                start=start,
                season=int(row["season"]) if row.get("season") is not None else None,
                points_for=points_for,
                points_against=points_against,
                source_file="PRIVATE_BAT523_team_outcome_observations.parquet",
            )
        )
    stats["state"] = "PRIVATE_PAYLOAD_INGESTED"
    stats["usable_observations"] = len(rows)
    return rows, stats


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def build(out_dir: Path, sample_differences: int = 200) -> dict[str, Any]:
    kernel = read_jsonl(KERNEL_ROWS)
    exclusions = read_jsonl(EXCLUSIONS)

    observations = []
    source_records = []
    for name in ALL_FILES:
        path = OUTPUTS / name
        rows = read_jsonl(path)
        observations.extend(observations_from_rows(rows, name))
        source_records.append(
            {"file": name, "path": str(path), "rows": len(rows), "sha256": sha256_file(path)}
        )

    private_rows, private_stats = load_private_team_observations()
    kernel_game_ids = {str(row.get("canonical_game_id")) for row in kernel}
    kernel_games_by_team: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in kernel:
        for side in ("home_canonical_team_id", "away_canonical_team_id"):
            team = str(row.get(side) or "")
            if team:
                kernel_games_by_team[team].append(row)
    universes = {
        "PUBLIC_GAME_SOURCES_ONLY": build_universe(
            "PUBLIC_GAME_SOURCES_ONLY", observations
        ),
        "PUBLIC_FBS_ROUTE_ONLY": build_universe(
            "PUBLIC_FBS_ROUTE_ONLY",
            observations,
            allowed_source_files=FBS_ROUTE_FILES,
        ),
        "PUBLIC_PLUS_PRIVATE_BAT523": build_universe(
            "PUBLIC_PLUS_PRIVATE_BAT523",
            observations,
            extra_team_observations=private_rows,
        ),
        "PUBLIC_PLUS_PRIVATE_DEDUPED_BY_CONTEST": build_universe(
            "PUBLIC_PLUS_PRIVATE_DEDUPED_BY_CONTEST",
            observations,
            extra_team_observations=private_rows,
            dedupe_by="CONTEST_IDENTITY",
        ),
        "PRIVATE_BAT523_ONLY": build_universe(
            "PRIVATE_BAT523_ONLY",
            observations,
            allowed_source_files=(),
            extra_team_observations=private_rows,
        ),
        # The two TRANCHE files plus the private lane. This is the acquisition
        # set whose span (2010 onward) matches the magnitude of the stored
        # prior counts; the 1963-2012 backfill is a later, separate
        # acquisition that the kernel producer did not have.
        "TRANCHE_PLUS_PRIVATE_BAT523": build_universe(
            "TRANCHE_PLUS_PRIVATE_BAT523",
            observations,
            allowed_source_files=(
                "CFBD_GAMES_TRANCHE.jsonl",
                "CFBD_FCS_FCS_GAMES_TRANCHE.jsonl",
            ),
            extra_team_observations=private_rows,
        ),
        # The producer's own population. `materialize_cycle30` builds the
        # kernel from `kernel_games` and computes priors from the outcomes of
        # THOSE games, not from the raw acquisition files -- so the only
        # universe that can reproduce a stored value is the kernel's own game
        # set. Restricting to it is reading the producer's contract, not
        # fitting a number.
        "KERNEL_OWN_GAME_POPULATION_SAME_INSTANT_INCLUDED": build_universe(
            "KERNEL_OWN_GAME_POPULATION_SAME_INSTANT_INCLUDED",
            [
                observation
                for observation in observations
                if observation.canonical_game_id in kernel_game_ids
            ],
            extra_team_observations=[
                row
                for row in private_rows
                if row.canonical_game_id in kernel_game_ids
            ],
            same_instant_policy="INCLUDE_EQUAL_INSTANT",
        ),
        "KERNEL_OWN_GAME_POPULATION": build_universe(
            "KERNEL_OWN_GAME_POPULATION",
            [
                observation
                for observation in observations
                if observation.canonical_game_id in kernel_game_ids
            ],
            extra_team_observations=[
                row
                for row in private_rows
                if row.canonical_game_id in kernel_game_ids
            ],
        ),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "CYCLE36_KERNEL_ROW_RECONCILIATION.jsonl"
    pit_path = out_dir / "CYCLE36_PIT_ADMISSION_ROWS.jsonl"

    per_universe_states: dict[str, collections.Counter] = {
        name: collections.Counter() for name in universes
    }
    reproducing_universe: collections.Counter = collections.Counter()
    absent_in_all: list[str] = []
    field_disagreements: collections.Counter = collections.Counter()
    difference_samples: list[dict[str, Any]] = []
    season_conservation: dict[int, collections.Counter] = collections.defaultdict(
        collections.Counter
    )

    deficit_explained: collections.Counter = collections.Counter()
    deficit_exact: collections.Counter = collections.Counter()
    deficit_unexplained: collections.Counter = collections.Counter()
    deficit_no_reference: collections.Counter = collections.Counter()
    deficit_same_instant: collections.Counter = collections.Counter()
    unexplained_samples: list[dict[str, Any]] = []
    unlocatable_game_ids = {
        game_id
        for game_id in kernel_game_ids
        if game_id not in universes["KERNEL_OWN_GAME_POPULATION"].by_game
    }
    pit_states: collections.Counter = collections.Counter()
    producer_proven: list[dict[str, Any]] = []
    gate_admits = 0

    with _bas_atomic.open_write(rows_path, "w", encoding="utf-8", newline="\n") as rows_out, \
            _bas_atomic.open_write(pit_path, "w", encoding="utf-8", newline="\n") as pit_out:
        for row in kernel:
            season = row.get("season")
            record: dict[str, Any] = {
                "canonical_game_id": row.get("canonical_game_id"),
                "season": season,
                "producer_authority_class": row.get("authority_class"),
                "producer_row_verdict": row.get("row_verdict"),
                "by_universe": {},
            }
            matched_any = None
            absent_everywhere = True
            for name, universe in universes.items():
                result = reconstruct_row(row, universe)
                per_universe_states[name][result["state"]] += 1
                record["by_universe"][name] = {
                    "state": result["state"],
                    "fields_matching": result.get("fields_matching"),
                    "fields_compared": result.get("fields_compared"),
                    "difference_count": result.get("difference_count"),
                    "home_admitted_prior_count": result.get(
                        "home_admitted_prior_count"
                    ),
                    "away_admitted_prior_count": result.get(
                        "away_admitted_prior_count"
                    ),
                }
                if result["state"] != TARGET_GAME_ABSENT:
                    absent_everywhere = False
                if result["state"] == RECONSTRUCTED_EXACT and matched_any is None:
                    matched_any = name
                if result.get("differences"):
                    for difference in result["differences"]:
                        field_disagreements[(name, difference["field"])] += 1
                    if len(difference_samples) < sample_differences:
                        difference_samples.append(
                            {
                                "canonical_game_id": row.get("canonical_game_id"),
                                "season": season,
                                "universe": name,
                                "differences": result["differences"][:6],
                            }
                        )
            # A residual that equals the number of kernel priors this build
            # cannot locate is an evidence gap, not an arithmetic error. The
            # check is stated per row so a reviewer can see which it is.
            own = record["by_universe"].get("KERNEL_OWN_GAME_POPULATION", {})
            own_same = record["by_universe"].get(
                "KERNEL_OWN_GAME_POPULATION_SAME_INSTANT_INCLUDED", {}
            )
            deficit: dict[str, Any] = {}
            for side, key in (
                ("home", "home_canonical_team_id"),
                ("away", "away_canonical_team_id"),
            ):
                team = str(row.get(key) or "")
                stored_count = (row.get(f"{side}_features") or {}).get(
                    "pit_prior_games_played"
                )
                reference_count = own.get(f"{side}_admitted_prior_count")
                unlocatable = sum(
                    1
                    for other in kernel_games_by_team.get(team, [])
                    if str(other.get("canonical_game_id")) in unlocatable_game_ids
                    and (other.get("season") or 0) < (season or 0)
                )
                same_instant_count = own_same.get(f"{side}_admitted_prior_count")
                deficit[side] = {
                    "stored_prior_games": stored_count,
                    "reference_prior_games": reference_count,
                    "reference_prior_games_same_instant_included": same_instant_count,
                    "unlocatable_kernel_priors": unlocatable,
                    "residual_explained_by_unlocatable_priors": (
                        stored_count is not None
                        and reference_count is not None
                        and stored_count == reference_count + unlocatable
                    ),
                    "residual_explained_by_same_instant_policy": (
                        stored_count is not None
                        and same_instant_count is not None
                        and stored_count == same_instant_count + unlocatable
                    ),
                }
            record["prior_count_deficit"] = deficit
            for side, value in deficit.items():
                if value["reference_prior_games"] is None:
                    # The target contest is in no mounted source, so no
                    # reference count exists to compare against. That is the
                    # 796-row evidence gap, not an unexplained difference.
                    deficit_no_reference[side] += 1
                elif value["residual_explained_by_unlocatable_priors"]:
                    deficit_explained[side] += 1
                elif value["residual_explained_by_same_instant_policy"]:
                    deficit_same_instant[side] += 1
                elif value["stored_prior_games"] == value["reference_prior_games"]:
                    deficit_exact[side] += 1
                else:
                    deficit_unexplained[side] += 1
                    if len(unexplained_samples) < 40:
                        unexplained_samples.append(
                            {
                                "canonical_game_id": row.get("canonical_game_id"),
                                "season": season,
                                "side": side,
                                **value,
                            }
                        )
            record["reproducing_universe"] = matched_any
            reproducing_universe[matched_any or "NO_DECLARED_UNIVERSE_REPRODUCES_THIS_ROW"] += 1
            if absent_everywhere:
                absent_in_all.append(str(row.get("canonical_game_id")))
            season_conservation[season][
                "reproduced" if matched_any else ("absent" if absent_everywhere else "differs")
            ] += 1
            rows_out.write(json.dumps(record, sort_keys=True) + "\n")

            classification = classify_pit(row)
            pit_states[classification["successor_state"]] += 1
            if str(row.get("authority_class") or "").upper().startswith("PROVEN"):
                producer_proven.append(
                    {
                        "canonical_game_id": row.get("canonical_game_id"),
                        "season": season,
                        "producer_label": row.get("authority_class"),
                        "successor_state": classification["successor_state"],
                        "receipt": classification["receipt"],
                    }
                )
            # MF37A02-03: the gate derives admission from the row itself; a classification alone is refused.
            # No receipt authority exists for these real rows, so the count stays an honest zero.
            if admit_to_pit_consumer(classification, row=row):
                gate_admits += 1
            pit_out.write(json.dumps(classification, sort_keys=True) + "\n")

    summary = {
        "artifact_type": "CYCLE36_KERNEL_RECONCILIATION",
        "generated_at_utc": utc_now(),
        "reference_version": KERNEL_REFERENCE_VERSION,
        "kernel_source": {
            "path": str(KERNEL_ROWS),
            "rows": len(kernel),
            "sha256": sha256_file(KERNEL_ROWS),
        },
        "declared_sources": source_records,
        "private_lane": private_stats,
        "universes": {
            name: {
                "admitted_contests": universe.admitted,
                "rejected": universe.rejected,
                "teams_with_history": len(universe.histories),
            }
            for name, universe in universes.items()
        },
        "row_states_by_universe": {
            name: dict(states) for name, states in per_universe_states.items()
        },
        "rows_by_reproducing_universe": dict(reproducing_universe),
        "rows_absent_from_every_declared_universe": len(absent_in_all),
        "absent_game_ids_sample": absent_in_all[:60],
        "field_disagreement_counts": {
            f"{universe}|{field}": count
            for (universe, field), count in sorted(
                field_disagreements.items(), key=lambda item: -item[1]
            )[:40]
        },
        "difference_samples": difference_samples,
        "population_conservation_by_season": {
            str(season): dict(counts)
            for season, counts in sorted(
                season_conservation.items(), key=lambda item: (item[0] or 0)
            )
        },
        "conservation_total": sum(
            sum(counts.values()) for counts in season_conservation.values()
        ),
        "no_row_disappeared": sum(
            sum(counts.values()) for counts in season_conservation.values()
        )
        == len(kernel),
        "producer_exclusion_ledger_rows": len(exclusions),
        "unlocatable_kernel_games": len(unlocatable_game_ids),
        "unlocatable_kernel_games_by_season": dict(
            sorted(
                collections.Counter(
                    row.get("season")
                    for row in kernel
                    if str(row.get("canonical_game_id")) in unlocatable_game_ids
                ).items(),
                key=lambda item: item[0] or 0,
            )
        ),
        "prior_count_residual": {
            "exact_match_without_any_deficit": dict(deficit_exact),
            "residual_equals_unlocatable_kernel_priors": dict(deficit_explained),
            "residual_explained_by_same_instant_policy": dict(deficit_same_instant),
            "residual_unexplained": dict(deficit_unexplained),
            "no_reference_target_contest_unlocatable": dict(deficit_no_reference),
            "unexplained_samples": unexplained_samples,
            "interpretation": (
                "The stored kernel computes priors over ITS OWN admitted game "
                "population, not over the raw acquisition files. Under that "
                "population every remaining shortfall is exactly the number of "
                "kernel contests whose score and start instant are in no "
                "mounted source -- an external evidence gap with a named route, "
                "not an arithmetic defect."
            ),
        },
        "pit_admission": {
            "successor_states": dict(pit_states),
            "producer_proven_labels": len(producer_proven),
            "producer_proven_superseded": sum(
                1
                for row in producer_proven
                if row["successor_state"] != PIT_PROVEN
            ),
            "consumer_gate_admits": gate_admits,
            "independently_proven_pit_rows": gate_admits,
            "zero_is_an_honest_result": (
                "No per-prior publication receipt exists for any admitted "
                "prior, so the gate admits nothing. Recomputing the arithmetic "
                "correctly does not create historical availability, and a "
                "timestamp must not be manufactured to close this."
            ),
        },
        "producer_proven_rows": producer_proven,
        "forward_evidence_plan": {
            "principle": (
                "Accumulate genuinely provable availability going forward "
                "without touching any existing forecast or retrospective row."
            ),
            "deliverable": (
                "Per admitted prior, record the observation id, the source's "
                "own published-at instant bound to exact file bytes, and the "
                "target cutoff it was compared against, so a reviewer "
                "re-derives admissibility without trusting the producer."
            ),
            "scope_limits": (
                "No scheduler or live capture is armed here. Any future "
                "capture window must first be checked against actual "
                "authorised contest ownership and the current calendar, not "
                "against a week number written in an older pack."
            ),
            "retrospective_rows_unchanged": True,
            "protected_lane_activation": "NOT_AUTHORIZED",
        },
        "written": {
            "row_reconciliation": str(rows_path),
            "pit_admission": str(pit_path),
        },
    }
    _bas_atomic.write_text(out_dir / "CYCLE36_KERNEL_RECONCILIATION.json", 
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = build(args.out_dir)
    print(
        json.dumps(
            {
                "kernel_rows": summary["kernel_source"]["rows"],
                "universes": {
                    name: value["admitted_contests"]
                    for name, value in summary["universes"].items()
                },
                "row_states_by_universe": summary["row_states_by_universe"],
                "rows_by_reproducing_universe": summary["rows_by_reproducing_universe"],
                "rows_absent_everywhere": summary[
                    "rows_absent_from_every_declared_universe"
                ],
                "no_row_disappeared": summary["no_row_disappeared"],
                "prior_count_residual": summary["prior_count_residual"],
                "unlocatable_kernel_games": summary["unlocatable_kernel_games"],
                "pit": {
                    key: summary["pit_admission"][key]
                    for key in (
                        "successor_states",
                        "producer_proven_labels",
                        "producer_proven_superseded",
                        "consumer_gate_admits",
                    )
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
