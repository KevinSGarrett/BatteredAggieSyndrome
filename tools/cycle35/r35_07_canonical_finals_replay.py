"""R35-07: replay the official finals with canonical participants bound.

The Cycle #34 recount said so in its own docstring: it did not perform
`bind_participants`, so the canonical-identity conflict path was never
exercised against real data. This replay closes that gap and adds an
independent recount that shares no code with the producer.

Three separate things happen here, deliberately kept apart:

1. **Producer path.** `parse_ncaa_com_scoreboard_contests` (regex over the
   embedded payload) feeds `competing_observations`, with canonical
   participants bound through `cycle30.acquisition.bind_participants` so
   orientation and ordering are validated rather than assumed.

2. **Independent reference.** A separate extractor reads the same raw bytes
   by locating the `initialGames` array and decoding it with a JSON decoder
   -- structural parsing, not the producer's regex -- and recounts
   observations, contests, terminal finals, ties and self-contradicting rows
   from scratch. If the two disagree, that is a finding, which is the entire
   reason not to reuse the producer's helpers for the count.

3. **Scoring join.** Only forecasts admitted by the Cycle #35 trusted-receipt
   contract may be joined. With no trusted receipt store in existence, the
   honest result is zero scored rows, recorded as evidence incompleteness.
   Nothing here can create a forecast to raise that number.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle30.acquisition import (  # noqa: E402
    AcquisitionError,
    bind_participants,
    parse_ncaa_com_scoreboard_contests,
)
from aggie_analytics.cycle33.official_finals import (  # noqa: E402
    competing_observations,
    observation_lifecycle,
)
from aggie_analytics.cycle35.forecast_admission import (  # noqa: E402
    TrustedReceiptStore,
)
from aggie_analytics.cycle35.program_aliases import (  # noqa: E402
    build_crosswalk,
    resolve_program,
)
from aggie_analytics.cycle35.scoring_successor import (  # noqa: E402
    score_admitted_forecasts,
)

RAW_ROOT = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\raw\ncaa")
SCOREBOARD_FILES = [
    "scoreboard-2026-00.html",
    "scoreboard-fcs-2026-00.html",
    "scoreboard-2026-01.html",
    "scoreboard-fcs-2026-01.html",
    "scoreboard-2026-02.html",
    "scoreboard-fcs-2026-02.html",
    "scoreboard-2026-03.html",
    "scoreboard-fcs-2026-03.html",
]
CURRENT_PROGRAMS = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs\CURRENT_2026_PROGRAMS.jsonl"
)

SUBMITTED_POPULATION = {
    "observation_count": 770,
    "unique_contest_count": 468,
    "admitted_unique_games": 290,
    "quarantined_conflicts": 0,
    "nonfinal_contests": 178,
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").casefold()).strip("-")


def load_canonical_crosswalk(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the declared alias crosswalk from the current national membership."""

    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    crosswalk = build_crosswalk(rows)
    stats = {
        "crosswalk_version": crosswalk["crosswalk_version"],
        "membership_rows": crosswalk["membership_rows"],
        "distinct_slugs": crosswalk["distinct_slugs"],
        "usable_slugs": crosswalk["usable_slugs"],
        "ambiguous_slugs": crosswalk["ambiguous_slugs"],
        "source": str(path),
    }
    return crosswalk, stats


def independent_extract(text: str) -> list[dict[str, Any]]:
    """Structurally decode the embedded `initialGames` array.

    This intentionally shares no code with
    `parse_ncaa_com_scoreboard_contests`, which scans the same bytes with a
    per-contest regular expression. Two implementations reading the same
    source is the only way a count is independently confirmed rather than
    merely recomputed by its own author.
    """

    out: list[dict[str, Any]] = []
    for marker in ('"initialGames":', '"games":'):
        index = text.find(marker)
        while index != -1:
            start = text.find("[", index)
            if start == -1:
                break
            try:
                array, _ = json.JSONDecoder().raw_decode(text[start:])
            except json.JSONDecodeError:
                index = text.find(marker, index + 1)
                continue
            if isinstance(array, list) and array and isinstance(array[0], dict):
                if array[0].get("__typename") == "Contest":
                    out.extend(array)
            index = text.find(marker, index + 1)
        if out:
            break
    return out


