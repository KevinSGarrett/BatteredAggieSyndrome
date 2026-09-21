"""R35-11: reparse the SEC capture and build the national opportunity set.

Cache-first and read-only. No network request is made by this script: the
SEC capture already on disk is reparsed, and the national report-opportunity
keys are selected from the declared 266-row policy inventory. Where evidence
is genuinely absent, the key stays in the denominator with its exact reason
instead of being dropped to make coverage look better.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle35.availability import (  # noqa: E402
    OUTCOME_BLOCKED,
    OUTCOME_EVIDENCE,
    OUTCOME_EVIDENCE_DECLARED_BUT_UNLOCATABLE,
    OUTCOME_NOT_ATTEMPTED,
    OUTCOME_POLICY_EVIDENCE_ONLY,
    OUTCOME_POLICY_VARIES_UNKNOWN,
    OUTCOME_UNKNOWN_POLICY,
    ReportOpportunity,
    enrich_assertion_identities,
    normalize_join_name,
    opportunity_coverage,
    parse_tabular_report,
    summarize,
)

SEC_CAPTURE = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle34\20260919T_R34_receipts"
    r"\r34_12_browser_capture\sec_official_availability_raw_20260920T054326Z.txt"
)
POLICY_INVENTORY = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs"
    r"\AVAILABILITY_POLICY_INVENTORY.jsonl"
)
#: Real cache-hit CFBD /roster receipts for 12 programs, 2026 season (see
#: CYCLE30_ROSTER_JOIN_LEDGER.json alongside it) -- covers 4 of the 11 SEC
#: programs in the capture (Alabama, Georgia, Ole Miss, Texas A&M). The
#: other 7 SEC programs in this capture have no local roster snapshot and
#: stay ROSTER_NOT_LOCALLY_AVAILABLE, honestly, rather than guessed.
ROSTER_JOIN_SLICE = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs"
    r"\CFBD_ROSTER_JOIN_SLICE.jsonl"
)
#: Real national game sources (see r35_08/r35_09), used only to resolve
#: contest identity by program/opponent/date -- never to compute or infer
#: an availability status.
GAME_SOURCES = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs\CFBD_GAMES_1963_2012.jsonl"),
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle30_work\outputs\CFBD_GAMES_TRANCHE.jsonl"),
)
REPORT_SEASON = 2026

#: The pack requires twelve predeclared national keys spanning multiple
#: reporting policies and conferences, including FCS. They are selected
#: deterministically (sorted by program id within each stratum) rather than
#: cherry-picked, so the selection cannot drift toward whichever programs
#: happened to yield evidence.
TARGET_KEY_COUNT = 12


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_opportunity_keys(rows: list[dict[str, Any]]) -> list[ReportOpportunity]:
    """Deterministic stratified selection across policy, division, conference."""

    strata: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        strata[(str(row.get("policy_status")), str(row.get("classification")))].append(
            row
        )
    selected: list[dict[str, Any]] = []
    # Round-robin across strata so no single policy/division dominates.
    ordered_strata = sorted(strata)
    index = 0
    while len(selected) < TARGET_KEY_COUNT and any(strata.values()):
        stratum = ordered_strata[index % len(ordered_strata)]
        bucket = strata[stratum]
        if bucket:
            bucket.sort(key=lambda item: str(item.get("program_id")))
            selected.append(bucket.pop(0))
        index += 1
        if index > 10_000:
            break

    keys: list[ReportOpportunity] = []
    for row in selected:
        keys.append(classify_opportunity(row))
    return keys


def locate_evidence(row: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Split a row's declared evidence paths into located and unlocatable.

    An inventory row may *claim* evidence; claiming is not having. Each
    declared path is resolved on disk here, and only the ones that really
    exist can support a "a report exists" disposition.
    """

    declared = row.get("evidence_paths") or []
    located: list[str] = []
    missing: list[str] = []
    for item in declared:
        text = str(item or "").strip()
        if not text:
            continue
        (located if Path(text).is_file() else missing).append(text)
    return located, missing


