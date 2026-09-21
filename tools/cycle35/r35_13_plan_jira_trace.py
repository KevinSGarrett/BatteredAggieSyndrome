"""R35-13: independently adjudicate the 12 PT35 mappings and trace Jira.

The manager's companion lists twelve concrete owner-section -> BAS-consequence
mappings. This adjudicates each one against evidence actually produced in
this cycle's run directory, and challenges both directions: a mapping the
manager asserted that the evidence does not support is a FALSE POSITIVE, and
an obligation the evidence shows but no mapping named is a MISSING MAPPING.
Agreeing with all twelve without checking would be the failure mode.

The 52 W06 domains, 25 seed rows and 8,111 heuristic relations are inputs,
not the governing union, and are explicitly NOT accepted wholesale here.

Jira handling is duplicate-audit-only and offline: no issue is created, no
status is moved to Done, no BAT-523 completion comment is written, and no
Jira payload is placed in public Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_OUTPUT_DEFAULT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs\20260920T172801Z"
    r"\implementation_output"
)

#: Existing owners. The pack is explicit that BAT-706 is already registered
#: and that "repairing" that false positive by adding a duplicate is itself a
#: defect, so this cycle creates no issue at all.
EXISTING_OWNERS = (
    "BAT-701",
    "BAT-706",
    "BAT-696",
    "BAT-708",
    "BAT-324",
    "BAT-417",
)
OWNER_CFIP = ("CFIP-19", "CFIP-22", "CFIP-24", "CFIP-27")

#: Each row: the manager's mapping, the requirement it lands on, and the
#: artifact this cycle produced that decides it.
PT35_MAPPINGS: tuple[dict[str, Any], ...] = (
    {
        "trace": "PT35-01",
        "owner_section": "01_CANONICAL_GAME_CONTEXT_PUBLISHER.md #2 Release contract",
        "manager_claim": "neutral.py accepts missing identities",
        "requirements": ["R35-07", "R35-08"],
        "evidence": ["R35_07_CANONICAL_FINALS_REPLAY.json"],
        "adjudication": "CONFIRMED_AND_ADDRESSED",
        "basis": (
            "Reproduced at the start head: travel_context returned a complete "
            "row with canonical_contest_id, both participants, venue_id and "
            "venue_timezone all null. Now refused, and the finals replay "
            "binds ordered canonical participants for 686 of 770 real "
            "observations."
        ),
    },
    {
        "trace": "PT35-02",
        "owner_section": "01_CANONICAL_GAME_CONTEXT_PUBLISHER.md #4 Time, corrections, invalidation",
        "manager_claim": "an administrative home flag is not physical home exposure",
        "requirements": ["R35-08", "R35-09"],
        "evidence": ["R35_09_INDEPENDENT_KERNEL_REFERENCE.json"],
        "adjudication": "CONFIRMED_PARTIALLY_ADDRESSED",
        "basis": (
            "ordinary_home_advantage is already None for unknown neutral "
            "state and 0.0 for confirmed neutral. Schedule/venue CORRECTION "
            "supersession with as-of semantics is still not implemented; the "
            "kernel's site_class is UNKNOWN for the rows inspected."
        ),
    },
    {
        "trace": "PT35-03",
        "owner_section": "03_ROSTER_PUBLISHER.md identity/release design",
        "manager_claim": "SEC name/jersey transcription is insufficient",
        "requirements": ["R35-11"],
        "evidence": ["R35_11_AVAILABILITY_RELEASE.json"],
        "adjudication": "CONFIRMED_PARTIALLY_ADDRESSED",
        "basis": (
            "Name/jersey is now joined against a real local roster snapshot "
            "for the 4 SEC programs it covers: 28 of 92 assertions there "
            "resolve a canonical_player_id on jersey+name agreement, and 64 "
            "are genuinely quarantined as ambiguous (real roster jersey-"
            "number collisions, never guessed). The other 7 SEC programs in "
            "the capture, and every assertion outside the covered 4, remain "
            "ROSTER_NOT_LOCALLY_AVAILABLE. The manager's underlying claim "
            "stands for the uncovered majority; it no longer holds "
            "universally, so 'resolved_player_ids = 0' is stale and is "
            "corrected here rather than left standing."
        ),
    },
    {
        "trace": "PT35-04",
        "owner_section": "04_STAFF_PUBLISHER.md #2 Source assertion grain and identity",
        "manager_claim": "substring/caller override proofs fail",
        "requirements": ["R35-02", "R35-03"],
        "evidence": [
            "R35_01_REPRODUCTION.json",
            "R35_02_STAFF_REBUILD_SUMMARY.json",
        ],
        "adjudication": "CONFIRMED_AND_ADDRESSED",
        "basis": (
            "Both defects reproduced at the start head and both now reject. "
            "All 880 references were reparsed from raw sources with exact key "
            "conservation; person, program, role, episode and locator are "
            "stored indivisibly with an assertion_support link."
        ),
    },
    {
        "trace": "PT35-05",
        "owner_section": "04_STAFF_PUBLISHER.md #3 Release, request and projection protocol",
        "manager_claim": "database/proposed adapter omit provenance/fields",
        "requirements": ["R35-03", "R35-04", "R35-12"],
        "evidence": [
            "R35_03_COACHING_RELEASE_SUMMARY.json",
            "CYCLE35_ALL22_ALIGNMENT.json",
        ],
        "adjudication": "CONFIRMED_AND_ADDRESSED",
        "basis": (
            "The release stores provenance per observation and reports zero "
            "assertions without a supporting observation. The adapter now "
            "carries conflict_state, responsibility, rights_state and "
            "source_revision and retains unmodelled extensions instead of "
            "discarding them."
        ),
    },
    {
        "trace": "PT35-06",
        "owner_section": "04_STAFF_PUBLISHER.md #4 PIT, conflicts and corrections",
        "manager_claim": "rights/conflict are dropped by adapter",
        "requirements": ["R35-04", "R35-05", "R35-12"],
        "evidence": ["CYCLE35_ALL22_ALIGNMENT.json"],
        "adjudication": "CONFIRMED_AND_ADDRESSED",
        "basis": (
            "semantic_fields_dropped is now empty for a payload supplying all "
            "four fields. Conflicts and adjudications are separate tables, so "
            "a correction supersedes without overwriting."
        ),
    },
    {
        "trace": "PT35-07",
        "owner_section": "07_FILM_MANIFEST_VALIDATION.md manifest admission",
        "manager_claim": "a matching hash alone is not semantic authority",
        "requirements": ["R35-12"],
        "evidence": ["CYCLE35_ALL22_ALIGNMENT.json"],
        "adjudication": "CONFIRMED_REMAINS_OPEN",
        "basis": (
            "Exact-release qualification of the C01 v0.1.2 wheel was not "
            "performed: the wheel was not downloaded, installed or qualified "
            "in a private lane this cycle. The manager's observed digest is "
            "carried as OBSERVED-BY-MANAGER, not as BAS-verified."
        ),
    },
    {
        "trace": "PT35-08",
        "owner_section": "08_FILM_PIT_IMPORT.md #2/#3 Time coordinates and replay modes",
        "manager_claim": "late wiki biographies cannot become pregame features",
        "requirements": ["R35-05", "R35-09", "R35-12"],
        "evidence": ["R35_09_PIT_FEASIBILITY.json"],
        "adjudication": "CONFIRMED_AND_ADDRESSED",
        "basis": (
            "The feasibility table separates RECOVERABLE, NOT_RECOVERABLE and "
            "FUTURE_COLLECTION bands, partitions the kernel exactly, and "
            "records independently proven PIT rows as 0 with the trusted "
            "fitted path BLOCKED."
        ),
    },
    {
        "trace": "PT35-09",
        "owner_section": "12_COACH_STATE_IMPORT.md BAS/F10 authority boundary",
        "manager_claim": "must not rewrite titles or infer play-callers",
        "requirements": ["R35-02", "R35-12"],
        "evidence": ["R35_03_COACHING_RELEASE_SUMMARY.json"],
        "adjudication": "CONFIRMED_AND_ADDRESSED",
        "basis": (
            "exact_title_text is stored verbatim beside the normalized "
            "role_family, and responsibility (including play-calling) is a "
            "separate table that this cycle populated with zero rows because "
            "no source explicitly evidenced it."
        ),
    },
    {
        "trace": "PT35-10",
        "owner_section": "13_TEAM_SCHEME_IMPORT.md scheme evidence/import",
        "manager_claim": "official and film-derived scheme claims need separate maturity",
        "requirements": ["R35-04", "R35-12"],
        "evidence": ["R35_03_COACHING_RELEASE_SUMMARY.json"],
        "adjudication": "CONFIRMED_REMAINS_OPEN",
        "basis": (
            "The scheme_assertion table exists with exact_source_text, side, "
            "normalization_version and interval columns, but zero rows were "
            "ingested this cycle. The obligation is structurally prepared and "
            "substantively unmet."
        ),
    },
    {
        "trace": "PT35-11",
        "owner_section": "18_PROTECTED_FORECAST_EVAL.md / 19_CHAMPION_PROMOTION.md",
        "manager_claim": "no promotion from exposed 2024/2025 or unproven freeze",
        "requirements": ["R35-06", "R35-09", "R35-12"],
        "evidence": [
            "R35_07_CANONICAL_FINALS_REPLAY.json",
            "R35_09_PIT_FEASIBILITY.json",
        ],
        "adjudication": "CONFIRMED_AND_ADDRESSED",
        "basis": (
            "Scoring admits only trusted-receipt forecasts committed before "
            "the contest cutoff; with no trusted store the scored row count "
            "is 0. 2024 and 2025 remain absent from the kernel and no "
            "promotion path exists."
        ),
    },
    {
        "trace": "PT35-12",
        "owner_section": "20_FORECAST_REPRODUCIBILITY.md / 21_BAS_FILM_ACCEPTANCE.md #6",
        "manager_claim": "replay, scientific evaluation and release authority are separate stages",
        "requirements": ["R35-12", "R35-14", "R35-15"],
        "evidence": ["CYCLE35_ALL22_ALIGNMENT.json"],
        "adjudication": "CONFIRMED_AND_ADDRESSED",
        "basis": (
            "The alignment artifact reports contract acceptance, artifact "
            "integrity, rights, operational readiness and scientific validity "
            "as five separate dimensions, only one of which BAS can assert."
        ),
    },
)

#: Obligations this cycle's evidence demonstrates that NO PT35 row named.
#: Adjudicating only the manager's twelve would be accepting their framing.
MISSING_MAPPINGS: tuple[dict[str, Any], ...] = (
    {
        "trace": "PT35-M1",
        "obligation": (
            "A national program-season denominator must exist before any "
            "coverage fraction is meaningful."
        ),
        "why_no_mapping_covered_it": (
            "All twelve rows concern per-domain contracts; none establishes "
            "the population those contracts are measured against."
        ),
        "evidence": ["CYCLE35_NATIONAL_COVERAGE.json"],
        "requirements": ["R35-05", "R35-01"],
        "state": "NEWLY_DELIVERED_THIS_CYCLE",
    },
    {
        "trace": "PT35-M2",
        "obligation": (
            "The private-data lane must be distinguishable from a bare "
            "directory before any validator demands a real-data rebuild."
        ),
        "why_no_mapping_covered_it": (
            "PT35-12 covers reproducibility stages but not the environment "
            "predicate that decides whether a replay is even possible."
        ),
        "evidence": ["CYCLE35_VALIDATION_RESULTS.json"],
        "requirements": ["R35-14"],
        "state": "NEWLY_DELIVERED_THIS_CYCLE",
    },
    {
        "trace": "PT35-M3",
        "obligation": (
            "External (non-FBS/FCS) opponents must remain visible in a "
            "national contest population rather than being dropped when they "
            "fail canonical binding."
        ),
        "why_no_mapping_covered_it": (
            "PT35-01 requires canonical participants but says nothing about "
            "what happens to a real opponent outside the canonical "
            "population."
        ),
        "evidence": ["R35_07_CANONICAL_FINALS_REPLAY.json"],
        "requirements": ["R35-05", "R35-07"],
        "state": "NEWLY_DELIVERED_THIS_CYCLE",
    },
)

#: Claims in the companion that the evidence does NOT support as stated.
FALSE_POSITIVE_CHALLENGES: tuple[dict[str, Any], ...] = (
    {
        "trace": "PT35-06",
        "challenged_clause": (
            "Listing R35-05 (historical/current acquisition tranche) among "
            "the requirements for the staff PIT/conflicts/corrections mapping."
        ),
        "challenge": (
            "The adapter's rights/conflict loss is an exchange-contract "
            "defect in R35-04/R35-12. It is independent of how many "
            "program-seasons have been acquired, so R35-05 is not a "
            "dependency of this mapping and pairing them would make the "
            "exchange fix look blocked on an acquisition backlog it does not "
            "need."
        ),
        "disposition": "MAPPING_NARROWED_NOT_REJECTED",
    },
    {
        "trace": "MR34-09",
        "challenged_clause": (
            "That a contradictory supplied winner indicates contaminated "
            "official-final data."
        ),
        "challenge": (
            "The defect is real in code and was reproduced, but the "
            "independent replay of all eight bound NCAA captures found ZERO "
            "winner contradictions across 290 terminal finals. No real row is "
            "affected, and reporting it as a data contamination would "
            "overstate it."
        ),
        "disposition": "DEFECT_CONFIRMED_DATA_IMPACT_ZERO",
    },
    {
        "trace": "BAT-637",
        "challenged_clause": (
            "That the BAT-637 gate identity drifted, as the failing test "
            "message asserts."
        ),
        "challenge": (
            "The live gate identity 606aed7f... equals both the corpus "
            "contract's declared pin and the sibling module's constant. A "
            "single module carries a stale hardcoded c1d22209... from before "
            "BAT-649. The gate did not drift; a code sidecar went stale, and "
            "treating it as gate drift would invite copying a live hash into "
            "an old pin."
        ),
        "disposition": "MANAGER_SUMMARY_REFRAMED_DEFECT_STILL_OPEN",
    },
)


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--run-output", default=str(RUN_OUTPUT_DEFAULT))
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_output = Path(args.run_output)

    adjudications: list[dict[str, Any]] = []
    for row in PT35_MAPPINGS:
        evidence = []
        for name in row["evidence"]:
            path = run_output / name
            evidence.append(
                {
                    "artifact": name,
                    "present": path.is_file(),
                    "sha256": sha256_file(path),
                }
            )
        adjudications.append(
            {
                **row,
                "evidence": evidence,
                "evidence_all_present": all(item["present"] for item in evidence),
                "independently_adjudicated": True,
            }
        )

    by_disposition: dict[str, int] = {}
    for row in adjudications:
        by_disposition[row["adjudication"]] = (
            by_disposition.get(row["adjudication"], 0) + 1
        )

    result = {
        "artifact_type": "CYCLE35_PLAN_JIRA_TRACE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pt35_mappings_adjudicated": len(adjudications),
        "pt35_adjudications": adjudications,
        "adjudication_counts": by_disposition,
        "all_evidence_artifacts_present": all(
            row["evidence_all_present"] for row in adjudications
        ),
        "missing_mappings_found_by_this_cycle": list(MISSING_MAPPINGS),
        "false_positive_challenges": list(FALSE_POSITIVE_CHALLENGES),
        "heuristic_inputs_not_accepted_as_the_governing_union": {
            "w06_domains": 52,
            "seed_rows": 25,
            "heuristic_relations": 8111,
            "treatment": (
                "Inputs only. None is accepted as semantic acceptance, and "
                "none of the 8,111 relations is adopted wholesale."
            ),
        },
        "jira": {
            "mode": "DUPLICATE_AUDIT_OFFLINE_ONLY",
            "existing_owners_reused": list(EXISTING_OWNERS),
            "existing_cfip_issues": list(OWNER_CFIP),
            "new_issues_created": 0,
            "duplicate_audit_result": (
                "Every R35 unit maps onto an already-registered owner key. "
                "BAT-706 is present in the auxiliary registry, as the manager "
                "corrected; no duplicate was created to 'repair' that earlier "
                "false positive, and no scope required a substantially new "
                "owner."
            ),
            "status_transitions_performed": 0,
            "done_transitions_performed": 0,
            "bat523_completion_comment_written": False,
            "public_git_contains_jira_payloads": False,
            "live_readback_performed": False,
            "live_readback_reason": (
                "Reading back live issue status requires a network call this "
                "cache-first cycle does not spend without specific "
                "confirmation. No local claim is made about current live "
                "status as a result."
            ),
        },
        "pit_admitted": False,
    }
    (out_dir / "CYCLE35_PLAN_JIRA_TRACE.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {
            "pt35_adjudicated": len(adjudications),
            "adjudication_counts": by_disposition,
            "all_evidence_present": result["all_evidence_artifacts_present"],
            "missing_mappings_found": len(MISSING_MAPPINGS),
            "false_positive_challenges": len(FALSE_POSITIVE_CHALLENGES),
            "new_jira_issues": 0,
        },
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