def independent_recount(games: list[dict[str, Any]]) -> dict[str, Any]:
    """Count from scratch: no producer helper, no shared normalization."""

    observations = 0
    contests: set[str] = set()
    terminal: set[str] = set()
    ties = 0
    winner_contradictions: list[dict[str, Any]] = []
    missing_scores = 0
    states: Counter = Counter()
    for game in games:
        observations += 1
        cid = str(game.get("contestId") or "")
        if cid:
            contests.add(cid)
        state = str(game.get("gameState") or "").upper()
        display = str(game.get("statusCodeDisplay") or "").casefold()
        states[state + "/" + display] += 1
        teams = game.get("teams") or []
        home = next((t for t in teams if t.get("isHome")), None)
        away = next((t for t in teams if not t.get("isHome")), None)
        if home is None or away is None:
            continue
        home_score = home.get("score")
        away_score = away.get("score")
        if not isinstance(home_score, int) or not isinstance(away_score, int):
            missing_scores += 1
            continue
        if state == "F" and display == "final" and cid:
            terminal.add(cid)
            if home_score == away_score:
                ties += 1
            # The source carries its own `isWinner` flags. Checking them
            # against the scores is MR34-09 applied to REAL data, not a
            # fixture: a row asserting a winner its own scores contradict is
            # internally inconsistent whoever published it.
            claimed_home_win = bool(home.get("isWinner"))
            claimed_away_win = bool(away.get("isWinner"))
            computed_home_win = home_score > away_score
            computed_away_win = away_score > home_score
            if (
                claimed_home_win != computed_home_win
                or claimed_away_win != computed_away_win
            ):
                winner_contradictions.append(
                    {
                        "contest_id": cid,
                        "home_score": home_score,
                        "away_score": away_score,
                        "claimed_home_is_winner": claimed_home_win,
                        "claimed_away_is_winner": claimed_away_win,
                    }
                )
    return {
        "observation_count": observations,
        "unique_contest_count": len(contests),
        "terminal_final_contest_count": len(terminal),
        "tie_final_count": ties,
        "rows_without_integer_scores": missing_scores,
        "winner_contradictions": winner_contradictions,
        "winner_contradiction_count": len(winner_contradictions),
        "state_histogram": dict(states),
        "implementation": "STRUCTURAL_JSON_DECODE_NOT_PRODUCER_REGEX",
    }