def report_grains(
    assertions: list[dict[str, Any]], parsed: Mapping[str, Any]
) -> dict[str, Any]:
    """Count each grain separately.

    An identity-state tally over assertions is NOT a count of players: the
    SEC capture publishes four stage columns per player row, so every
    player is counted four times. Reporting "28 resolved" without saying
    28 WHAT is how an assertion tally reads as a player tally.

    Four grains are reported, and none is derivable from another by
    division: 252 assertions, 63 published player rows of which 61 are
    distinct on (program, name, jersey), 63 unique player-program-contest
    records, and 23 distinct resolved people.
    """

    def distinct(selector) -> set:
        return {selector(a) for a in assertions}

    source_player_rows = distinct(
        lambda a: (a.get("program"), a.get("published_player_name"), a.get("jersey"))
    )
    player_program_contest = distinct(lambda a: a.get("player_program_contest_key"))
    resolved_people = {
        a["canonical_player_id"]
        for a in assertions
        if a.get("canonical_player_id") is not None
    }
    # Per-player identity state, taken once per source player row rather
    # than once per stage assertion.
    per_row_state: dict[tuple, str] = {}
    contests_per_row: dict[tuple, set] = {}
    for item in assertions:
        key = (item.get("program"), item.get("published_player_name"), item.get("jersey"))
        per_row_state.setdefault(key, item.get("identity_state"))
        contests_per_row.setdefault(key, set()).add(item.get("canonical_contest_id"))
    return {
        "assertion_grain": {
            "assertions": len(assertions),
            "expected": parsed.get("expected_assertion_count"),
            "conservation_holds": parsed.get("conservation_holds"),
            "by_identity_state": dict(Counter(a["identity_state"] for a in assertions)),
        },
        "source_player_row_grain": {
            "source_player_rows": len(source_player_rows),
            "reported_player_rows": parsed.get("player_rows"),
            "stage_columns": parsed.get("stage_columns"),
            "by_identity_state": dict(Counter(per_row_state.values())),
            # The capture publishes 63 rows but only 61 are distinct on
            # (program, name, jersey): two players appear twice, once per
            # contest. Stating the difference and where it comes from stops
            # "61" reading as a row that went missing.
            "published_rows_not_distinct_on_program_name_jersey": (
                None
                if parsed.get("player_rows") is None
                else int(parsed["player_rows"]) - len(source_player_rows)
            ),
            "duplicate_published_rows": [
                {
                    "program": program,
                    "published_player_name": name,
                    "jersey": jersey,
                    "distinct_contests": sorted(contests),
                }
                for (program, name, jersey), contests in sorted(
                    contests_per_row.items()
                )
                if len(contests) > 1
            ],
        },
        "player_program_contest_grain": {
            "unique_records": len(player_program_contest),
        },
        "distinct_resolved_people": len(resolved_people),
        "note": (
            "Identity-state tallies at the assertion grain count each player "
            "once per published stage column. The source_player_row_grain "
            "figures are the per-player counts."
        ),
    }


def explain_changed_rows(
    current: list[dict[str, Any]], previous_path: Path
) -> dict[str, Any]:
    """Diff this run's per-assertion identity outcome against a prior run.

    The manager's rule is "Explain every changed row and do not force an
    improved numerator", so every row whose identity or contest state
    moved is listed with the evidence that moved it, in both directions.
    """

    if not previous_path.is_file():
        return {"compared": False, "reason": f"no prior artifact at {previous_path}"}
    prior = {}
    for line in previous_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        prior[str(row.get("source_locator"))] = row

    changes: list[dict[str, Any]] = []
    for row in current:
        before = prior.get(str(row.get("source_locator")))
        if before is None:
            changes.append({"source_locator": row.get("source_locator"), "change": "ADDED"})
            continue
        if (
            before.get("identity_state") == row.get("identity_state")
            and before.get("canonical_player_id") == row.get("canonical_player_id")
            and before.get("contest_resolution_state") == row.get("contest_resolution_state")
        ):
            continue
        evidence = row.get("identity_evidence") or {}
        changes.append(
            {
                "source_locator": row.get("source_locator"),
                "program": row.get("program"),
                "published_player_name": row.get("published_player_name"),
                "jersey": row.get("jersey"),
                "identity_state_before": before.get("identity_state"),
                "identity_state_after": row.get("identity_state"),
                "canonical_player_id_before": before.get("canonical_player_id"),
                "canonical_player_id_after": row.get("canonical_player_id"),
                "contest_state_before": before.get("contest_resolution_state"),
                "contest_state_after": row.get("contest_resolution_state"),
                "why": {
                    "roster_full_name": evidence.get("roster_full_name"),
                    "given_name_evidence": evidence.get("given_name_evidence"),
                    "surname_evidence": evidence.get("surname_evidence"),
                    "jersey_evidence": evidence.get("jersey_evidence"),
                },
            }
        )
    resolved_before = sum(1 for r in prior.values() if r.get("canonical_player_id"))
    resolved_after = sum(1 for r in current if r.get("canonical_player_id"))
    return {
        "compared": True,
        "previous_artifact": str(previous_path),
        "previous_assertions": len(prior),
        "current_assertions": len(current),
        "changed_row_count": len(changes),
        "resolved_player_ids_before": resolved_before,
        "resolved_player_ids_after": resolved_after,
        "changes": changes,
    }


