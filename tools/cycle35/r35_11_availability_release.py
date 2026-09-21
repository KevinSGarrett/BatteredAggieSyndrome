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
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.cycle35.availability import (  # noqa: E402
    OUTCOME_BLOCKED,
    OUTCOME_EVIDENCE,
    OUTCOME_POLICY_NO_REPORT,
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
        policy = str(row.get("policy_status"))
        disposition = str(row.get("disposition"))
        if policy == "UNKNOWN_POLICY":
            outcome = OUTCOME_UNKNOWN_POLICY
            detail = (
                "The program's availability-reporting policy is not "
                "established, so neither the presence nor the absence of a "
                "report can be interpreted."
            )
        elif policy == "FCS_VARIES_BY_PROGRAM":
            outcome = OUTCOME_POLICY_NO_REPORT
            detail = (
                "FCS reporting varies by program and no conference-wide "
                "report exists. Absence of a report means UNKNOWN, never "
                "that every player is healthy."
            )
        elif disposition == "ATTEMPTED_WITH_EVIDENCE":
            outcome = OUTCOME_EVIDENCE
            detail = "A public reporting policy exists and evidence was acquired."
        else:
            outcome = OUTCOME_BLOCKED
            detail = (
                "A public reporting policy exists but no route was completed "
                "in the cache-first budget for this cycle."
            )
        keys.append(
            ReportOpportunity(
                program_id=str(row.get("program_id")),
                display_name=str(row.get("display_name")),
                classification=str(row.get("classification")),
                conference=str(row.get("conference")),
                policy_status=policy,
                outcome=outcome,
                detail=detail,
            )
        )
    return keys


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
        index[str(row.get("team"))].append(
            {
                "id": row.get("id"),
                "last_name": row.get("lastName"),
                "jersey": row.get("jersey"),
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
            entry = {"canonical_game_id": "SRC-002:GAME:" + str(game_id)}
            for team, opponent in ((home, away), (away, home)):
                key = (
                    normalize_join_name(team),
                    normalize_join_name(opponent),
                    when.month,
                    when.day,
                )
                index[key].append(entry)
    return dict(index), stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
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
            "resolved_player_ids": resolved_player_count,
            "resolved_contest_ids": resolved_contest_count,
            "by_identity_state": dict(identity_state_counts),
            "by_contest_resolution_state": dict(contest_state_counts),
            "roster_programs_covered": roster_stats.get("programs_covered"),
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
