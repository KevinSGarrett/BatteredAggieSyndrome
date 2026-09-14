"""Emit Cycle 33 requirement/status packet. Not scientific acceptance."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.cycle33.findings import ORIGINAL_MR31_MEANINGS, full_correction_table

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z\implementation_output"
)
SCI = OUT / "science"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
HEAD = "ca8e0a1f4ef3b30e4b50505e98b463daabcd7185"
HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"


def req(
    rid: str,
    title: str,
    state: str,
    block: str,
    evidence: list[str],
    next_action: str,
    owner: str,
    notes: str,
) -> dict:
    return {
        "requirement_id": rid,
        "title": title,
        "state": state,
        "block_class": block,
        "owner": owner,
        "implementation_evidence": evidence,
        "manager_acceptance": "PENDING",
        "scientific_trust_recovered": False,
        "next_action": next_action,
        "notes": notes,
        "as_of_utc": NOW,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    requirements = [
        req(
            "R33-01",
            "Preserve and bind the full starting stack",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_STARTING_STACK.json")],
            "Complete payload/protected-hash inventory, change-owner matrix, and dirty-tree source digest for tests.",
            "BAT-706",
            "14 worktrees. Predecessor ca8e0a1f bound. Canonical main 55e12a5a is not the validation subject. Cycle32 worktree left unmutated.",
        ),
        req(
            "R33-02",
            "Actual-clock national continuity and truthful Week 2 closeout",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_WEEK2_CLOSEOUT.json")],
            "Census every Week2 FBS/FCS contest from official authority; do not re-arm TAMU-ASU.",
            "BAT-705",
            "TAMU-ASU contest 6604259 on cached week-02 scoreboard is STALE_PREGAME (no invented final). T-24H/T-90M MISSED_CUTOFF_NO_BACKFILL. NCAA caches parse 360 observations / 260 unique IDs across weeks 00-03. FCS separate scoreboard not in this cache set. Kickoff dates captured; most cutoffs remain CUTOFF_UNKNOWN. Missouri State week-1 identity not reused.",
        ),
        req(
            "R33-03",
            "Implement lossless national role/qualification semantics",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.json")],
            "Map remaining 272 unmapped occupancy rows / 227 distinct titles; reprocess 2606 excluded spans; do not promote qualified OC.",
            "BAT-701",
            "6215 parsed records reprocessed. Occupancy PRINCIPAL 744 / CO_SHARED 136 / QUALIFIED 311 / OBSERVED 7514 / UNMAPPED 272. Unique name strings 6170 vs 6215 program-name pairs.",
        ),
        req(
            "R33-04",
            "Remove operator-as-fact and repair official field entailment",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle30/coaching.py"],
            "Rematerialize current matrix without operator OC; re-adjudicate all CONFIRMED cells against locatable spans; investigate SJSU/VT/Lehigh/Princeton.",
            "BAT-701",
            "HEAD_COACH_DUAL_OCCUPANCY is empty. Successor matrix rematerialized: 798 cells, Washington OC UNKNOWN_NOT_LISTED, operator_oc_present false. Cycle32 predecessor matrix artifact is preserved, not overwritten. Span IDs remain string-built pending locatable body/offset validation. Seven name-set disagreements remain review queues.",
        ),
        req(
            "R33-05",
            "Repair team-season Wikipedia parsing at structural depth",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle33/wiki_parameters.py"],
            "Reparse all affected caches into parser-versioned staff successors.",
            "BAT-701",
            "Football-only top-level parameters; soccer/basketball rejected; Infobox college sports team season accepted only when sport=football. Original six counterexamples remain passing.",
        ),
        req(
            "R33-06",
            "Repair career identity, intervals and cross-school continuity",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle30/coaching.py"],
            "Reparse all inherited career pages, not only 188 new pages.",
            "BAT-701",
            "Politician/disambiguation rejected; conflicting source_person_id not overwritten; OC/QB+ref retained. 8399 inherited career pages remapped; evidence-bound join for every current occupant is not complete.",
        ),
        req(
            "R33-07",
            "Materialize scheme and tenure evidence nationally",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_SCHEME_TENURE_CLAIMS.json")],
            "Normalize conflicting scheme strings; attach official corroboration; keep film/causal separate.",
            "BAT-164",
            "13218 cached pages, 0 page errors, 4651 nonempty scheme pages (2416 pre-2013), 9111 nonempty scheme claims, 27691 nonempty tenure claims, inferred_count=0. Wikipedia is not official verification.",
        ),
        req(
            "R33-08",
            "Complete current national staff adjudication and ground-truth reference",
            "INCOMPLETE",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.json")],
            "Independently establish CS-05 stratified reference set; quantify precision/recall; leave UNKNOWN OC/DC unknown unless sourced.",
            "BAT-701",
            "Successor matrix rematerialized (798). CS-05 manual slice is 10 manager primary receipts independent of the parser; unsampled population is not proven. 26 UNKNOWN_NOT_LISTED cells remain unknown.",
        ),
        req(
            "R33-09",
            "Historical national acquisition with row-level dispositions",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_HISTORICAL_STAFF_CELL_ROWS.json")],
            "Extend 2000-2012 staff-cell dispositions beyond scheme/tenure caches; keep discontinued programs.",
            "BAT-701",
            "8355 2013-2023 role-cell rows persisted. User corpus is additional observations, not replacement. Pre-2013 scheme pages exist; full pre-2013 staff cells remain backlog.",
        ),
        req(
            "R33-10",
            "Make corroboration and coverage reconstructible",
            "INCOMPLETE",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_HISTORICAL_STAFF_CELL_ROWS.jsonl")],
            "Replace stale predecessor Wikipedia file in corroboration; emit every field comparison; label 6240 vs 6215 snapshots.",
            "BAT-701",
            "Row-level historical cells exist. Full current corroboration rebuild unfinished.",
        ),
        req(
            "R33-11",
            "Preserve real acquisition receipts and verify provider capabilities",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle33/acquisition_receipts.py"],
            "Patch remaining acquire helpers; evidence-backed Sportradar NCAAFB route matrix; no guessed /injuries 404 as national absence.",
            "BAT-703",
            "Query-parse sanitization and cache-hit identity preservation implemented for the named helpers. Capability matrix not independently expanded.",
        ),
        req(
            "R33-12",
            "Enforce model population and fold integrity",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle33/fit_integrity.py"],
            "Recompute independent 8216-row kernel on exact head; keep proven PIT = 0.",
            "BAT-700",
            "Duplicate/overlap/chronology/exposed-season guards reject at fold_local_fit. Independent numerical replay not repeated this cycle. proven_pit=0.",
        ),
        req(
            "R33-13",
            "Repair official-final observation identity and conflicts",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle30/acquisition.py"],
            "Emit immutable successor with observation vs unique-game denominators; recompute metrics on unique frozen games.",
            "BAT-705",
            "Competing scores quarantine before first-win. Predecessor census: 198 observations, 99 contest IDs. Successor scoring unfinished.",
        ),
        req(
            "R33-14",
            "Availability, neutral venues and Week 2 context",
            "INCOMPLETE",
            "LOCAL_REPAIR_REQUIRED",
            [],
            "Capture actual player-status documents; retain national expected keys including non-conference games.",
            "BAT-324",
            "Not materially advanced this cycle beyond inherited Cycle32 exhaustion evidence.",
        ),
        req(
            "R33-15",
            "Queryable research database and real consumer export",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_QUERY_DEMONSTRATIONS.json")],
            "Package-installed wheel test; load scheme/tenure claims into the consumer; FCS/FBS conflict/unknown remain visible.",
            "BAT-704",
            "sqlite CLI requires --database. Air Force 2018, Lehigh 2026, Troy Calhoun, unresolved rows demonstrated. Unresolved count includes blank cells.",
        ),
        req(
            "R33-16",
            "All-22/C01 alignment with actual current authority",
            "PARTIAL",
            "OWNER_ADJUDICATION",
            ["src/aggie_analytics/cycle33/all22_adapter.py"],
            "Refresh 11 All-22 checkout identities; submit proposal through owner workflow; do not mutate dirty All-22 work.",
            "BAT-704",
            "StaffSnapshotV1 is lossy. C01_OWNER_ADOPTION_PENDING. Gridiron runtime unauthorized.",
        ),
        req(
            "R33-17",
            "Technical-plan union and full-system backlog",
            "INCOMPLETE",
            "LOCAL_REPAIR_REQUIRED",
            [],
            "Adjudicate coaching/scheme/availability/neutral/identity/C01 sections against the 902-plan inventory.",
            "BAT-708",
            "902 candidates / 8111 heuristics remain unreviewed as a semantic union. No 100%-mapped claim.",
        ),
        req(
            "R33-18",
            "Correct finding identity and evidence-based completion accounting",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle33/findings.py"],
            "Attach claim-level evidence per requirement instead of generic bundles.",
            "BAT-706",
            "Cycle32 MR31-09 onward label shift restored to original meanings. Predecessor report preserved.",
        ),
        req(
            "R33-19",
            "Independent scientific review and generalized adversarial tests",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/scientific_reference/cycle33.py"],
            "Distinct structural/scientific/adversarial passes on exact source/data; no producer scientific helpers.",
            "BAT-696",
            "Independent fold/finals guards exist. Full-scope audit gaps persist. Self-tests do not confer scientific acceptance.",
        ),
        req(
            "R33-20",
            "Jira synchronization, reviews and cost control",
            "INCOMPLETE",
            "OWNER_ADJUDICATION",
            ["C:\\BatteredAggieSyndrome.data\\ops\\cycle33\\JIRA_UPDATE_RECEIPTS.json"],
            "Duplicate-audit then local/live Jira updates without parent completion comment or paid review.",
            "BAT-706",
            "No live Jira Done/merge. Paid AI cost 0. Hold remains. Reviews not remirrored this cycle.",
        ),
        req(
            "R33-21",
            "Exact-head clean-room validation and safe hygiene",
            "INCOMPLETE",
            "LOCAL_REPAIR_REQUIRED",
            [],
            "Commit intended source then validate detached submitted head, isolated wheel, warnings-as-errors, hash seeds 0/1, mounted twice.",
            "BAT-706",
            "Focused tests pass on dirty worktree. Exact-head clean-room, full unittest, package install not run. git diff --check clean for current edits.",
        ),
        req(
            "R33-22",
            "Final acceptance packet and persistence",
            "PARTIAL",
            "RELEASE_AUTHORITY",
            [str(OUT / "CYCLE33_FINAL_REPORT.md")],
            "Keep packet synchronized as remaining local work proceeds. CYCLE_COMPLETE is prohibited under hold.",
            "BAT-706",
            "This emission. Headline IN_PROGRESS_LOCAL_WORK_REMAINS.",
        ),
        req(
            "R33-23",
            "Integrate and verify the user-collected 2000-2026 national staff corpus",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [
                str(SCI / "CYCLE33_USER_COACHES_IMPORT_SUMMARY.json"),
                str(SCI / "CYCLE33_USER_COACHES_LIVE_DELTA.json"),
                str(SCI / "CYCLE33_QUERY_DEMONSTRATIONS.json"),
            ],
            "Inspect 91 risk fragments, 7 current name-set disagreements, 12 aliases; primary-source verify samples; keep unverified visible.",
            "BAT-701",
            "54/54 files, 6749 staff observations, 273 queue rows imported as USER_COMPILED_RESEARCH_OBSERVATION. Live OneDrive CSVs byte-identical to snapshot. 2026 classified COMBINED_FBS_FCS. 2009 FBS 120 blank Team IDs retained. Not official, not PIT.",
        ),
    ]
    ucs = [
        {"clause": "UCS-01", "state": "PARTIAL", "notes": "Snapshot 54 CSVs preserved; live OneDrive 54 CSVs byte-identical. Runtime uses snapshot, not OneDrive."},
        {"clause": "UCS-02", "state": "PARTIAL", "notes": "Named-column importer; 2009 stale-header conflict retained; formulas quarantined; 6749+273 round-trip counts."},
        {"clause": "UCS-03", "state": "INCOMPLETE", "notes": "Year/subdivision coverage emitted. FIU/FAU 2004 and WKU 2007 overlaps remain review queues. Independent membership crosswalk unfinished."},
        {"clause": "UCS-04", "state": "PARTIAL", "notes": "Column is not role authority. Assistant OC not principal. 91 risk fragments remain a review queue."},
        {"clause": "UCS-05", "state": "INCOMPLETE", "notes": "Importer does not overwrite BAS. Seven current name-set disagreements not fully adjudicated."},
        {"clause": "UCS-06", "state": "INCOMPLETE", "notes": "Registered as USER_COMPILED_RESEARCH_OBSERVATION. Primary-supported historical samples exist from manager receipts, not full corpus verification."},
        {"clause": "UCS-07", "state": "PARTIAL", "notes": "Missingness tokens are not people. 273-row queue imported separately. Unresolved query returns blanks rather than omitting them."},
        {"clause": "UCS-08", "state": "PARTIAL", "notes": "Research dates not known-at. Scheme/tenure come from Wikipedia caches, not CSV columns. Frozen forecasts not mutated."},
        {"clause": "UCS-09", "state": "PARTIAL", "notes": "Reusable importer, sqlite, CLI, query demonstrations exist. Package-installed consumer test unfinished."},
        {"clause": "UCS-10", "state": "PARTIAL", "notes": "Positive/negative importer tests exist. Independent semantic review of every appointment is not claimed."},
        {"clause": "UCS-11", "state": "INCOMPLETE", "notes": "No live Jira rewrite. C01 pending. All-22 checkouts not mutated."},
        {"clause": "UCS-12", "state": "PARTIAL", "notes": "This packet. Local work remains. CYCLE_COMPLETE prohibited."},
    ]
    (OUT / "CYCLE_REQUIREMENT_STATUS.json").write_text(
        json.dumps(
            {
                "cycle": 33,
                "headline": "IN_PROGRESS_LOCAL_WORK_REMAINS",
                "as_of_utc": NOW,
                "subject_head": HEAD,
                "operator_hold": HOLD,
                "paid_ai_cost": 0,
                "scientific_trust_recovered": False,
                "cycle_complete_prohibited": True,
                "requirements": requirements,
                "ucs_clauses": ucs,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "CYCLE33_REQUIREMENT_TO_EVIDENCE.json").write_text(
        json.dumps(
            {
                "cycle": 33,
                "as_of_utc": NOW,
                "rows": [
                    {
                        "requirement_id": row["requirement_id"],
                        "evidence": row["implementation_evidence"],
                        "state": row["state"],
                        "block_class": row["block_class"],
                    }
                    for row in requirements
                ],
                "generic_three_file_bundle_forbidden": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    findings = []
    for fid, meaning in ORIGINAL_MR31_MEANINGS.items():
        findings.append(
            {
                "finding_id": fid,
                "original_meaning": meaning,
                "cycle32_label_shift_restored": True,
                "disposition": "PRESERVED_ORIGINAL_MEANING",
                "block_class": "LOCAL_REPAIR_REQUIRED",
            }
        )
    for item in json.loads(
        Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33\FINDINGS.json").read_text(encoding="utf-8")
    )["findings"]:
        findings.append(
            {
                "finding_id": item["id"],
                "title": item["title"],
                "severity": item["severity"],
                "cycle33_requirements": item.get("cycle33_requirements"),
                "implementation_status": "SEE_REQUIREMENT_STATES",
                "independently_repaired": False,
                "scientific_trust_recovered": False,
            }
        )
    (OUT / "CYCLE33_FINDING_DISPOSITION.json").write_text(
        json.dumps(
            {
                "cycle": 33,
                "as_of_utc": NOW,
                "predecessor_cycle32_report_preserved": True,
                "mr31_correction_table": full_correction_table(),
                "findings": findings,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "CYCLE33_VALIDATION_RESULTS.json").write_text(
        json.dumps(
            {
                "as_of_utc": NOW,
                "subject": "dirty cycle33-scr worktree, PYTHONPATH=src",
                "not_exact_head_clean_room": True,
                "git_diff_check": "PASS",
                "tests": {
                    "test_cycle33_national_staff": {"tests": 25, "exit": 0},
                    "test_cycle32_manager_counterexamples": {"tests": 75, "exit": 0},
                    "test_cycle30_adversarial_controls": {"tests": 61, "exit": 0},
                },
                "uncommitted_source": True,
                "isolated_wheel": "NOT_RUN",
                "full_unittest": "NOT_RUN",
                "warnings_as_errors": "NOT_RUN",
                "hash_seeds": "NOT_RUN",
                "jira_strict_live_readback": "NOT_RUN",
                "paid_review": "NOT_REVIEWED",
                "paid_ai_cost": 0,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (OUT / "CYCLE33_NATIONAL_COVERAGE.json").write_text(
        json.dumps(
            {
                "as_of_utc": NOW,
                "current_official_parsed_records": 6215,
                "predecessor_other_position": 5337,
                "taxonomy_unmapped_titles": 272,
                "unique_global_name_strings": 6170,
                "unique_program_name_pairs": 6215,
                "historical_2013_2023_role_cells": 8355,
                "scheme_pages_attempted": 13218,
                "nonempty_scheme_pages": 4651,
                "pre_2013_scheme_pages": 2416,
                "nonempty_scheme_claims": 9111,
                "nonempty_tenure_claims": 27691,
                "user_corpus_staff_observations": 6749,
                "user_corpus_queue_rows": 273,
                "user_corpus_role_cells": 502946,
                "week2_cached_observations": 360,
                "week2_unique_contest_ids": 260,
                "tamu_asu_ncaa_contest_id": "6604259",
                "user_csv_is_not_official": True,
                "proven_pit": 0,
                "not_full_national_or_25_year_verification": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    unfinished = [
        row
        for row in requirements
        if row["state"] != "COMPLETE"
    ]
    (OUT / "CYCLE33_UNFINISHED_ITEMS.json").write_text(
        json.dumps(
            {
                "as_of_utc": NOW,
                "headline": "IN_PROGRESS_LOCAL_WORK_REMAINS",
                "count": len(unfinished),
                "items": [
                    {
                        "id": row["requirement_id"],
                        "state": row["state"],
                        "block_class": row["block_class"],
                        "next_action": row["next_action"],
                    }
                    for row in unfinished
                ],
                "nothing_left_is_false": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report = (
        "# Cycle 33 packet — not scientific acceptance\n\n"
        "Headline: **IN_PROGRESS_LOCAL_WORK_REMAINS**\n\n"
        "Operator hold: ACTIVE. CYCLE_COMPLETE is prohibited. Paid AI cost: 0. "
        "Proven PIT: 0. Fitted outputs: UNTRUSTED_SHADOW.\n\n"
        "## Six dimensions\n\n"
        "1. Implementation: local code/data/query work advanced; incomplete units remain.\n"
        "2. Data/evidence completeness: INCOMPLETE. Missingness labels are not completeness.\n"
        "3. Software validation: focused tests pass on dirty worktree PYTHONPATH=src "
        "(25 Cycle33 / 75 Cycle32). Exact-head clean-room and isolated wheel not completed "
        "as a detached submitted head before this emission.\n"
        "4. Independent scientific acceptance: not conferred by self-tests.\n"
        "5. Integration/release: UNAUTHORIZED under hold.\n"
        "6. Overall cycle: IN_PROGRESS_LOCAL_WORK_REMAINS.\n\n"
        "## Identities\n\n"
        f"- Predecessor submitted head: `{HEAD}` (PR #687).\n"
        "- Canonical main is not the validation subject.\n"
        "- Pack restoration after accidental ops/cycle33 deletion: 9/15 Sept 14 files "
        "byte-identical; reconstructed companions are labeled in CYCLE33_PACK_RESTORATION.json.\n\n"
        "## Material counts\n\n"
        "- Current parsed records 6215; UNMAPPED occupancy 272.\n"
        "- Successor current matrix 798; Washington OC UNKNOWN_NOT_LISTED.\n"
        "- Historical 2013-2023 role cells 8355.\n"
        "- Wikimedia scheme/tenure: 13218 pages; 4651 nonempty scheme pages; 9111 nonempty scheme claims.\n"
        "- User corpus: 54 files, 6749 staff observations, 273 queue rows; live=snapshot identical.\n"
        "- Week2 NCAA caches: 360 observations / 260 unique IDs; TAMU-ASU 6604259 stale pregame; "
        "MISSED_CUTOFF_NO_BACKFILL; Missouri State not reused.\n"
        "- Jira mirror not fully converged; paid review NOT_REVIEWED.\n"
    )
    (OUT / "CYCLE33_FINAL_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "requirements": len(requirements)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