def classify_opportunity(row: Mapping[str, Any]) -> ReportOpportunity:
    """Disposition one report-opportunity key from evidence, not labels.

    Two invalid implications were removed here after the manager's
    closeout review:

    * `disposition == "ATTEMPTED_WITH_EVIDENCE"` alone was turned into
      REPORT_EVIDENCE_PRESENT, producing five keys that claimed a report
      existed while carrying an empty `evidence_paths` list.
    * `FCS_VARIES_BY_PROGRAM` was turned directly into
      POLICY_PUBLISHES_NO_REPORT. Programs varying in what they publish
      does not establish that none of them publishes anything.
    """

    policy = str(row.get("policy_status"))
    disposition = str(row.get("disposition"))
    located, missing = locate_evidence(row)
    declared_period = str(row.get("season") or "UNDECLARED")
    vintage = row.get("evidence_vintage") or row.get("retrieved_at_utc")
    evidence_kind = str(row.get("evidence_kind") or ("POLICY_RECORD" if located else "NONE"))

    def build(outcome: str, detail: str, kind: str) -> ReportOpportunity:
        return ReportOpportunity(
            program_id=str(row.get("program_id")),
            display_name=str(row.get("display_name")),
            classification=str(row.get("classification")),
            conference=str(row.get("conference")),
            policy_status=policy,
            outcome=outcome,
            detail=detail,
            evidence_paths=tuple(located),
            declared_period=declared_period,
            grain="PROGRAM_DECLARED_PERIOD_POLICY",
            evidence_kind=kind,
            evidence_verified=bool(located) and not missing,
            vintage=str(vintage) if vintage else None,
        )

    if policy == "UNKNOWN_POLICY":
        return build(
            OUTCOME_UNKNOWN_POLICY,
            "The program's availability-reporting policy is not established, "
            "so neither the presence nor the absence of a report can be "
            "interpreted.",
            evidence_kind,
        )
    if policy == "FCS_VARIES_BY_PROGRAM":
        return build(
            OUTCOME_POLICY_VARIES_UNKNOWN,
            "Reporting varies by program and no conference-wide report is "
            "established. That does not establish that no report is "
            "published; the game-report state stays UNKNOWN.",
            evidence_kind,
        )
    if missing and not located:
        return build(
            OUTCOME_EVIDENCE_DECLARED_BUT_UNLOCATABLE,
            f"{len(missing)} evidence path(s) were declared for this key but "
            "none resolves on disk, so no report can be claimed.",
            "NONE",
        )
    if disposition == "ATTEMPTED_WITH_EVIDENCE":
        if not located:
            return build(
                OUTCOME_POLICY_EVIDENCE_ONLY,
                "The inventory records an attempted route with evidence, but "
                "no locatable game-specific report evidence is bound to this "
                "key. A program policy record is not a game report.",
                "NONE",
            )
        if evidence_kind != "GAME_REPORT":
            return build(
                OUTCOME_POLICY_EVIDENCE_ONLY,
                "Located evidence describes the program's policy, not a "
                "specific game report for the declared period.",
                evidence_kind,
            )
        return build(
            OUTCOME_EVIDENCE,
            "A public reporting policy exists and locatable game-report "
            "evidence is bound to this key.",
            "GAME_REPORT",
        )
    if disposition == "NOT_ATTEMPTED":
        return build(
            OUTCOME_NOT_ATTEMPTED,
            "No route was attempted for this key this cycle, so nothing is "
            "established about what the source publishes.",
            evidence_kind,
        )
    return build(
        OUTCOME_BLOCKED,
        "A public reporting policy exists but no route was completed in the "
        "cache-first budget for this cycle.",
        evidence_kind,
    )


def build_program_id_crosswalk(policy_rows: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(row["display_name"]): str(row["program_id"])
        for row in policy_rows
        if row.get("display_name") and row.get("program_id")
    }


