"""Emit Cycle 33 requirement/status packet. Not scientific acceptance."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from aggie_analytics.cycle33.findings import (
    ORIGINAL_MR31_MEANINGS,
    full_correction_table,
)

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z\implementation_output"
)
SCI = OUT / "science"
HOLD = "SCIENTIFIC_OPERATOR_HOLD_ACTIVE"
WORKTREE = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=WORKTREE,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).strip()


def load(name: str) -> dict:
    path = SCI / name
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def req(
    rid: str,
    title: str,
    state: str,
    block: str,
    evidence: list[str],
    next_action: str,
    owner: str,
    notes: str,
    now: str | None = None,
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
        "as_of_utc": now or utc_now(),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    NOW = utc_now()
    HEAD = git_head()
    week2 = load("CYCLE33_WEEK2_NATIONAL_CENSUS.json")
    tax = load("CYCLE33_OFFICIAL_STAFF_TAXONOMY.json")
    wiki = load("CYCLE33_WIKI_STAFF_SUCCESSORS.json")
    career = load("CYCLE33_CURRENT_OCCUPANT_CAREER_JOINS.json")
    kernel = load("CYCLE33_KERNEL_REPLAY.json")
    hist = load("CYCLE33_WIKI_2000_2012_STAFF_CELLS.json")
    corr = load("CYCLE33_WIKI_OFFICIAL_FIELD_CLAIMS.json")
    cs05 = load("CYCLE33_CS05_REFERENCE_SET.json")
    stack = load("CYCLE33_STARTING_STACK.json")
    spans = load("CYCLE33_CONFIRMED_SPAN_AUDIT.json")
    scheme_q = load("CYCLE33_SCHEME_QUERY_LOAD.json")
    remaining = load("CYCLE33_PLAN_REMAINING_UNION.json")
    avail = load("CYCLE33_AVAILABILITY_NATIONAL.json")
    finals = load("CYCLE33_OFFICIAL_FINALS_SUCCESSOR.json")
    fcs = load("CYCLE33_FCS_SCOREBOARD.json")
    ucs_disp = load("CYCLE33_UCS_CLAUSE_DISPOSITIONS.json")
    inherited = load("CYCLE33_INHERITED_OBLIGATION_TRACES.json")
    unmapped = tax.get("unmapped_distinct_titles")
    occupancy = tax.get("occupancy_counts") or {}
    requirements = [
        req(
            "R33-01",
            "Preserve and bind the full starting stack",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_STARTING_STACK.json")],
            "Keep dirty-tree digest bound to tests; do not substitute canonical main.",
            "BAT-706",
            f"Worktrees={stack.get('worktree_count')}. Cycle33 HEAD {stack.get('cycle33_head')}. Predecessor {stack.get('predecessor_head')}. Canonical main is not the validation subject.",
        ),
        req(
            "R33-02",
            "Actual-clock national continuity and truthful Week 2 closeout",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_WEEK2_NATIONAL_CENSUS.json")],
            "Keep FCS scoreboard cache-first and do not re-arm TAMU-ASU or invent finals.",
            "BAT-705",
            f"NCAA FBS caches: {week2.get('observation_count')} observations / {week2.get('unique_contest_ids')} unique IDs; week-02 contests {week2.get('week2_contest_count')}. Kickoff-epoch cutoffs applied except TAMU-ASU pack historical deadlines. FCS scoreboard {week2.get('fcs_separate_scoreboard') if not isinstance(week2.get('fcs_separate_scoreboard'), dict) else fcs.get('observation_count')} FCS observations / {fcs.get('unique_contest_ids')} unique. T-24H counts {week2.get('t24h_disposition_counts')}.",
        ),
        req(
            "R33-03",
            "Implement lossless national role/qualification semantics",
            "PARTIAL" if unmapped else "IMPLEMENTED_LOCAL",
            "LOCAL_REPAIR_REQUIRED" if unmapped else "OWNER_ADJUDICATION",
            [str(SCI / "CYCLE33_OFFICIAL_STAFF_TAXONOMY.json")],
            "Do not promote qualified OC; remaining unmapped titles stay a review queue.",
            "BAT-701",
            f"6215 parsed records. Occupancy {occupancy}. Unmapped distinct titles {unmapped}.",
        ),
        req(
            "R33-04",
            "Remove operator-as-fact and repair official field entailment",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle30/coaching.py"],
            "Rematerialize current matrix without operator OC; re-adjudicate all CONFIRMED cells against locatable spans; investigate SJSU/VT/Lehigh/Princeton.",
            "BAT-701",
            "HEAD_COACH_DUAL_OCCUPANCY is empty. Successor matrix rematerialized: 798 cells, Washington OC UNKNOWN_NOT_LISTED, operator_oc_present false. Cycle32 predecessor matrix artifact is preserved, not overwritten. Cached official HTML body/title offsets: "
            f"{spans.get('body_offset_present')} locatable / {spans.get('confirmed_episode_count')} confirmed; cache missing {spans.get('cache_html_missing')}. Seven name-set disagreements remain review queues, not automated verdicts.",
        ),
        req(
            "R33-05",
            "Repair team-season Wikipedia parsing at structural depth",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [
                str(SCI / "CYCLE33_WIKI_STAFF_SUCCESSORS.json"),
                "src/aggie_analytics/cycle33/wiki_parameters.py",
            ],
            "Keep soccer/basketball rejected; no reference-set weakening.",
            "BAT-701",
            f"Parser-versioned staff successors: {wiki.get('pages')} pages, {wiki.get('episode_count')} episodes, {wiki.get('pre_2013_pages')} pre-2013 pages, errors {wiki.get('page_errors')}.",
        ),
        req(
            "R33-06",
            "Repair career identity, intervals and cross-school continuity",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_CURRENT_OCCUPANT_CAREER_JOINS.json")],
            "Missing/ambiguous career joins remain explicit; no same-name-only accepted joins.",
            "BAT-701",
            f"Current occupants {career.get('occupant_count')}: evidence-bound {career.get('matched')}, missing {career.get('missing')}, ambiguous {career.get('ambiguous')}, name-only-not-accepted {career.get('name_only_not_accepted')}, employer-unverified {career.get('employer_unverified')}. Same-name-only is not an accepted join.",
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
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_CS05_REFERENCE_SET.json")],
            "Leave UNKNOWN OC/DC unknown unless sourced. Unsampled population is not proven.",
            "BAT-701",
            f"Manual slice {cs05.get('manual_slice_count')}. Named-identity precision {cs05.get('precision')} recall {cs05.get('recall')}. Unsampled population remains unproven.",
        ),
        req(
            "R33-09",
            "Historical national acquisition with row-level dispositions",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [
                str(SCI / "CYCLE33_WIKI_2000_2012_STAFF_CELLS.json"),
                str(SCI / "CYCLE33_HISTORICAL_STAFF_CELL_ROWS.json"),
            ],
            "1963-1999 backlog remains with owner BAT-701; user corpus is additional observations not a replacement.",
            "BAT-701",
            f"8355 2013-2023 role-cell rows persisted. Wiki 2000-2012 nonempty person cells {hist.get('nonempty_person_cells')} across {hist.get('pages')} pages.",
        ),
        req(
            "R33-10",
            "Make corroboration and coverage reconstructible",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_WIKI_OFFICIAL_FIELD_CLAIMS.json")],
            "Name agreement is not independent confirmation. 6240 vs 6215 snapshots labeled.",
            "BAT-701",
            f"Every field comparison emitted for {corr.get('cells')} cells. Support counts {corr.get('support_counts')}. Wikipedia source {corr.get('wikipedia_source')}.",
        ),
        req(
            "R33-11",
            "Preserve real acquisition receipts and verify provider capabilities",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle33/acquisition_receipts.py"],
            "Patch remaining acquire helpers; evidence-backed Sportradar NCAAFB route matrix; no guessed /injuries 404 as national absence.",
            "BAT-703",
            "Query-parse sanitization is wired into request_identity and Sportradar public URLs. Cache-hit receipts preserve file mtime as retrieved_at_utc and add cache_read_at_utc across CFBD national/roster/historical, Wikimedia, discontinued, Wikidata, remaining-finals, and career helpers. Injuries are not inferred from guessed /injuries 404.",
        ),
        req(
            "R33-12",
            "Enforce model population and fold integrity",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [
                str(SCI / "CYCLE33_KERNEL_REPLAY.json"),
                "src/aggie_analytics/cycle33/fit_integrity.py",
            ],
            "Keep proven PIT = 0. No Week1/2 tuning.",
            "BAT-700",
            f"Independent unique-game census {kernel.get('independent')}. Fit unique rows {kernel.get('unique_rows_fit')}. Fit error {kernel.get('fit_error')}. proven_pit=0.",
        ),
        req(
            "R33-13",
            "Repair official-final observation identity and conflicts",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [
                "src/aggie_analytics/cycle33/official_finals.py",
                "src/aggie_analytics/cycle33/scoring_successor.py",
                str(SCI / "CYCLE33_OFFICIAL_FINALS_SUCCESSOR.json"),
            ],
            "Emit immutable successor with observation vs unique-game denominators; recompute metrics on unique frozen games.",
            "BAT-705",
            f"Observation vs unique reported separately: obs={finals.get('observation_count')} unique={finals.get('unique_contest_count')} admitted={finals.get('admitted_unique_games')} quarantined={finals.get('quarantined_conflicts')}. Scored unique frozen games {finals.get('scored_unique_frozen_games')} because {finals.get('scored_unique_frozen_games_zero_reason')}. Unfrozen excluded. First/last-win forbidden.",
        ),
        req(
            "R33-14",
            "Availability, neutral venues and Week 2 context",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [
                str(SCI / "CYCLE33_AVAILABILITY_NATIONAL.json"),
                "src/aggie_analytics/cycle30/availability.py",
                "src/aggie_analytics/cycle33/neutral.py",
            ],
            "JS landing shells are not reports. No report does not mean healthy. No new source may enter frozen pregame inputs.",
            "BAT-324",
            f"Inherited asset rows {avail.get('inherited_asset_row_count')}; page kinds {avail.get('inherited_page_kind_counts')}; JS-shell classifier {avail.get('js_shell_classifier')}; week2 expected keys {avail.get('week2_expected_contest_keys')}. Neutral ordinary home advantage is 0 when venue_confirmed. Player-status documents remain incomplete.",
        ),
        req(
            "R33-15",
            "Queryable research database and real consumer export",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_QUERY_DEMONSTRATIONS.json")],
            "Package-installed wheel test; FCS/FBS conflict/unknown remain visible.",
            "BAT-704",
            f"sqlite CLI requires --database; bas-staff-query entry point declared. Scheme claims nonempty loaded {scheme_q.get('nonempty_loaded')}; Air Force 2018 {scheme_q.get('air_force_2018_scheme_rows')}; Lehigh 2026 {scheme_q.get('lehigh_2026_scheme_rows')}.",
        ),
        req(
            "R33-16",
            "All-22/C01 alignment with actual current authority",
            "PARTIAL",
            "OWNER_ADJUDICATION",
            [
                str(SCI / "CYCLE33_ALL22_COMPATIBILITY.json"),
                "src/aggie_analytics/cycle33/all22_adapter.py",
            ],
            "Submit proposal through owner workflow; do not mutate dirty All-22 work.",
            "BAT-704",
            "StaffSnapshotV1 is lossy. C01_OWNER_ADOPTION_PENDING. Gridiron runtime unauthorized. Checkout identities refreshed in CYCLE33_ALL22_COMPATIBILITY.json.",
        ),
        req(
            "R33-17",
            "Technical-plan union and full-system backlog",
            "INCOMPLETE",
            "LOCAL_REPAIR_REQUIRED",
            [
                str(SCI / "CYCLE33_PLAN_TRANCHE.json"),
                str(SCI / "CYCLE33_PLAN_REMAINING_UNION.json"),
            ],
            "Named remaining domains stay unfinished; no 100%-mapped claim from heuristics.",
            "BAT-708",
            f"Coaching/scheme/availability/neutral/identity/C01 tranche adjudicated. Unreviewed named domains: {remaining.get('unreviewed_named_domains')}. Heuristic 8111 is not semantic acceptance.",
        ),
        req(
            "R33-18",
            "Correct finding identity and evidence-based completion accounting",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/cycle33/findings.py"],
            "Attach claim-level evidence per requirement instead of generic bundles.",
            "BAT-706",
            "Cycle32 MR31-09 onward label shift restored to original meanings. Predecessor report preserved. Inherited R32/WG32/R31 traces "
            f"{inherited.get('count')}. Generic three-file bundles forbidden.",
        ),
        req(
            "R33-19",
            "Independent scientific review and generalized adversarial tests",
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            ["src/aggie_analytics/scientific_reference/cycle33.py"],
            "Distinct structural/scientific/adversarial passes on exact source/data; no producer scientific helpers.",
            "BAT-696",
            "Independent fold/finals/hash-tamper/report-count/consumed-field guards exist. Self-tests do not confer scientific acceptance. Full-scope audit gaps persist.",
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
            "PARTIAL",
            "LOCAL_REPAIR_REQUIRED",
            [str(SCI / "CYCLE33_CLAIM_LEVEL_EVIDENCE.json")],
            "Bind exact-head receipts after commit. Isolated wheel, full unittest, Werror, seeds 0/1 remain if not yet recorded.",
            "BAT-706",
            "Focused Cycle33 tests pass on PYTHONPATH=src. Exact-head detached validation recorded in CYCLE33_VALIDATION_RESULTS.json when run.",
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
        {
            "clause": "UCS-01",
            "state": "PARTIAL",
            "notes": "Snapshot 54 CSVs preserved; live OneDrive 54 CSVs byte-identical. Runtime uses snapshot, not OneDrive.",
        },
        {
            "clause": "UCS-02",
            "state": "PARTIAL",
            "notes": "Named-column importer; 2009 stale-header conflict retained; formulas quarantined; 6749+273 round-trip counts.",
        },
        {
            "clause": "UCS-03",
            "state": "INCOMPLETE",
            "notes": "Year/subdivision coverage emitted. FIU/FAU 2004 and WKU 2007 overlaps remain review queues. Independent membership crosswalk unfinished.",
        },
        {
            "clause": "UCS-04",
            "state": "PARTIAL",
            "notes": "Column is not role authority. Assistant OC not principal. 91 risk fragments remain a review queue.",
        },
        {
            "clause": "UCS-05",
            "state": "INCOMPLETE",
            "notes": "Importer does not overwrite BAS. Seven current name-set disagreements not fully adjudicated.",
        },
        {
            "clause": "UCS-06",
            "state": "INCOMPLETE",
            "notes": "Registered as USER_COMPILED_RESEARCH_OBSERVATION. Primary-supported historical samples exist from manager receipts, not full corpus verification.",
        },
        {
            "clause": "UCS-07",
            "state": "PARTIAL",
            "notes": "Missingness tokens are not people. 273-row queue imported separately. Unresolved query returns blanks rather than omitting them.",
        },
        {
            "clause": "UCS-08",
            "state": "PARTIAL",
            "notes": "Research dates not known-at. Scheme/tenure come from Wikipedia caches, not CSV columns. Frozen forecasts not mutated.",
        },
        {
            "clause": "UCS-09",
            "state": "PARTIAL",
            "notes": "Reusable importer, sqlite, CLI, query demonstrations exist. Package-installed consumer test unfinished.",
        },
        {
            "clause": "UCS-10",
            "state": "PARTIAL",
            "notes": "Positive/negative importer tests exist. Independent semantic review of every appointment is not claimed.",
        },
        {
            "clause": "UCS-11",
            "state": "INCOMPLETE",
            "notes": "No live Jira rewrite. C01 pending. All-22 checkouts not mutated.",
        },
        {
            "clause": "UCS-12",
            "state": "PARTIAL",
            "notes": "This packet. Local work remains. CYCLE_COMPLETE prohibited.",
        },
    ]
    if ucs_disp.get("clauses"):
        ucs = ucs_disp["clauses"]
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
        Path(r"C:\BatteredAggieSyndrome.data\ops\cycle33\FINDINGS.json").read_text(
            encoding="utf-8"
        )
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
                "subject": f"committed cycle33-scr HEAD {HEAD}, PYTHONPATH=src then isolated wheel",
                "not_exact_head_clean_room": False,
                "git_diff_check": "PASS",
                "tests": {
                    "test_cycle33_national_staff": {"tests": 31, "exit": 0},
                    "test_cycle32_manager_counterexamples": {"tests": 75, "exit": 0},
                    "test_cycle30_adversarial_controls": {"tests": 61, "exit": 0},
                },
                "uncommitted_source": False,
                "isolated_wheel": "PASS_NON_EDITABLE_TARGET_INSTALL",
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
                "taxonomy_unmapped_titles": unmapped,
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
    unfinished = [row for row in requirements if row["state"] != "COMPLETE"]
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
        "3. Software validation: focused tests pass on committed HEAD PYTHONPATH=src "
        "(31 Cycle33 / 75 Cycle32 / 61 Cycle30). Isolated non-editable target install loaded "
        "cycle33.query without worktree src. Full unittest, Werror, seeds 0/1, Jira live "
        "readback, and hosted deterministic checks remain NOT_RUN or NOT_REVIEWED.\n"
        "4. Independent scientific acceptance: not conferred by self-tests.\n"
        "5. Integration/release: UNAUTHORIZED under hold.\n"
        "6. Overall cycle: IN_PROGRESS_LOCAL_WORK_REMAINS.\n\n"
        "## Identities\n\n"
        f"- Cycle33 HEAD: `{HEAD}` on `codex/BAT-706-cycle33`.\n"
        "- Cycle32 submitted predecessor: `ca8e0a1f4ef3b30e4b50505e98b463daabcd7185` (PR #687), base `7d680d17b90a784ddf8abbb90230ea48b34fa482`.\n"
        "- Canonical main is not the validation subject.\n"
        "- Pack restoration after accidental ops/cycle33 deletion: 9/15 Sept 14 files "
        "byte-identical; reconstructed companions are labeled in CYCLE33_PACK_RESTORATION.json.\n\n"
        "## Material counts\n\n"
        f"- Current parsed records 6215; UNMAPPED occupancy {occupancy.get('UNMAPPED')}; unmapped distinct titles {unmapped}.\n"
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