def bind_all_participants(
    rows: list[dict[str, Any]], crosswalk: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bound: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    rules: Counter = Counter()
    external_opponents: Counter = Counter()
    for row in rows:
        home = resolve_program(row.get("home_seoname"), crosswalk)
        if home["resolution_state"] != "RESOLVED":
            home = resolve_program(row.get("home_name"), crosswalk)
        away = resolve_program(row.get("away_seoname"), crosswalk)
        if away["resolution_state"] != "RESOLVED":
            away = resolve_program(row.get("away_name"), crosswalk)
        for side in (home, away):
            if side["resolution_state"] == "RESOLVED":
                rules[side["rule"]] += 1
            else:
                external_opponents[str(side["raw"])] += 1
        if (
            home["resolution_state"] != "RESOLVED"
            or away["resolution_state"] != "RESOLVED"
        ):
            unresolved.append(
                {
                    "ncaa_com_contest_id": row.get("ncaa_com_contest_id"),
                    "home_seoname": row.get("home_seoname"),
                    "away_seoname": row.get("away_seoname"),
                    "home_state": home["resolution_state"],
                    "away_state": away["resolution_state"],
                }
            )
            # The observation is RETAINED with its identity state visible --
            # an unresolvable participant (a Division II/III or NAIA
            # opponent, or a discontinued program) is a population-boundary
            # fact, never a reason to drop a real game.
            bound.append(
                {
                    **row,
                    "participant_binding_state": "UNRESOLVED_PARTICIPANT",
                    "home_resolution_state": home["resolution_state"],
                    "away_resolution_state": away["resolution_state"],
                }
            )
            continue
        try:
            identities = bind_participants(
                canonical_home_id=home["program_id"],
                canonical_away_id=away["program_id"],
                ordered_participant_ids=[home["program_id"], away["program_id"]],
                displayed_home_name=str(row.get("home_name") or ""),
                displayed_away_name=str(row.get("away_name") or ""),
                name_only=False,
            )
        except AcquisitionError as exc:
            rejected.append(
                {
                    "ncaa_com_contest_id": row.get("ncaa_com_contest_id"),
                    "reason": str(exc),
                    "home_program_id": home["program_id"],
                    "away_program_id": away["program_id"],
                }
            )
            bound.append({**row, "participant_binding_state": "REJECTED_BINDING"})
            continue
        bound.append(
            {
                **row,
                "home_canonical_team_id": identities["home_canonical_id"],
                "away_canonical_team_id": identities["away_canonical_id"],
                "home_binding_rule": home["rule"],
                "away_binding_rule": away["rule"],
                "participant_binding_state": "CANONICAL_BOUND",
            }
        )
    return bound, {
        "bound_count": sum(
            1 for r in bound if r.get("participant_binding_state") == "CANONICAL_BOUND"
        ),
        "unresolved_count": len(unresolved),
        "rejected_count": len(rejected),
        "binding_rule_counts": dict(rules),
        "external_or_unresolved_participants": dict(
            external_opponents.most_common(80)
        ),
        "distinct_external_or_unresolved_names": len(external_opponents),
        "unresolved": unresolved[:50],
        "unresolved_truncated": len(unresolved) > 50,
        "rejected": rejected,
        "no_observation_dropped": len(bound) == len(rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    missing = [f for f in SCOREBOARD_FILES if not (RAW_ROOT / f).is_file()]
    if missing:
        raise SystemExit("missing raw scoreboard captures: " + repr(missing))

    crosswalk, crosswalk_stats = load_canonical_crosswalk(CURRENT_PROGRAMS)

    producer_rows: list[dict[str, Any]] = []
    independent_games: list[dict[str, Any]] = []
    per_file: dict[str, Any] = {}
    for name in SCOREBOARD_FILES:
        path = RAW_ROOT / name
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        producer = parse_ncaa_com_scoreboard_contests(text)
        independent = independent_extract(text)
        per_file[name] = {
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "producer_rows": len(producer),
            "independent_rows": len(independent),
            "counts_agree": len(producer) == len(independent),
        }
        producer_rows.extend(producer)
        independent_games.extend(independent)

    bound_rows, binding_stats = bind_all_participants(producer_rows, crosswalk)
    grouped = competing_observations(bound_rows)
    independent = independent_recount(independent_games)

    # Join only admission-proven forecasts. No trusted receipt store exists,
    # so this is constructed empty on purpose and the result must be zero.
    empty_store = TrustedReceiptStore((), trusted_issuers=())
    scoring = score_admitted_forecasts(
        [
            row
            for row in grouped["admitted_unique_games"]
            if row.get("participant_binding_state") == "CANONICAL_BOUND"
        ],
        [],
        store=empty_store,
        as_of_utc=datetime.now(timezone.utc),
    )

    producer_counts = {
        "observation_count": grouped["observation_count"],
        "unique_contest_count": grouped["unique_contest_count"],
        "admitted_unique_games": len(grouped["admitted_unique_games"]),
        "quarantined_conflicts": len(grouped["quarantined_conflicts"]),
        "nonfinal_contests": len(grouped.get("nonfinal_contests") or []),
        "internally_inconsistent": len(
            grouped.get("internally_inconsistent_observations") or []
        ),
    }
    lifecycles = Counter(observation_lifecycle(row) for row in bound_rows)

    agreement = {
        "observation_count_agrees": producer_counts["observation_count"]
        == independent["observation_count"],
        "unique_contest_count_agrees": producer_counts["unique_contest_count"]
        == independent["unique_contest_count"],
        "producer_observation_count": producer_counts["observation_count"],
        "independent_observation_count": independent["observation_count"],
        "producer_unique_contests": producer_counts["unique_contest_count"],
        "independent_unique_contests": independent["unique_contest_count"],
    }

    result = {
        "artifact_type": "CYCLE35_R35_07_CANONICAL_FINALS_REPLAY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only_inputs": per_file,
        "canonical_crosswalk": crosswalk_stats,
        "participant_binding": binding_stats,
        "producer_path_counts": producer_counts,
        "observation_lifecycles": dict(lifecycles),
        "independent_reference": independent,
        "producer_vs_independent": agreement,
        "submitted_population_for_comparison": SUBMITTED_POPULATION,
        "submitted_population_deltas": {
            key: producer_counts.get(key, None) - value
            if isinstance(producer_counts.get(key), int)
            else None
            for key, value in SUBMITTED_POPULATION.items()
        },
        "scoring_join": {
            "scored_row_count": scoring["scored_row_count"],
            "eligible_final_contests": scoring["eligible_final_contests"],
            "admitted_forecast_rows": scoring["admitted_forecast_rows"],
            "trusted_receipt_store": scoring["store"],
            "zero_scored_is_valid_evidence_incompleteness": True,
            "no_forecast_was_created_to_raise_this_number": True,
        },
        "bind_participants_was_performed": True,
        "counts_recomputed_without_producer_helpers": True,
        "pit_admitted": False,
    }
    (out_dir / "R35_07_CANONICAL_FINALS_REPLAY.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    rows_path = out_dir / "R35_07_BOUND_OBSERVATIONS.jsonl"
    with rows_path.open("w", encoding="utf-8") as handle:
        for row in bound_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(
        {
            "producer": producer_counts,
            "independent": {
                k: independent[k]
                for k in (
                    "observation_count",
                    "unique_contest_count",
                    "terminal_final_contest_count",
                    "winner_contradiction_count",
                )
            },
            "binding": {
                k: binding_stats[k]
                for k in ("bound_count", "unresolved_count", "rejected_count")
            },
            "agreement": agreement,
            "scored_rows": scoring["scored_row_count"],
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