def build_roster_index(path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    if not path.is_file():
        return {}, {"path": str(path), "mounted": False}
    rows = read_jsonl(path)
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        # first_name, the roster season and the source id were previously
        # dropped here, which is why a report for "Bob Smith" could resolve
        # to roster person "Alice Smith": the contradicting given name never
        # reached the matcher, and the bare provider id was not
        # source-qualified.
        index[str(row.get("team"))].append(
            {
                "id": row.get("id"),
                "first_name": row.get("firstName"),
                "last_name": row.get("lastName"),
                "jersey": row.get("jersey"),
                "position": row.get("position"),
                "roster_season": row.get("source_year"),
                "source_id": row.get("source_id"),
                "source_path": str(path),
            }
        )
    return dict(index), {
        "path": str(path),
        "mounted": True,
        "rows": len(rows),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "programs_covered": sorted(index),
    }


def build_games_index(
    sources: tuple[Path, ...], season: int
) -> tuple[dict[tuple[str, str, int, int], list[dict[str, Any]]], dict[str, Any]]:
    from datetime import datetime as _datetime

    index: dict[tuple[str, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    stats = {"sources": [], "season_rows": 0}
    for source in sources:
        rows = read_jsonl(source)
        stats["sources"].append({"path": str(source), "rows": len(rows)})
        for row in rows:
            if row.get("season") != season:
                continue
            start = row.get("startDate")
            if not isinstance(start, str) or not start.strip():
                continue
            try:
                when = _datetime.fromisoformat(start.replace("Z", "+00:00"))
            except ValueError:
                continue
            game_id = row.get("id")
            home, away = row.get("homeTeam"), row.get("awayTeam")
            if game_id is None or not home or not away:
                continue
            stats["season_rows"] += 1
            entry = {
                "canonical_game_id": "SRC-002:GAME:" + str(game_id),
                "start_date": start,
                "source_path": str(source),
            }
            for team, opponent in ((home, away), (away, home)):
                # The year is part of the key: without it a published
                # 9/20/25 label matched a 2026 contest purely because the
                # month and day agreed.
                key = (
                    normalize_join_name(team),
                    normalize_join_name(opponent),
                    when.year,
                    when.month,
                    when.day,
                )
                index[key].append(entry)
    return dict(index), stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument(
        "--compare-with", default="",
        help="A prior R35_11_AVAILABILITY_ASSERTIONS.jsonl to diff this run's "
        "per-assertion identity outcomes against, so every changed row is "
        "explained with the evidence that moved it.",
    )
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not SEC_CAPTURE.is_file():
        raise SystemExit("SEC capture not present: " + str(SEC_CAPTURE))
    raw = SEC_CAPTURE.read_bytes()
    parsed = parse_tabular_report(
        raw.decode("utf-8", errors="replace"),
        source_sha256=hashlib.sha256(raw).hexdigest(),
        retrieval_utc="2026-09-20T05:43:26+00:00",
    )

    policy_rows = read_jsonl(POLICY_INVENTORY)
    program_id_by_name = build_program_id_crosswalk(policy_rows)
    roster_index, roster_stats = build_roster_index(ROSTER_JOIN_SLICE)
    games_index, games_stats = build_games_index(GAME_SOURCES, REPORT_SEASON)

    enriched_assertions = [
        enrich_assertion_identities(
            assertion,
            program_id_by_name=program_id_by_name,
            roster_index=roster_index,
            games_index=games_index,
            season=REPORT_SEASON,
        )
        for assertion in parsed["assertions"]
    ]
    parsed["assertions"] = enriched_assertions
    stats = summarize(enriched_assertions)

    identity_state_counts = Counter(a["identity_state"] for a in enriched_assertions)
    contest_state_counts = Counter(a["contest_resolution_state"] for a in enriched_assertions)
    resolved_player_count = sum(
        1 for a in enriched_assertions if a["canonical_player_id"] is not None
    )
    resolved_contest_count = sum(
        1 for a in enriched_assertions if a["canonical_contest_id"] is not None
    )
    grain_report = report_grains(enriched_assertions, parsed)
    changed_rows = (
        explain_changed_rows(enriched_assertions, Path(args.compare_with))
        if args.compare_with
        else {"compared": False, "reason": "no --compare-with supplied"}
    )

    keys = select_opportunity_keys(policy_rows)
    coverage = opportunity_coverage(keys)

    programs = Counter(row["program"] for row in parsed["assertions"])
    result = {
        "artifact_type": "CYCLE35_R35_11_AVAILABILITY_RELEASE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_requests_made": 0,
        "cache_first": True,
        "sec_capture": {
            "path": str(SEC_CAPTURE),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "player_rows": parsed["player_rows"],
            "stage_columns": parsed["stage_columns"],
            "assertion_count": parsed["assertion_count"],
            "expected_assertion_count": parsed["expected_assertion_count"],
            "conservation_holds": parsed["conservation_holds"],
            "malformed_rows": parsed["malformed_rows"],
            "distinct_programs": len(programs),
            "publication_time_established": parsed["publication_time_established"],
            "publication_time_reason": parsed["publication_time_reason"],
        },
        "status_distribution": stats,
        "national_report_opportunities": coverage,
        "policy_inventory": {
            "path": str(POLICY_INVENTORY),
            "rows": len(policy_rows),
            "sha256": hashlib.sha256(POLICY_INVENTORY.read_bytes()).hexdigest()
            if POLICY_INVENTORY.is_file()
            else None,
        },
        "grain_report": grain_report,
        "changed_rows_vs_previous_run": changed_rows,
        "canonical_identity_state": {
            "resolved_player_ids": resolved_player_count,
            "resolved_contest_ids": resolved_contest_count,
            "assertion_count": len(enriched_assertions),
            "by_identity_state": dict(identity_state_counts),
            "by_contest_resolution_state": dict(contest_state_counts),
            "roster_source": roster_stats,
            "games_source": games_stats,
            "reason": (
                "A player resolves only when a local roster snapshot covers "
                "the program AND the published jersey number/name agree with "
                "exactly one roster row; an ambiguous or conflicting match is "
                "quarantined, never guessed. A resolved identity is never "
                "itself an injury/health fact -- it does not change status "
                "or presence. Roster coverage is real but partial: only "
                + str(len(roster_stats.get("programs_covered", [])))
                + " of the capture's programs have a local roster snapshot."
            ),
        },
        "unmet_requirements": [
            "Durable official raw/rendered evidence is not bound for the SEC "
            "capture: the file is a rendered table with no per-report "
            "publication timestamp and no archived original response.",
            "Canonical player identity is resolved only for programs with a "
            "local roster snapshot (" + ", ".join(roster_stats.get("programs_covered", [])) + "); "
            "the remaining SEC programs in this capture stay "
            "ROSTER_NOT_LOCALLY_AVAILABLE, a genuine local data gap, not a "
            "code defect.",
            "Stage vintage is exposed only as an ordinal position within the "
            "report's own four-stage sequence, never as an absolute "
            "publication timestamp, since no per-stage timestamp exists in "
            "this capture.",
            "Of the 12 predeclared keys, only those marked "
            + OUTCOME_EVIDENCE
            + " carry acquired evidence; the rest are retained with their "
            "exact reason and remain unmet.",
        ],
        "semantics": {
            "no_report_means": "UNKNOWN",
            "unlisted_player_means": "UNKNOWN",
            "dash_stage_means": "PUBLISHED_EMPTY_NOT_AVAILABLE",
            "out_means_injured": False,
            "page_byline_dates_each_embedded_report": False,
            "name_hit_or_roster_membership_is_not_an_injury_fact": True,
            "no_report_is_not_an_injury_fact": True,
        },
        "pit_admitted": False,
    }
    (out_dir / "R35_11_AVAILABILITY_RELEASE.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    rows_path = out_dir / "R35_11_AVAILABILITY_ASSERTIONS.jsonl"
    with rows_path.open("w", encoding="utf-8") as handle:
        for row in parsed["assertions"]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(json.dumps(
        {
            "player_rows": parsed["player_rows"],
            "stage_columns": parsed["stage_columns"],
            "assertions": parsed["assertion_count"],
            "conservation_holds": parsed["conservation_holds"],
            "distinct_programs": len(programs),
            "by_status": stats["by_status"],
            "by_presence": stats["by_presence"],
            "unrecognized_vocabulary": stats["unrecognized_vocabulary"],
            "opportunity_keys": coverage["key_count"],
            "opportunity_outcomes": coverage["by_outcome"],
            "opportunity_classifications": coverage["by_classification"],
            "distinct_conferences": len(coverage["distinct_conferences"]),
            "distinct_policies": coverage["distinct_policies"],
            "resolved_player_ids_ASSERTION_GRAIN": resolved_player_count,
            "resolved_contest_ids_ASSERTION_GRAIN": resolved_contest_count,
            "source_player_rows": grain_report["source_player_row_grain"]["source_player_rows"],
            "by_identity_state_PER_PLAYER_ROW": grain_report["source_player_row_grain"]["by_identity_state"],
            "distinct_resolved_people": grain_report["distinct_resolved_people"],
            "unique_player_program_contest": grain_report["player_program_contest_grain"]["unique_records"],
            "by_identity_state_ASSERTION_GRAIN": dict(identity_state_counts),
            "by_contest_resolution_state": dict(contest_state_counts),
            "roster_programs_covered": roster_stats.get("programs_covered"),
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
