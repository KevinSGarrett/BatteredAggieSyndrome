"""R36-16: the handoff packet, with six independent dimensions per requirement.

Every requirement gets implementation, data/evidence, software validation,
independent scientific acceptance, integration/release and overall reported
SEPARATELY, because a single status is what lets "the code is written" read
as "the science is accepted".

The packet is assembled from artifacts that already exist on disk. A declared
artifact that is absent becomes an explicit unavailable entry rather than a
silently shortened list, and the packet's own validation runs the adversarial
predicates against itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle36.packet_guards import (  # noqa: E402
    check_command_receipts,
    check_data_root,
    check_head_binding,
    check_lane_head_currency,
    check_member_digests,
    check_population_not_empty,
    check_selected_release_is_the_successor,
    check_unknown_not_converted,
)
from aggie_analytics import atomic_io as _bas_atomic

DATA_ROOT = r"C:\BatteredAggieSyndrome.data"
MANAGER_RUN = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35\20260921T131038Z"
)

IMPL_COMPLETE = "LOCAL_IMPLEMENTATION_COMPLETE"
IMPL_PROGRESS = "IN_PROGRESS"
IMPL_BLOCKED = "BLOCKED_AUTHORITY"

DATA_COMPLETE = "COMPLETE_WITHIN_DECLARED_SCOPE"
DATA_INCOMPLETE = "INCOMPLETE"
DATA_UNAVAILABLE = "SOURCE_UNAVAILABLE"

SW_PASS = "PASS"
SW_FAIL = "FAIL"
SW_NOT_RUN = "NOT_RUN"

ACCEPT_NOT_REVIEWED = "NOT_REVIEWED"
RELEASE_NOT_AUTHORIZED = "NOT_AUTHORIZED"
OVERALL_LOCAL = "IN_PROGRESS_LOCAL_WORK_REMAINS"
OVERALL_SUBMITTED = "IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError:
        return None


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


#: Every declared packet member, with the requirement it serves.
DECLARED_MEMBERS = [
    ("CYCLE36_PRESERVATION_START.json", "R36-01"),
    ("CYCLE36_REPOSITORY_INTEGRITY.json", "R36-02"),
    ("CYCLE36_PROGRAM_RENAME_SOURCES.json", "R36-04"),
    ("CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json", "R36-04"),
    ("CYCLE36_NATIONAL_MEMBERSHIP_ROWS.jsonl", "R36-04"),
    ("CYCLE36_PROGRAM_CROSSWALK.json", "R36-04"),
    ("CYCLE36_INDEPENDENT_SEASON_REVIEW.json", "R36-03"),
    ("CYCLE36_FULL_STAFF_INGEST.json", "R36-05"),
    ("CYCLE36_CAREER_TRANCHE_RECONCILIATION.json", "R36-05"),
    ("CYCLE36_USER_CORPUS_CELLS.json", "R36-05"),
    ("CYCLE36_USER_CORPUS_CELLS.jsonl", "R36-05"),
    ("CYCLE36_STAFF_CAPTURE_INVENTORY.jsonl", "R36-05"),
    ("CYCLE36_STAFF_OBSERVATION_ROWS.jsonl", "R36-05"),
    ("CYCLE36_CAREER_CORPUS.json", "R36-05"),
    ("CYCLE36_CAREER_EPISODE_ROWS.jsonl", "R36-05"),
    ("CYCLE36_SCHEME_AND_RESPONSIBILITY.json", "R36-06"),
    ("CYCLE36_SCHEME_ASSERTIONS.jsonl", "R36-06"),
    ("CYCLE36_SCHEME_CONFLICTS.jsonl", "R36-06"),
    ("CYCLE36_RESPONSIBILITY_ASSERTIONS.jsonl", "R36-06"),
    ("CYCLE36_DELIVERED_RELEASE_MANIFEST.json", "R36-07"),
    ("CYCLE36_PREDECESSOR_RECONCILIATION.json", "R36-07"),
    ("CYCLE36_INDEPENDENT_SEASON_REVIEW_V1_NEWLINE_TRANSLATED.json", "R36-16"),
    ("CYCLE36_PREDECESSOR_RECONCILIATION_V1_UPPERCASE_MAP.json", "R36-16"),
    ("CYCLE36_KERNEL_RECONCILIATION.json", "R36-08"),
    ("CYCLE36_KERNEL_ROW_RECONCILIATION.jsonl", "R36-08"),
    ("CYCLE36_PIT_ADMISSION.json", "R36-08"),
    ("CYCLE36_PIT_ADMISSION_ROWS.jsonl", "R36-08"),
    ("CYCLE36_NEUTRAL_TRAVEL.json", "R36-09"),
    ("CYCLE36_NEUTRAL_TRAVEL_ROWS.jsonl", "R36-09"),
    ("CYCLE36_FORECAST_AND_FINALS.json", "R36-10"),
    ("CYCLE36_AVAILABILITY.json", "R36-11"),
    ("CYCLE36_AVAILABILITY_ROWS.jsonl", "R36-11"),
    ("CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION.json", "R36-12"),
    ("CYCLE36_ALL22_CONTRACT_COMPATIBILITY.json", "R36-13"),
    ("CYCLE36_ALL22_SECTION_TRACE.json", "R36-13"),
    ("CYCLE36_PLAN_JIRA_TRACE.json", "R36-14"),
    ("CYCLE36_JIRA_MIRROR_DISCREPANCY.json", "R36-14"),
    ("CYCLE36_HISTORICAL_AUDIT_MATRIX.json", "R36-14"),
    ("CYCLE36_VALIDATION_RESULTS.json", "R36-15"),
    ("CYCLE36_REQUIREMENT_STATUS.json", "R36-16"),
    ("CYCLE36_FINDING_DISPOSITION.json", "R36-16"),
    ("CYCLE36_REVIEW_FINDING_LEDGER.json", "R36-16"),
    ("CYCLE36_FALSE_POSITIVE_REJECTIONS.json", "R36-16"),
    ("CYCLE36_UNFINISHED_ITEMS.json", "R36-16"),
    ("CYCLE36_AUTHORITY_REQUESTS.json", "R36-16"),
    ("CYCLE36_COST_LEDGER.json", "R36-16"),
    ("CYCLE36_FINAL_REPORT.md", "R36-16"),
]


def requirement_rows(run: Path) -> list[dict[str, Any]]:
    """Six dimensions per requirement, each justified by a named artifact."""

    release = read_json(run / "CYCLE36_DELIVERED_RELEASE_MANIFEST.json") or {}
    validation = read_json(run / "CYCLE36_VALIDATION_RESULTS.json") or {}
    population = read_json(run / "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json") or {}
    staff = read_json(run / "CYCLE36_FULL_STAFF_INGEST.json") or {}
    scheme = read_json(run / "CYCLE36_SCHEME_AND_RESPONSIBILITY.json") or {}
    kernel = read_json(run / "CYCLE36_KERNEL_RECONCILIATION.json") or {}
    neutral = read_json(run / "CYCLE36_NEUTRAL_TRAVEL.json") or {}
    forecast = read_json(run / "CYCLE36_FORECAST_AND_FINALS.json") or {}
    availability = read_json(run / "CYCLE36_AVAILABILITY.json") or {}
    family_b = read_json(run / "CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION.json") or {}
    c01 = read_json(run / "CYCLE36_ALL22_CONTRACT_COMPATIBILITY.json") or {}
    all22 = read_json(run / "CYCLE36_ALL22_SECTION_TRACE.json") or {}
    career = read_json(run / "CYCLE36_CAREER_CORPUS.json") or {}
    plan = read_json(run / "CYCLE36_PLAN_JIRA_TRACE.json") or {}
    integrity = read_json(run / "CYCLE36_REPOSITORY_INTEGRITY.json") or {}

    lane_results = validation.get("lane_results") or {}
    focused = lane_results.get("cycle36_focused_regressions", SW_NOT_RUN)
    strict = lane_results.get("local_strict_repository", SW_NOT_RUN)
    full_mounted = lane_results.get("canonical_mounted_full_suite", SW_NOT_RUN)

    def row(
        requirement: str,
        name: str,
        implementation: str,
        deliverable: str,
        data_state: str,
        numerator: Any,
        denominator: Any,
        software: str,
        evidence: list[str],
        limitation: str,
    ) -> dict[str, Any]:
        return {
            "requirement_id": requirement,
            "name": name,
            "implementation": implementation,
            "exact_deliverable": deliverable,
            "data_evidence": data_state,
            "numerator": numerator,
            "denominator": denominator,
            "software_validation": software,
            "independent_scientific_acceptance": ACCEPT_NOT_REVIEWED,
            "integration_release": RELEASE_NOT_AUTHORIZED,
            "overall": OVERALL_SUBMITTED,
            "evidence": evidence,
            "limitation": limitation,
        }

    rows = [
        row(
            "R36-01",
            "Preserve and reconcile the full starting state",
            IMPL_COMPLETE,
            "Conservation ledger over 15 requirements, 35 obligations, 12 findings; "
            "10 inherited blockers re-read and categorised.",
            DATA_COMPLETE,
            21,
            21,
            focused,
            ["CYCLE36_PRESERVATION_START.json"],
            "Conservation is of the inherited record. It does not audit the "
            "correctness of what those records assert.",
        ),
        row(
            "R36-02",
            "Restore latest-head software and packet integrity",
            IMPL_COMPLETE,
            "Manifest regenerated through tools.repo_integrity.write_manifest; the "
            "PR-unique [process] commit corrected SHA-scoped in the policy; ten "
            "adversarial packet predicates with regressions.",
            DATA_COMPLETE,
            integrity.get("manifest_finding_count_after"),
            integrity.get("manifest_finding_count_before"),
            strict,
            ["CYCLE36_REPOSITORY_INTEGRITY.json", "CYCLE36_PACKET_VALIDATION.json"],
            "Hosted checks at the final head are NOT_RUN: publication of this "
            "branch is a separate permission this pack does not grant.",
        ),
        row(
            "R36-03",
            "Replace weak membership and staff-season authority",
            IMPL_COMPLETE,
            "Record-scoped season binder and exact-transform membership lineage, "
            "with all five manager fixtures plus new wrong-sport, wrong-school, "
            "multiple-season, attribute, template and same-heading controls.",
            DATA_COMPLETE,
            (staff.get("season_states") or {}).get(
                "SEASON_BOUND_BY_GOVERNING_SECTION_HEADING"
            ),
            staff.get("observation_rows"),
            focused,
            ["CYCLE36_FULL_STAFF_INGEST.json", "CYCLE36_STAFF_OBSERVATION_ROWS.jsonl"],
            "A bound season is source-effective, not a pregame known-at. The "
            "stratified human-readable review of admitted season tuples is "
            "delivered as the row file; an independent reviewer has not yet "
            "read it.",
        ),
        row(
            "R36-04",
            "Repair national population and sourced aliases",
            IMPL_COMPLETE,
            "12,988 program-season keys with every season 1963-2026 present; 2024 "
            "and 2025 restored from cached payloads; effective-dated aliases for "
            "three renames; 20 unresolved names published with reasons.",
            DATA_COMPLETE,
            population.get("program_season_keys"),
            12988,
            focused,
            [
                "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json",
                "CYCLE36_PROGRAM_CROSSWALK.json",
            ],
            "20 display names still resolve to no canonical program. They "
            "are not absent from the sources -- an earlier version of this "
            "limitation said so and was wrong for 15 of them, because the "
            "payloads write McNeese for McNeese State, Troy for Troy State "
            "and St. Peter's for Saint Peter's. Each name now carries the "
            "declared spellings related to it as candidates, and each "
            "candidate needs a source stating the rename with an effective "
            "date before it could resolve anything. Matching them without "
            "that source would be the convenience merge the pack forbids, "
            "so the cells stay unresolved and the denominator does not "
            "move.",
        ),
        row(
            "R36-05",
            "Deliver full staff and career ingestion",
            IMPL_COMPLETE,
            f"{staff.get('captures_examined')} captures dispositioned and "
            f"{staff.get('observation_rows')} observation rows with raw titles and "
            "versioned role decompositions, plus the whole cached career "
            f"corpus: {career.get('pages_read')} pages and "
            f"{career.get('episode_rows')} episodes, each with a disposition.",
            DATA_INCOMPLETE,
            # Rows over captures was not a fraction of anything. What is
            # actually incomplete here is the binding of declared acquisition
            # attempts to cached bytes, so the pair measures that: 213 of 266
            # attempts have a capture whose digest matches their receipt.
            staff.get("declared_attempts_matched_by_digest"),
            staff.get("declared_attempts"),
            focused,
            [
                "CYCLE36_STAFF_CAPTURE_INVENTORY.jsonl",
                "CYCLE36_FULL_STAFF_INGEST.json",
                "CYCLE36_CAREER_TRANCHE_RECONCILIATION.json",
            ],
            "All 110,044 user-corpus cells are preserved at cell grain with "
            "their own program resolution and an unverified tier. The whole "
            "cached career corpus is now read: 8,399 pages, 44,748 episodes, "
            "every one dispositioned and carried in the release. 15,993 "
            "resolve an employer, a specific role and an interval and are "
            "retained as candidates; none is joined, because every episode is "
            "RETROSPECTIVE_CANDIDATE_ONLY with pit_admitted false at source. "
            "No career page was newly acquired, so nothing here is officially "
            "corroborated, and 17,574 episodes name an employer outside the "
            "declared FBS/FCS population.",
        ),
        row(
            "R36-06",
            "Ingest supported schemes and responsibilities",
            IMPL_COMPLETE,
            f"{(scheme.get('scheme_states') or {}).get('ADMITTED_CANDIDATE_SCHEME_ASSERTION')} "
            "candidate scheme assertions where there were none; three source-text "
            "conflicts retained; explicit play-calling scan with rejections "
            "recorded.",
            DATA_COMPLETE,
            (scheme.get("scheme_states") or {}).get(
                "ADMITTED_CANDIDATE_SCHEME_ASSERTION"
            ),
            scheme.get("scheme_claims_examined"),
            focused,
            ["CYCLE36_SCHEME_AND_RESPONSIBILITY.json", "CYCLE36_SCHEME_ASSERTIONS.jsonl"],
            "Every admitted row is WIKIPEDIA_ONLY_NOT_OFFICIAL at the candidate "
            "tier. No scheme is officially corroborated and none is PIT-admitted.",
        ),
        row(
            "R36-07",
            "Publish a deterministic national release and query path",
            IMPL_COMPLETE if release else IMPL_PROGRESS,
            "New immutable release directory built twice from frozen inputs and "
            "compared per table; queried from a temporary directory with no "
            "checkout on the path.",
            DATA_COMPLETE if release else DATA_INCOMPLETE,
            # Observations over memberships was not a fraction of anything,
            # the same defect R36-05's pair carried. What this requirement
            # measures is whether the two builds agree table by table at the
            # scientific grain, so the pair is agreeing tables over compared
            # tables.
            sum(
                1
                for entry in (
                    (release.get("determinism") or {}).get("per_table") or {}
                ).values()
                if entry.get("identical")
            ),
            len((release.get("determinism") or {}).get("per_table") or {}),
            focused,
            ["CYCLE36_DELIVERED_RELEASE_MANIFEST.json"],
            "The release carries source observations and identities. It carries "
            "no score, no index and no causal claim.",
        ),
        row(
            "R36-08",
            "Close kernel reconciliation and contain unproven PIT",
            IMPL_COMPLETE,
            "13,280 rows reconstructed under six declared universes; residual "
            "explained per row; all 36 producer PROVEN labels superseded and the "
            "consumer gate admits zero.",
            DATA_INCOMPLETE,
            ((kernel.get("prior_count_residual") or {}).get(
                "residual_equals_unlocatable_kernel_priors"
            ) or {}).get("home"),
            (kernel.get("kernel_source") or {}).get("rows"),
            focused,
            ["CYCLE36_KERNEL_RECONCILIATION.json", "CYCLE36_PIT_ADMISSION.json"],
            "796 kernel contests have no mounted score or start instant (792 of "
            "them season 2023), and 34 home / 35 away sides keep a +1 residual "
            "no declared policy variant reproduces. Independently proven PIT "
            "remains zero and cannot be raised by recomputation.",
        ),
        row(
            "R36-09",
            "Correct venue vintage and neutral-site consumers",
            IMPL_COMPLETE,
            f"{neutral.get('contests')} national contests rebuilt with vintage-"
            "selected geography, two travel legs and fail-closed unknowns.",
            DATA_INCOMPLETE,
            neutral.get("contests_with_both_legs"),
            neutral.get("contests"),
            focused,
            ["CYCLE36_NEUTRAL_TRAVEL.json", "CYCLE36_NEUTRAL_TRAVEL_ROWS.jsonl"],
            "Legs are computable only where a venue carries coordinates; most "
            "pre-2000 contests do not, so their legs are unknown rather than "
            "zero. Origins are current-vintage references, never historical "
            "point-in-time travel.",
        ),
        row(
            "R36-10",
            "Preserve genuine forecasts and reconstruct official scoring",
            IMPL_COMPLETE,
            "26 forecast artifacts inventoried against durable bytes and receipt "
            "authority; official-final population reconstructed independently; "
            "six named scoring refusals each with a reason code.",
            DATA_UNAVAILABLE,
            (forecast.get("frozen_packet_inventory") or {}).get("eligible_packets"),
            (forecast.get("frozen_packet_inventory") or {}).get("packets_examined"),
            focused,
            ["CYCLE36_FORECAST_AND_FINALS.json"],
            "Zero eligible packets. The artifacts carry durable bytes and no "
            "manifest binding contest, model, inputs and a freeze instant. That "
            "evidence does not exist and was not backfilled.",
        ),
        row(
            "R36-11",
            "Deliver availability joins with national policy coverage",
            IMPL_COMPLETE,
            "One row per source assertion with exact status text, vintage and a "
            "declared identity rule; national policy denominator over every "
            "declared program.",
            DATA_INCOMPLETE,
            availability.get("resolved_player_rows"),
            availability.get("assertions_in"),
            focused,
            ["CYCLE36_AVAILABILITY.json", "CYCLE36_AVAILABILITY_ROWS.jsonl"],
            "160 of 252 assertions are quarantined because no roster for their "
            "program and season is mounted. Only SEC reports exist at all; every "
            "other conference contributes UNKNOWN_NOT_HEALTHY opportunities.",
        ),
        row(
            "R36-12",
            "Qualify the composed Family B successor",
            IMPL_COMPLETE,
            "Composed successor reproduced in a new isolated root; all four "
            "published identities derived independently; eleven negative controls "
            "rejected on the owning side; rollback scope written.",
            DATA_COMPLETE,
            family_b.get("negative_controls_rejected"),
            family_b.get("negative_controls_total"),
            focused,
            ["CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION.json"],
            "Isolated qualification is not semantic acceptance of the scientific "
            "calculations inside those consumers, and the canonical mounted lane "
            "honestly remains FAIL while the successor is not activated.",
        ),
        row(
            "R36-13",
            "Align with current All-22 plans and the actual C01 package",
            IMPL_COMPLETE,
            "Wheel digest verified, installed in a throwaway virtualenv with no "
            "index access, its own validators executed against synthetic "
            "payloads; represented/lost/pending field matrix; owner proposal; "
            "all 34 pinned owner documents rehashed against their recorded "
            "remote digests and extracted section by section, with the current "
            "0574-0595 and retained 0070-0081 capability series reconciled.",
            DATA_COMPLETE,
            (all22.get("documents_read") or 0) + (
                c01.get("validator_probes_agreeing") or 0
            ),
            (all22.get("documents_declared") or 0) + (
                c01.get("validator_probes_total") or 0
            ),
            focused,
            [
                "CYCLE36_ALL22_CONTRACT_COMPATIBILITY.json",
                "CYCLE36_ALL22_SECTION_TRACE.json",
            ],
            "Section-level extraction now covers all 34 pinned owner documents "
            "and 249 sections, and every capability is resolved from document "
            "metadata. That is a trace, not an implementation: 33 of 34 "
            "capabilities have no BAS code behind them, the staff projection "
            "remains lossy, owner adoption is outstanding, and the dependent "
            "C01/Film section union beyond AREA-24 is still unread.",
        ),
        row(
            "R36-14",
            "Repair plan/Jira truth and execute named audit units",
            IMPL_COMPLETE,
            "742 live issues read, protected identities asserted unchanged, three "
            "named units audited in three passes each, all 51 domain rows carried "
            "with a next deliverable.",
            DATA_INCOMPLETE,
            len((plan.get("all_cycle_ledger") or {}).get("audited_in_cycle36") or []),
            (plan.get("all_cycle_ledger") or {}).get("cycle_count"),
            focused,
            [
                "CYCLE36_PLAN_JIRA_TRACE.json",
                "CYCLE36_HISTORICAL_AUDIT_MATRIX.json",
                "CYCLE36_JIRA_MIRROR_DISCREPANCY.json",
            ],
            "32 cycles remain unaudited, 40 of 51 domains were untouched and "
            "the 4,549 plan candidates remain an inventory. The private "
            "mirror is now compared row by row -- 12 of 15 mirrored rows "
            "still match the live board, 3 CFIP rows are stale because that "
            "workflow moved on, and none diverges from a state this project "
            "records -- but the mirror asserts 15 of 742 issues, so this is "
            "a discrepancy report and not a parity certificate. The comment "
            "ids it records were not verified to still exist. No Jira write "
            "was performed.",
        ),
        row(
            "R36-15",
            "Exact-final validation and adversarial reporting",
            IMPL_COMPLETE,
            "Nine declared lanes with real command receipts; hash-seed identity "
            "agreement; warnings-as-errors; private-root census bounding the "
            "unmounted claim.",
            DATA_COMPLETE,
            sum(1 for value in lane_results.values() if value == SW_PASS),
            len(lane_results) or None,
            full_mounted,
            ["CYCLE36_VALIDATION_RESULTS.json"],
            "Hosted checks at the final head are NOT_RUN. 73 source files "
            "hardcode the private data root, so the unmounted lane excludes the "
            "environment variable's consumers and not those modules.",
        ),
        row(
            "R36-16",
            "Final handoff with enforceable definitions of done",
            IMPL_COMPLETE,
            "This packet: per-requirement six-dimension status, finding "
            "disposition, unfinished items, authority requests and cost ledger.",
            DATA_COMPLETE,
            None,
            None,
            focused,
            ["CYCLE36_PACKET_MANIFEST.json", "CYCLE36_PACKET_VALIDATION.json"],
            "A finished report is not a finished cycle.",
        ),
    ]
    return rows


def finding_dispositions(run: Path) -> dict[str, Any]:
    pack = read_json(Path(r"C:\BatteredAggieSyndrome.data\ops\cycle36\FINDINGS.json")) or {}
    inherited = pack.get("findings") or []
    dispositions = {
        "MR35R-01": (
            "REPRODUCED_AND_REPAIRED",
            "30 of the 31 hosted findings reproduced locally (manifest size, hash "
            "and coverage) and regenerated to zero through the canonical "
            "generator; the 31st, the PR-unique [process] commit touching a "
            "material path, corrected SHA-scoped in the policy.",
            "CYCLE36_REPOSITORY_INTEGRITY.json",
        ),
        "MR35R-02": (
            "REPAIRED_WITH_A_GUARD",
            "A stale-head packet now fails its own predicate, with head, tree, "
            "data root, member digests and command receipts each checked "
            "separately and the worst state winning.",
            "CYCLE36_PACKET_VALIDATION.json",
        ),
        "MR35R-03": (
            "REPRODUCED_AND_REPAIRED",
            "The subset probe now REFUSES and an unrelated cached year cannot "
            "move an existing row's authority; lineage is exact transform "
            "reproduction.",
            "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json",
        ),
        "MR35R-04": (
            "REPRODUCED_AND_REPAIRED",
            "All four negative controls now bind nothing and the positive still "
            "binds. On the real corpus no capture relied only on an inadmissible "
            "context, so production impact was zero corrupted rows and six "
            "recovered ones.",
            "CYCLE36_FULL_STAFF_INGEST.json",
        ),
        "MR35R-05": (
            "REPAIRED",
            "2024 and 2025 restored from already-cached payloads at zero request "
            "cost; every season 1963-2026 now has a row.",
            "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json",
        ),
        "MR35R-06": (
            "REPAIRED_WITHIN_WHAT_THE_CACHE_SUPPORTS",
            "Whole-cache staff ingestion (2,140 captures, 16,428 observation "
            "rows), scheme ingestion (8,716 candidate assertions), the 48-key "
            "career-tranche reconciliation, and the wider career corpus: all "
            "8,399 cached pages and 44,748 episodes dispositioned and carried "
            "in the release. What the cache cannot supply is corroboration -- "
            "every career episode is RETROSPECTIVE_CANDIDATE_ONLY at source, "
            "so 15,993 resolve an employer, a role and an interval and none "
            "is joined.",
            "CYCLE36_CAREER_CORPUS.json",
        ),
        "MR35R-07": (
            "PARTIALLY_REPAIRED",
            "One general crosswalk with effective-dated rename evidence; 108,355 "
            "of 110,044 cells resolve. 20 historical display names remain "
            "unresolved with named reasons.",
            "CYCLE36_PROGRAM_CROSSWALK.json",
        ),
        "MR35R-08": (
            "REPAIRED_AND_CONTAINED",
            "Arithmetic resolved per row against the producer's own population; "
            "all 36 PROVEN labels superseded; the consumer gate admits zero and "
            "that zero is honest.",
            "CYCLE36_KERNEL_RECONCILIATION.json",
        ),
        "MR35R-09": (
            "REPRODUCED_AND_REPAIRED",
            "Selection is a function of declared vintage; input permutation "
            "cannot change it; same-vintage disagreement fails closed.",
            "CYCLE36_NEUTRAL_TRAVEL.json",
        ),
        "MR35R-10": (
            "QUALIFIED_ACTIVATION_STILL_BLOCKED",
            "Composed successor reproduced independently with eleven negative "
            "controls. Activation remains an explicit human decision.",
            "CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION.json",
        ),
        "MR35R-11": (
            "ADDRESSED_AS_A_TRACE_NOT_AN_IMPLEMENTATION",
            "All 34 pinned owner documents rehashed against their recorded "
            "remote digests and extracted section by section: 22 current "
            "documents carrying CAP-0574 to CAP-0595, 12 retained carrying "
            "CAP-0070 to CAP-0081, 249 sections, every capability resolved "
            "from document metadata rather than a filename, and one "
            "front-matter contradiction referred to the owner. This "
            "establishes that the current hierarchy was read, not that BAS "
            "implements it: 33 of 34 capabilities have no BAS code behind "
            "them and the dependent C01/Film section union beyond AREA-24 is "
            "still unread.",
            "CYCLE36_ALL22_SECTION_TRACE.json",
        ),
        "MR35R-12": (
            "REPAIRED_FOR_QUALIFICATION",
            "Wheel physically qualified in isolation, 14 of 14 validator probes "
            "agree, field matrix published. Owner adoption remains open.",
            "CYCLE36_ALL22_CONTRACT_COMPATIBILITY.json",
        ),
    }
    rows = []
    for finding in inherited:
        key = finding.get("finding_id")
        state, detail, evidence = dispositions.get(
            key, ("NOT_ADDRESSED", "No Cycle #36 work targeted this finding.", None)
        )
        rows.append(
            {
                "finding_id": key,
                "original_title_verbatim": finding.get("title"),
                "original_state_verbatim": finding.get("state"),
                "required_successor": finding.get("required_successor"),
                "cycle36_disposition": state,
                "cycle36_detail": detail,
                "before_evidence": [
                    item.get("path") for item in finding.get("evidence") or []
                ],
                "after_evidence": str(run / evidence) if evidence else None,
                "scientific_acceptance": False,
            }
        )
    new_findings = [
        {
            "finding_id": "C36-N01",
            "severity": "P2",
            "state": "FOUND_AND_FIXED_IN_THIS_CYCLE",
            "title": (
                "The first version of the Family B probe demanded both "
                "validators reject every control, producing three false findings."
            ),
            "detail": (
                "A control that tampers with a downstream-only file must be "
                "rejected downstream and legitimately passes upstream. The "
                "control now declares which side must fail."
            ),
            "after_evidence": str(run / "CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION.json"),
        },
        {
            "finding_id": "C36-N02",
            "severity": "P2",
            "state": "FOUND_AND_FIXED_IN_THIS_CYCLE",
            "title": (
                "The first rename acquisition left HTML character references "
                "encoded, so a present institution read as absent."
            ),
            "detail": (
                "The A&M System page writes 'Texas A&#038;M'. Resolving "
                "references is part of reading the bytes."
            ),
            "after_evidence": str(run / "CYCLE36_PROGRAM_RENAME_SOURCES.json"),
        },
        {
            "finding_id": "C36-N03",
            "severity": "P2",
            "state": "FOUND_AND_FIXED_IN_THIS_CYCLE",
            "title": (
                "The first finals reconciliation read a 'lifecycle' key the "
                "source never writes, reporting one contest and zero finals."
            ),
            "detail": (
                "The NCAA scoreboard feed carries game_state and "
                "status_code_display. Reading the fields it actually uses "
                "reproduces 770 observations, 468 contests and 290 finals."
            ),
            "after_evidence": str(run / "CYCLE36_FORECAST_AND_FINALS.json"),
        },
        {
            "finding_id": "C36-N07",
            "severity": "P1",
            "state": "FOUND_AND_FIXED_IN_THIS_CYCLE",
            "title": (
                "The R36-02 policy correction left both instruction seals "
                "stale, and only the full suite could see it."
            ),
            "detail": (
                "Appending the SHA-scoped correction took "
                "instructions/policies/execution_focus_policy.json from 26,186 "
                "to 27,228 bytes. instructions/manifest.json and "
                "instructions/FILE_HASHES.sha256 both carry its digest and "
                "neither moved, so test_instructions_pack and "
                "test_autonomous_control_tools failed in the mounted and "
                "unmounted full suites. The focused lanes this cycle added do "
                "not touch the instruction seal, so a repair that was itself "
                "incomplete looked finished. Regenerated through "
                "tools/generate_instruction_manifest.py; --check is clean."
            ),
            "after_evidence": "instructions/manifest.json",
        },
        {
            "finding_id": "C36-N08",
            "severity": "P2",
            "state": "FOUND_AND_OPEN",
            "title": (
                "The repository-wide discover lane cannot import any cycle "
                "package, so it never executed the Cycle #36 tests."
            ),
            "detail": (
                "unittest discover at the repository root reports "
                "ModuleNotFoundError for aggie_analytics.cycle36, and "
                "identically for cycle30, cycle33, cycle34 and cycle35: an "
                "installed distribution named aggie_analytics shadows the "
                "checkout's src for every module imported after it. 65 of the "
                "baseline's 84 findings and 75 of this head's are this one "
                "defect. The Cycle #36 tests run and pass in the focused and "
                "true-unmounted lanes; the full-suite lane proves nothing "
                "about them either way. Repairing the import root is a "
                "cross-cutting harness change that would alter what every "
                "historical lane measured, so it is recorded rather than "
                "changed inside this cycle."
            ),
            "after_evidence": "CYCLE36_VALIDATION_RESULTS.json",
        },
        {
            "finding_id": "C36-N09",
            "severity": "P1",
            "state": "FOUND_AND_FIXED_IN_THIS_CYCLE",
            "title": (
                "Two acceptance clauses were reported met while the code "
                "measured something narrower."
            ),
            "detail": (
                "The independent season reader checked one evidence tier and "
                "so read 5,123 of 16,428 labelled rows while the artifact "
                "said it checked every admitted season-support tuple; it now "
                "reads all of them and confirms 9,110 bound seasons with zero "
                "disagreements. The unresolved-alias state was named "
                "UNRESOLVED_NAME_ABSENT_FROM_EVERY_DECLARED_SOURCE_PAYLOAD "
                "when the code had tested two normalised lookups, and the "
                "payloads do name fifteen of the twenty under another "
                "spelling. Both were found by reading delivered rows against "
                "the pack, not by a failing test, which is why the suites "
                "were green while the claims were wrong."
            ),
            "after_evidence": "CYCLE36_INDEPENDENT_SEASON_REVIEW.json",
        },
        {
            "finding_id": "C36-N06",
            "severity": "P1",
            "state": "FOUND_AND_OPEN",
            "title": (
                "53 of 266 declared staff acquisition attempts have no cached "
                "capture whose bytes hash to their declared receipt identity."
            ),
            "detail": (
                "The successor binds a capture to a program only by content "
                "digest, so those attempts stay unbound and their staff rows "
                "carry no program. That accounts for 54 of the 88 programs "
                "with a predecessor assertion the successor cannot match. "
                "Either the cache lost those files or the ledger digests are "
                "stale; both are evidence-integrity questions for the "
                "acquisition lane, and neither is repaired by loosening the "
                "binding."
            ),
            "after_evidence": str(run / "CYCLE36_PREDECESSOR_RECONCILIATION.json"),
        },
        {
            "finding_id": "C36-N05",
            "severity": "P1",
            "state": "FOUND_AND_FIXED_IN_THIS_CYCLE",
            "title": (
                "Two full-cache staff ingests ran concurrently against one "
                "output path, producing an artifact that was the output of "
                "neither."
            ),
            "detail": (
                "An earlier background run was still alive with an open handle "
                "and kept writing at its own offsets. It also halved the "
                "throughput of the run that replaced it. The stale process was "
                "terminated, the artifact regenerated, and every producer now "
                "writes atomically and verifies its own output."
            ),
            "after_evidence": str(run / "CYCLE36_FULL_STAFF_INGEST.json"),
        },
        {
            "finding_id": "C36-N04",
            "severity": "P1",
            "state": "FOUND_AND_OPEN",
            "title": (
                "Cycle #33 span location rebuilt three per-character offset maps "
                "per lookup, making a whole-cache staff pass take hours."
            ),
            "detail": (
                "Memoised in span_locate with identical outputs; the existing "
                "cycle33/cycle35 span tests still pass. The underlying quadratic "
                "shape remains for any future caller that does not hit the cache."
            ),
            "after_evidence": str(run / "CYCLE36_VALIDATION_RESULTS.json"),
        },
    ]
    return {
        "artifact_type": "CYCLE36_FINDING_DISPOSITION",
        "generated_at_utc": utc_now(),
        "inherited_findings": rows,
        "inherited_count": len(rows),
        "new_findings": new_findings,
        "new_count": len(new_findings),
        "every_inherited_finding_dispositioned": all(
            row["cycle36_disposition"] != "NOT_ADDRESSED" for row in rows
        ),
    }


def build(out_dir: Path, run: Path, repo: Path) -> dict[str, Any]:
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    rows = requirement_rows(run)
    findings = finding_dispositions(run)

    _bas_atomic.write_text(run / "CYCLE36_REQUIREMENT_STATUS.json", 
        json.dumps(
            {
                "artifact_type": "CYCLE36_REQUIREMENT_STATUS",
                "generated_at_utc": utc_now(),
                "source_head": head,
                "source_tree": tree,
                "requirements": rows,
                "dimensions_reported_independently": [
                    "implementation",
                    "data_evidence",
                    "software_validation",
                    "independent_scientific_acceptance",
                    "integration_release",
                    "overall",
                ],
                "implementer_cannot_grant_acceptance": True,
                "hold": "PRESERVE_ACTIVE",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    _bas_atomic.write_text(run / "CYCLE36_FINDING_DISPOSITION.json", 
        json.dumps(findings, indent=2, sort_keys=True), encoding="utf-8"
    )

    members = []
    missing = []
    for name, requirement in DECLARED_MEMBERS:
        path = run / name
        if path.is_file():
            members.append(
                {
                    "path": name,
                    "requirement": requirement,
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
        else:
            missing.append({"path": name, "requirement": requirement})

    validation = read_json(run / "CYCLE36_VALIDATION_RESULTS.json") or {}
    release = read_json(run / "CYCLE36_DELIVERED_RELEASE_MANIFEST.json") or {}
    population = read_json(run / "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json") or {}
    staff = read_json(run / "CYCLE36_FULL_STAFF_INGEST.json") or {}

    packet = {
        "artifact_type": "CYCLE36_PACKET_MANIFEST",
        "generated_at_utc": utc_now(),
        "source_head": head,
        "source_tree": tree,
        "source_branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "data_root": DATA_ROOT,
        "run_directory": str(run),
        "members": members,
        "member_count": len(members),
        "declared_but_absent": missing,
        "declared_but_absent_count": len(missing),
        "lanes": validation.get("lanes") or [],
        "delivered_release": release.get("database"),
        "delivered_release_sha256": release.get("database_sha256"),
        "predecessor_releases_untouched": [
            r"...\ops\cycle35\runs\20260921T055921Z_implementation\release_r4"
        ],
        "resealed_outside_git": (
            "This packet is sealed after the final source commit and is not "
            "itself committed, so no commit exists solely to record its own "
            "digest."
        ),
    }
    counts = {
        "program_seasons": population.get("program_season_keys") or 0,
        "staff_rows": staff.get("observation_rows") or 0,
    }
    validation_result = {
        "artifact_type": "CYCLE36_PACKET_VALIDATION",
        "generated_at_utc": utc_now(),
        "findings": [
            check_head_binding(packet, head, tree),
            check_member_digests(packet, run),
            check_data_root(packet, DATA_ROOT),
            check_command_receipts(packet),
            check_lane_head_currency(packet, validation),
            check_population_not_empty(counts, ("program_seasons", "staff_rows")),
            check_selected_release_is_the_successor(
                release.get("database"),
                release.get("database") or "",
                [
                    str(
                        Path(
                            r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs"
                            r"\20260921T055921Z_implementation\release_r4"
                            r"\CYCLE35_COACHING_RELEASE_coverage.sqlite"
                        )
                    )
                ],
            ),
            check_unknown_not_converted(
                {
                    "season_unknown_rows": "UNKNOWN",
                    "independently_proven_pit_rows": "ZERO",
                    "scientific_acceptance_unknown": "NOT_REVIEWED",
                }
            ),
        ],
    }
    states = {finding["state"] for finding in validation_result["findings"]}
    validation_result["overall"] = (
        "FAIL" if "FAIL" in states else ("UNAVAILABLE" if "UNAVAILABLE" in states else "OK")
    )
    _bas_atomic.write_text(run / "CYCLE36_PACKET_MANIFEST.json", 
        json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8"
    )
    _bas_atomic.write_text(run / "CYCLE36_PACKET_VALIDATION.json", 
        json.dumps(validation_result, indent=2, sort_keys=True), encoding="utf-8"
    )
    return {
        "requirements": rows,
        "findings": findings,
        "packet": packet,
        "packet_validation": validation_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=ROOT)
    args = parser.parse_args()
    result = build(args.run_dir, args.run_dir, args.repo.resolve())
    print(
        json.dumps(
            {
                "requirements": len(result["requirements"]),
                "inherited_findings": result["findings"]["inherited_count"],
                "new_findings": result["findings"]["new_count"],
                "packet_members": result["packet"]["member_count"],
                "declared_but_absent": result["packet"]["declared_but_absent_count"],
                "packet_validation": result["packet_validation"]["overall"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
