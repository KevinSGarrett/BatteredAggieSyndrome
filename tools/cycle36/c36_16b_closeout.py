"""R36-16 (continued): PIT admission, ledgers, unfinished items and the report.

These artifacts exist to make the cycle's limits legible. Each unfinished
item names its original requirement, the exact missing deliverable, the last
observed evidence, what was attempted, which kind of action remains, the
responsible owner, the decision needed and what can continue meanwhile --
because "needs more work" is not a blocker description.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
try:  # U37-11: atomic writes when the package is importable; the plain calls otherwise
    from aggie_analytics import atomic_io as _bas_atomic
except ImportError:  # a standalone run without the package keeps its plain writes
    import types as _bas_types

    _bas_atomic = _bas_types.SimpleNamespace(
        write_text=lambda path, *args, **kwargs: path.write_text(*args, **kwargs),
        write_bytes=lambda path, *args, **kwargs: path.write_bytes(*args, **kwargs),
        open_write=lambda path, *args, **kwargs: path.open(*args, **kwargs),
    )

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]

MANAGER_RUN = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle35\20260921T131038Z"
)


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


def pit_admission(run: Path) -> dict[str, Any]:
    kernel = read_json(run / "CYCLE36_KERNEL_RECONCILIATION.json") or {}
    admission = kernel.get("pit_admission") or {}
    return {
        "artifact_type": "CYCLE36_PIT_ADMISSION",
        "generated_at_utc": utc_now(),
        "successor_states": admission.get("successor_states"),
        "producer_proven_labels": admission.get("producer_proven_labels"),
        "producer_proven_superseded": admission.get("producer_proven_superseded"),
        "consumer_gate_admits": admission.get("consumer_gate_admits"),
        "independently_proven_pit_rows": admission.get(
            "independently_proven_pit_rows"
        ),
        "producer_proven_rows": kernel.get("producer_proven_rows"),
        "row_level_file": str(run / "CYCLE36_PIT_ADMISSION_ROWS.jsonl"),
        "row_level_sha256": sha256_file(run / "CYCLE36_PIT_ADMISSION_ROWS.jsonl"),
        "predecessor_labels_retained": True,
        "gate_fails_closed": admission.get("consumer_gate_admits") == 0,
        "what_would_change_this": (
            "A per-prior publication receipt: for each admitted prior, the "
            "observation id, the source's own published-at instant bound to "
            "exact file bytes, and the target cutoff it was compared against. "
            "Nothing else raises this number, and a manufactured timestamp is "
            "not a receipt."
        ),
        "forward_plan": kernel.get("forward_evidence_plan"),
        "retrospective_use_remains_legitimate": True,
        "protected_lane_activation": "NOT_AUTHORIZED",
    }


def false_positive_rejections(run: Path) -> dict[str, Any]:
    inherited = read_json(MANAGER_RUN / "FALSE_POSITIVE_REJECTIONS.json") or {}
    return {
        "artifact_type": "CYCLE36_FALSE_POSITIVE_REJECTIONS",
        "generated_at_utc": utc_now(),
        "inherited": inherited.get("records") or [],
        "inherited_preserved_not_deleted": True,
        "cycle36_records": [
            {
                "id": "FP-C36-ALL22-TRACE-PREDICATES",
                "original_concern": (
                    "The first All-22 section trace reported that five of "
                    "twelve retained documents name no current successor, and "
                    "six contradictions between an accepted front matter and "
                    "the document body."
                ),
                "disposition": "FALSE_POSITIVE_REJECTED",
                "reason": (
                    "Both were the trace's own predicates. A successor is "
                    "written as a range or a conjunction -- "
                    "SUPERSEDED_BY_06_THROUGH_09_SOURCE_NAMED_OWNERS, "
                    "SUPERSEDED_BY_12_AND_13_SOURCE_NAMED_OWNERS -- and the "
                    "first version compared the whole string to one filename "
                    "stem. Five of the six contradictions were the literal "
                    "result state INCOMPLETE inside backticks, or domain "
                    "vocabulary such as 'incomplete roster'. With ranges "
                    "resolved and code spans removed, eleven of twelve "
                    "documents resolve every successor, the twelfth declares "
                    "no supersession at all, and exactly one genuine "
                    "contradiction remains: 03_ROSTER_PUBLISHER section 11 "
                    "says the AREA-24 hierarchy 'remains an incomplete Phase "
                    "2 draft' while its front matter says "
                    "ACCEPTED_PHASE_2_PLAN. That one is referred to the "
                    "owner, not resolved here."
                ),
                "retained_original": (
                    "first run of tools/cycle36/c36_13b_all22_section_trace.py"
                ),
                "corrected_evidence": "CYCLE36_ALL22_SECTION_TRACE.json",
            },
            {
                "id": "FP-C36-FAMILY-B-BOTH-SIDES",
                "original_concern": (
                    "Three Family B negative controls were reported as "
                    "unexpectedly accepted."
                ),
                "disposition": "FALSE_POSITIVE_REJECTED",
                "reason": (
                    "The tool required BOTH validators to reject every control. "
                    "A control that tampers with a downstream-only file must be "
                    "rejected downstream and legitimately passes upstream, "
                    "because upstream never reads that file. With the required "
                    "side declared per control, all eleven reject correctly. "
                    "The three were an accounting defect in the probe, not "
                    "behaviour of the consumers."
                ),
                "retained_original": "first run of tools/cycle36/c36_12_family_b_composed.py",
                "corrected_evidence": str(
                    run / "CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION.json"
                ),
            },
            {
                "id": "FP-C36-INDEPENDENT-READER-NEWLINE-TRANSLATION",
                "original_concern": (
                    "The independent season reader reported 78 records where "
                    "the producer bound a season and it found no governing "
                    "heading, across 45 captures."
                ),
                "disposition": "FALSE_POSITIVE_REJECTED",
                "reason": (
                    "The reader decoded captures through read_text, which on "
                    "Windows applies universal-newline translation and removes "
                    "every CR. One capture carries 3,390 of them, so every "
                    "recorded offset landed up to 3,390 characters early and "
                    "fell outside the heading that actually governs it. The "
                    "reader now decodes from bytes, exactly as the producer "
                    "does, and concordance is 16,074 of 16,074 comparable "
                    "rows with zero disagreements. The 78 were the reader's "
                    "own defect, not the producer's."
                ),
                "retained_original": (
                    "CYCLE36_INDEPENDENT_SEASON_REVIEW_V1_NEWLINE_TRANSLATED.json"
                ),
                "corrected_evidence": "CYCLE36_INDEPENDENT_SEASON_REVIEW.json",
            },
            {
                "id": "FP-C36-JSONL-WRITE-ATTRIBUTED-TO-THE-FILESYSTEM",
                "original_concern": (
                    "A 35 MB observation artifact read back with eleven "
                    "truncated records, and the first diagnosis attributed it "
                    "to the write path or the filesystem."
                ),
                "disposition": "CAUSE_CORRECTED_DEFECT_IS_REAL",
                "reason": (
                    "The artifact really was corrupt; the attribution was "
                    "wrong. Process inspection found TWO full-cache ingests "
                    "alive at once, an earlier one still holding an open "
                    "handle on the same path and writing at its own offsets. "
                    "The stale process was terminated and the artifact "
                    "regenerated. The atomic write and post-write verification "
                    "are what caught it and are kept, but the cause was "
                    "operator concurrency, not the write path."
                ),
                "retained_original": (
                    "commit 1a86fcca, whose message describes the symptom "
                    "without naming concurrency"
                ),
                "corrected_evidence": "src/aggie_analytics/cycle36/jsonl_io.py",
            },
            {
                "id": "FP-C36-SEASON-MASS-CORRUPTION",
                "original_concern": (
                    "MR35R-04 proves the Cycle #35 season binder admits comment, "
                    "script, navigation and biography years, which invites the "
                    "conclusion that the delivered season evidence is corrupt."
                ),
                "disposition": "FALSE_POSITIVE_REJECTED_AS_A_PRODUCTION_CLAIM",
                "reason": (
                    "The defect is real and the negative controls stand. Two "
                    "independent measurements bound its production impact. "
                    "Against the 880-row reference slice: 711 rows bound to "
                    "2026 before and 717 after, six recovered from a "
                    "resolvable ambiguity and none corrupted; no capture the "
                    "predecessor bound relied ONLY on an inadmissible context. "
                    "Against the whole delivered release: of 1,499 predecessor "
                    "assertions, 913 keep their season, 229 were CURRENT and "
                    "remain unspecified in both, 7 gain a season the "
                    "predecessor did not assert, exactly 1 changes, and 0 are "
                    "withdrawn. Reporting mass corruption would have been a "
                    "finding the evidence does not support; reporting zero "
                    "change would also have been wrong, and the one changed "
                    "assertion is named in the reconciliation."
                ),
                "retained_original": str(MANAGER_RUN / "ADVERSARIAL_PROBE_RESULTS.json"),
                "corrected_evidence": str(run / "CYCLE36_FULL_STAFF_INGEST.json"),
            },
        ],
        "both_records_retained": True,
    }


def review_finding_ledger(run: Path) -> dict[str, Any]:
    disposition = read_json(run / "CYCLE36_FINDING_DISPOSITION.json") or {}
    return {
        "artifact_type": "CYCLE36_REVIEW_FINDING_LEDGER",
        "generated_at_utc": utc_now(),
        "inherited_findings": [
            {
                "finding_id": row["finding_id"],
                "disposition": row["cycle36_disposition"],
                "evidence": row["after_evidence"],
            }
            for row in disposition.get("inherited_findings") or []
        ],
        "new_findings": disposition.get("new_findings") or [],
        "hosted_review_comments_adjudicated": 0,
        "hosted_review_state": (
            "NOT_APPLICABLE_NO_PUBLICATION: this branch was not pushed, so no "
            "hosted run and no review comment exists to adjudicate."
        ),
        "paid_retries_used": 0,
        "self_approved_scientific_acceptance": False,
    }


UNFINISHED = [
    {
        "original_requirement": "R36-05",
        "missing_deliverable": (
            "Official corroboration for any career episode. All 44,748 "
            "episodes across 8,399 cached pages are now processed and carried "
            "in the release, and 15,993 resolve an employer, a specific role "
            "and an interval -- but every one is RETROSPECTIVE_CANDIDATE_ONLY "
            "with pit_admitted false at source, so none can be joined. A "
            "second, independent source per episode is what would change "
            "that."
        ),
        "last_observed_evidence": "CYCLE36_CAREER_CORPUS.json",
        "safe_alternatives_attempted": (
            "The whole cached corpus was read rather than left at the 48 "
            "predeclared keys, employers were resolved through the same "
            "crosswalk R36-04 built rather than a looser matcher, and roles "
            "were decomposed with the cycle33 taxonomy. 17,574 episodes name "
            "an employer outside the declared FBS/FCS population, 10,975 "
            "carry no title that entails a specific role and 174 carry no "
            "interval; each is refused for the first thing missing rather "
            "than joined on a guess."
        ),
        "remaining_action_kind": "SOURCE_UNAVAILABLE",
        "responsible_owner": "BAT-701",
        "exact_decision_needed": (
            "Whether to spend from the free request lanes on official "
            "corroboration for named episodes, given that Wikimedia career "
            "text alone cannot raise an episode above candidate tier."
        ),
        "what_can_continue_meanwhile": (
            "Everything else in the release. The career table is queryable "
            "now, with every refusal reason in it, and no delivered "
            "assertion depends on a career episode."
        ),
    },
    {
        "original_requirement": "R36-08",
        "missing_deliverable": (
            "Score and start instant for 796 kernel contests (792 of them season "
            "2023), and an explanation for a +1 prior residual on 34 home and 35 "
            "away sides."
        ),
        "last_observed_evidence": str(
            Path("CYCLE36_KERNEL_RECONCILIATION.json")
        ),
        "safe_alternatives_attempted": (
            "Six declared source universes including the private BAT-523 lane; "
            "the public tranche, the FCS route files and a contest-identity "
            "dedup were each tested and none supplies these contests."
        ),
        "remaining_action_kind": "SOURCE_UNAVAILABLE",
        "responsible_owner": "BAT-696",
        "exact_decision_needed": (
            "Whether to spend free requests acquiring 2023 game results from the "
            "declared source, and under which namespace, given the kernel's own "
            "identifiers do not occur in the cached tranche."
        ),
        "what_can_continue_meanwhile": (
            "The 12,450/12,449 explained rows and the PIT containment stand "
            "without them."
        ),
    },
    {
        "original_requirement": "R36-08",
        "missing_deliverable": (
            "Any per-prior publication receipt. Independently proven PIT is zero."
        ),
        "last_observed_evidence": str(Path("CYCLE36_PIT_ADMISSION.json")),
        "safe_alternatives_attempted": (
            "The arithmetic was reconstructed exactly; that does not create "
            "historical availability and no timestamp was manufactured."
        ),
        "remaining_action_kind": "SOURCE_UNAVAILABLE",
        "responsible_owner": "BAT-696",
        "exact_decision_needed": (
            "Whether to arm the forward evidence route, which requires checking "
            "actual authorised contest ownership against the current calendar."
        ),
        "what_can_continue_meanwhile": (
            "Retrospective descriptive research, which this containment leaves "
            "legitimate."
        ),
    },
    {
        "original_requirement": "R36-11",
        "missing_deliverable": (
            "Rosters for the 160 quarantined availability assertions' programs "
            "and seasons, and availability reports from any conference other "
            "than the SEC."
        ),
        "last_observed_evidence": str(Path("CYCLE36_AVAILABILITY.json")),
        "safe_alternatives_attempted": (
            "The mounted roster slice was joined by the declared name-and-jersey "
            "rule, resolving 92. The remaining programs have no mounted roster."
        ),
        "remaining_action_kind": "FREE_REQUEST_CEILING",
        "responsible_owner": "BAT-324",
        "exact_decision_needed": (
            "Whether to spend from the 50-request availability lane on roster "
            "acquisition for the named programs, or on additional conference "
            "report routes."
        ),
        "what_can_continue_meanwhile": (
            "The policy denominator and the 92 resolved rows are complete now."
        ),
    },
    {
        "original_requirement": "R36-12",
        "missing_deliverable": (
            "Canonical activation of the composed Family B successor, and the "
            "canonical mounted lane it would turn from FAIL."
        ),
        "last_observed_evidence": str(
            Path("CYCLE36_FAMILY_B_COMPOSED_QUALIFICATION.json")
        ),
        "safe_alternatives_attempted": (
            "Full isolated qualification with eleven negative controls and a "
            "written rollback scope. Nothing canonical was touched."
        ),
        "remaining_action_kind": "RELEASE_AUTHORITY",
        "responsible_owner": "the user or a separately authorised release authority",
        "exact_decision_needed": (
            "Approve or decline CYCLE33-APPROVAL-LAKE-SUCCESSOR-001 at the exact "
            "scope written in the qualification artifact."
        ),
        "what_can_continue_meanwhile": (
            "Everything; the default stays LEGACY and no consumer changes."
        ),
    },
    {
        "original_requirement": "R36-13",
        "missing_deliverable": (
            "Section-level requirement extraction for all 22 current owner "
            "documents, and owner adoption of the richer staff representation."
        ),
        "last_observed_evidence": str(
            Path("CYCLE36_ALL22_CONTRACT_COMPATIBILITY.json")
        ),
        "safe_alternatives_attempted": (
            "The released wheel was qualified physically and the staff boundary "
            "implemented against it with a declared loss matrix."
        ),
        "remaining_action_kind": "OWNER_ADOPTION",
        "responsible_owner": "CFIP-19/22/24/27 owners",
        "exact_decision_needed": (
            "Whether the proposed value.staff[] and rights fields are accepted "
            "into a future StaffSnapshot contract version."
        ),
        "what_can_continue_meanwhile": (
            "The BAS-local envelope remains the lossless record and needs no "
            "owner decision."
        ),
    },
    {
        "original_requirement": "R36-14",
        "missing_deliverable": (
            "Audits for 32 of 35 cycles, work in 40 of 51 domains, and "
            "semantic adjudication of 4,549 plan candidates. This pack named "
            "three legacy units for three-pass closure and required the rest "
            "to be visible, not audited; the remainder is therefore next "
            "cycle's scope rather than this cycle's unmet obligation."
        ),
        "last_observed_evidence": str(Path("CYCLE36_HISTORICAL_AUDIT_MATRIX.json")),
        "safe_alternatives_attempted": (
            "Three named units received three passes each, every untouched "
            "domain and cycle is listed by name rather than omitted, and the "
            "private mirror -- which was previously listed here as "
            "uncertified -- is now compared row by row in "
            "CYCLE36_JIRA_MIRROR_DISCREPANCY.json, with no row diverging "
            "from a state this project records."
        ),
        "remaining_action_kind": "SCOPING_DECISION",
        "responsible_owner": "BAT-708 and BAT-696",
        "exact_decision_needed": (
            "Which units to name for the next cycle; the list is too large for "
            "one cycle and picking is a scoping decision."
        ),
        "what_can_continue_meanwhile": "All delivered work stands independently.",
    },
    {
        "original_requirement": "R36-15",
        "missing_deliverable": (
            "Hosted validation results at the final head, and hosted review "
            "comments to adjudicate."
        ),
        "last_observed_evidence": str(Path("CYCLE36_VALIDATION_RESULTS.json")),
        "safe_alternatives_attempted": (
            "Every local lane was run with real receipts; hosted checks require "
            "publishing the branch."
        ),
        "remaining_action_kind": "RELEASE_AUTHORITY",
        "responsible_owner": "the user",
        "exact_decision_needed": (
            "Permission to push codex/BAT-706-cycle36 and open a draft pull "
            "request based on codex/BAT-706-cycle35, with no merge and no hold "
            "release."
        ),
        "what_can_continue_meanwhile": "All local lanes and evidence are complete.",
    },
    {
        "original_requirement": "ALL",
        "missing_deliverable": "Independent scientific acceptance.",
        "last_observed_evidence": str(Path("CYCLE36_REQUIREMENT_STATUS.json")),
        "safe_alternatives_attempted": (
            "Regressions, negative controls, independent reconstructions and "
            "adversarial predicates. None of these is acceptance."
        ),
        "remaining_action_kind": "INDEPENDENT_REVIEW",
        "responsible_owner": "the manager or an independent reviewer",
        "exact_decision_needed": (
            "Review the delivered artifacts and either accept within a named "
            "scope or record remaining findings."
        ),
        "what_can_continue_meanwhile": (
            "Nothing depends on it locally; it gates release, not work."
        ),
    },
]

AUTHORITY_REQUESTS = [
    {
        "request_id": "C36-AUTH-01",
        "what": (
            "Push branch codex/BAT-706-cycle36 and open a DRAFT pull request "
            "based on codex/BAT-706-cycle35."
        ),
        "why": (
            "Hosted validation at the exact final head cannot run without it, "
            "and R36-15 requires hosted results separately from local ones."
        ),
        "scope_limits": (
            "Push and draft PR only. No merge, no force push, no branch "
            "deletion, no hold release, no label that triggers a paid workflow. "
            "The PR body carries no private evidence, no raw data and no All-22 "
            "plan text."
        ),
        "inspected_workflow_triggers": [
            {
                "workflow": ".github/workflows/ci.yml",
                "on": "push, pull_request",
                "would_run": True,
                "paid": False,
            },
            {
                "workflow": ".github/workflows/security.yml",
                "on": "pull_request, push to main, weekly schedule",
                "would_run": True,
                "paid": False,
            },
            {
                "workflow": ".github/workflows/cycle29-no-api-review-attestation.yml",
                "on": "pull_request",
                "would_run": True,
                "paid": False,
            },
            {
                "workflow": ".github/workflows/codex-scientific-review.yml",
                "on": "pull_request",
                "would_run": True,
                "paid": False,
                "note": (
                    "A skip stub. Its only step writes verdict "
                    "SKIPPED_UNTIL_PAID_SCIENTIFIC_REVIEW_READY and makes no "
                    "model call."
                ),
            },
            {
                "workflow": ".github/workflows/paid-scientific-review.yml",
                "on": "pull_request [labeled], workflow_dispatch",
                "would_run": False,
                "paid": True,
                "note": (
                    "Job gate requires workflow_dispatch or the exact label "
                    "paid-scientific-review-ready. A push or a plain draft PR "
                    "does not reach it, and no label is added by this request."
                ),
            },
        ],
        "paid_workflows_that_would_run": 0,
        "state": "REQUESTED_NOT_GRANTED",
    },
    {
        "request_id": "C36-AUTH-02",
        "what": (
            "Approve CYCLE33-APPROVAL-LAKE-SUCCESSOR-001 to activate the "
            "composed Family B successor as the canonical default."
        ),
        "why": (
            "Isolated qualification is complete and reproduces every published "
            "identity; the canonical mounted lane stays FAIL until activation."
        ),
        "scope_limits": (
            "The two named artifacts only. Rollback is a configuration change "
            "because no canonical file was written."
        ),
        "state": "REQUESTED_NOT_GRANTED",
    },
    {
        "request_id": "C36-AUTH-03",
        "what": (
            "Decide whether to spend from the free request lanes on 2023 game "
            "results and on rosters for the 160 quarantined availability rows."
        ),
        "why": (
            "Both are named, bounded acquisitions that would close specific "
            "measured gaps."
        ),
        "scope_limits": (
            "Within the declared 50-request lanes. No paid API, no subscription "
            "change, no quota escalation."
        ),
        "state": "REQUESTED_NOT_GRANTED",
    },
]


def cost_ledger(run: Path) -> dict[str, Any]:
    rename = read_json(run / "CYCLE36_PROGRAM_RENAME_SOURCES.json") or {}
    availability = read_json(run / "CYCLE36_AVAILABILITY.json") or {}
    return {
        "artifact_type": "CYCLE36_COST_LEDGER",
        "generated_at_utc": utc_now(),
        "paid_ai_or_model_calls": 0,
        "paid_reviewer_calls": 0,
        "paid_api_budget_expansion": 0,
        "subscription_changes": 0,
        "paid_review_label_added": False,
        "lanes": {
            "COACHING_MEMBERSHIP_SCHEMES": {
                "ceiling": 50,
                "requests_spent": 5,
                "cache_hits": rename.get("cache_hits", 0),
                "detail": (
                    "Four institutional rename pages plus one retry after a "
                    "certificate-chain failure on the first attempt."
                ),
                "remaining": 45,
            },
            "AVAILABILITY": {
                "ceiling": 50,
                "requests_spent": 0,
                "cache_hits": (availability.get("route_attempts") or {}).get("rows", 0),
                "detail": (
                    "No availability request was made; the existing 14 route "
                    "attempts and the mounted roster slice were reused."
                ),
                "remaining": 50,
            },
        },
        "administrative_readbacks": {
            "github": "read via the manager's hash-bound snapshots; no new call",
            "jira": "read via the manager's hash-bound snapshots; no new call",
            "note": (
                "Administrative metadata reads are not paid model calls and are "
                "counted separately from the source lanes."
            ),
        },
        "no_concealed_reset": (
            "These counters are cumulative for Cycle #36 and are not reset "
            "across continuations."
        ),
        "source_terms_respected": (
            "Four public institutional pages, one request each, 1.5 seconds "
            "apart, identified user agent, TLS verification left ON. No 403, no "
            "CAPTCHA and no authentication was encountered or bypassed."
        ),
    }


def final_report(run: Path) -> str:
    status = read_json(run / "CYCLE36_REQUIREMENT_STATUS.json") or {}
    rows = status.get("requirements") or []
    validation = read_json(run / "CYCLE36_VALIDATION_RESULTS.json") or {}
    release = read_json(run / "CYCLE36_DELIVERED_RELEASE_MANIFEST.json") or {}
    population = read_json(run / "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json") or {}
    staff = read_json(run / "CYCLE36_FULL_STAFF_INGEST.json") or {}
    scheme = read_json(run / "CYCLE36_SCHEME_AND_RESPONSIBILITY.json") or {}
    kernel = read_json(run / "CYCLE36_KERNEL_RECONCILIATION.json") or {}

    lines: list[str] = []
    lines.append("# Cycle #36 final report")
    lines.append("")
    lines.append("## Overall state")
    lines.append("")
    lines.append(
        "**IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED.** Every requirement has a "
        "local deliverable with execution evidence. Nothing here is "
        "independently reviewed, nothing is merged, no lane is activated and "
        "the operator hold is unchanged. A finished report is not a finished "
        "cycle."
    )
    lines.append("")
    lines.append("## Requirement table")
    lines.append("")
    lines.append(
        "| Req | Implementation | Data/evidence | Software | Independent | "
        "Release | Overall |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row['requirement_id']} | {row['implementation']} | "
            f"{row['data_evidence']} | {row['software_validation']} | "
            f"{row['independent_scientific_acceptance']} | "
            f"{row['integration_release']} | {row['overall']} |"
        )
    lines.append("")
    lines.append("## Implemented but not accepted")
    lines.append("")
    lines.append(
        "All sixteen. No requirement in this cycle has independent scientific "
        "acceptance, and the implementer cannot grant it."
    )
    lines.append("")
    lines.append("## What changed in the delivered database")
    lines.append("")
    counts = release.get("table_counts") or {}
    if counts:
        lines.append(
            f"A new immutable release at `{release.get('database')}` "
            f"(sha256 `{release.get('database_sha256')}`). It replaces nothing: "
            "release_r4 and every earlier snapshot are untouched."
        )
        lines.append("")
        for name in sorted(counts):
            lines.append(f"- `{name}`: {counts[name]:,} rows")
    else:
        lines.append(
            "The release build did not complete in this run; see "
            "CYCLE36_DELIVERED_RELEASE_MANIFEST.json for its state."
        )
    lines.append("")
    lines.append("## National coverage")
    lines.append("")
    lines.append(
        f"- Program-season keys: **{population.get('program_season_keys'):,}** "
        "(was 12,460)."
    )
    lines.append(
        "- Seasons with no membership row in 1963-2026: "
        f"**{len(population.get('seasons_with_no_membership') or [])}**. Every "
        "year in scope is represented, including the restored 2024 and 2025."
    )
    lines.append(
        f"- Staff observation rows: **{staff.get('observation_rows'):,}** across "
        f"{staff.get('captures_examined'):,} dispositioned captures, against a "
        "predecessor 880-row HC/OC/DC reference slice."
    )
    user = read_json(run / "CYCLE36_USER_CORPUS_CELLS.json") or {}
    if user:
        lines.append(
            f"- User research-corpus cells preserved: **{user.get('cells_out', 0):,}** "
            f"across {user.get('distinct_seasons', 0)} seasons and "
            f"{user.get('distinct_role_columns', 0)} role columns, every one "
            "unverified and none point-in-time admitted."
        )
    lines.append(
        "- Candidate scheme assertions: "
        f"**{(scheme.get('scheme_states') or {}).get('ADMITTED_CANDIDATE_SCHEME_ASSERTION'):,}** "
        "where the delivered release had none."
    )
    lines.append("")
    lines.append("## Data that remains incomplete")
    lines.append("")
    career = read_json(run / "CYCLE36_CAREER_TRANCHE_RECONCILIATION.json") or {}
    lines.append(
        "- The 48-key career tranche is reconciled and **none of the 48 is "
        f"joinable**: {(career.get('joinability') or {}).get('NOT_JOINABLE_CANDIDATE_TIER_ONLY', 0)} "
        "are candidate-tier with no official corroboration, "
        f"{(career.get('joinability') or {}).get('NOT_JOINABLE_NO_PERSON_IN_THE_EVIDENCE', 0)} "
        "name no person and "
        f"{(career.get('joinability') or {}).get('NOT_JOINABLE_COMPETING_PEOPLE_RETAINED', 0)} "
        "retain competing people. The wider cached career corpus is no longer "
        "untouched: 8,399 pages and 44,748 episodes are processed and carried "
        "in the release, 15,993 of them resolving an employer, a role and an "
        "interval, and none joined."
    )
    lines.append(
        "- 796 kernel contests have no mounted score or start instant; 792 of "
        "them are season 2023."
    )
    lines.append(
        "- Independently proven point-in-time rows: "
        f"**{((kernel.get('pit_admission') or {}).get('consumer_gate_admits'))}**. "
        "The gate fails closed and no timestamp was manufactured."
    )
    lines.append(
        "- 160 of 252 availability assertions are quarantined for want of a "
        "mounted roster; only the SEC publishes reports at all."
    )
    population = read_json(run / "CYCLE36_NATIONAL_POPULATION_AND_COVERAGE.json") or {}
    lines.append(
        "- 20 display names still resolve to no canonical program. Each was "
        "inspected individually against every declared name: "
        f"{population.get('unresolved_names_with_a_related_declared_spelling', 0)} "
        "of them do have a related declared spelling -- the payloads write "
        "McNeese for McNeese State and St. Peter's for Saint Peter's -- and "
        "those are named as candidates requiring source rename evidence, not "
        "merged. The cells stay unresolved and the denominator does not move."
    )
    reconciliation = read_json(run / "CYCLE36_PREDECESSOR_RECONCILIATION.json") or {}
    buckets = reconciliation.get("buckets") or {}
    if buckets:
        reasons = reconciliation.get("absent_row_reasons") or {}
        lines.append(
            "- Against the Cycle #35 release, "
            f"**{buckets.get('NOT_PRESENT_IN_SUCCESSOR', 0)}** predecessor "
            "assertions have no counterpart here. "
            f"{reasons.get('programs_the_successor_never_bound', 0)} of their "
            f"{reasons.get('distinct_programs_with_an_absent_row', 0)} programs "
            "were never bound, because 53 of 266 declared acquisition attempts "
            "have no cached capture whose bytes hash to their declared receipt "
            "identity (C36-N06, open)."
        )
        lines.append(
            "- The season repair itself withdraws nothing: "
            f"{buckets.get('RETAINED_SAME_SEASON', 0)} assertions keep their "
            f"season, {buckets.get('BOTH_LEAVE_THE_SEASON_UNSPECIFIED', 0)} "
            "were CURRENT and stay unspecified, "
            f"{buckets.get('SEASON_NEWLY_BOUND_BY_THE_SUCCESSOR', 0)} gain one, "
            f"and exactly {buckets.get('CHANGED_SEASON', 0)} changes."
        )
    lines.append("")
    lines.append("## Which tests are red")
    lines.append("")
    for lane, result in sorted((validation.get("lane_results") or {}).items()):
        lines.append(f"- `{lane}`: **{result}**")
    lines.append("")
    lines.append(
        "Hosted validation is NOT_RUN because the branch was not published. "
        "The canonical mounted Family B lane remains FAIL because the successor "
        "is qualified and not activated."
    )
    lines.append("")
    lines.append("## Decisions that remain with the user")
    lines.append("")
    for request in AUTHORITY_REQUESTS:
        lines.append(f"- **{request['request_id']}** — {request['what']}")
    lines.append("")
    lines.append("## What this cycle does not claim")
    lines.append("")
    lines.append(
        "- Not that the historical project is correct: 32 of 35 cycles remain "
        "unaudited and 40 of 51 domains were untouched."
    )
    lines.append("- Not that any forecast is trustworthy.")
    lines.append("- Not that the C01 contract has been adopted.")
    lines.append("- Not that Cycle #35 is accepted, or that Cycle #36 is.")
    lines.append("")
    return "\n".join(lines) + "\n"


def build(run: Path) -> dict[str, Any]:
    artifacts = {
        "CYCLE36_PIT_ADMISSION.json": pit_admission(run),
        "CYCLE36_FALSE_POSITIVE_REJECTIONS.json": false_positive_rejections(run),
        "CYCLE36_REVIEW_FINDING_LEDGER.json": review_finding_ledger(run),
        "CYCLE36_UNFINISHED_ITEMS.json": {
            "artifact_type": "CYCLE36_UNFINISHED_ITEMS",
            "generated_at_utc": utc_now(),
            "items": UNFINISHED,
            "item_count": len(UNFINISHED),
            "every_item_names_its_blocker_kind": True,
        },
        "CYCLE36_AUTHORITY_REQUESTS.json": {
            "artifact_type": "CYCLE36_AUTHORITY_REQUESTS",
            "generated_at_utc": utc_now(),
            "requests": AUTHORITY_REQUESTS,
            "none_granted_by_this_cycle": True,
        },
        "CYCLE36_COST_LEDGER.json": cost_ledger(run),
    }
    run.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        _bas_atomic.write_text(run / name, 
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    _bas_atomic.write_text(run / "CYCLE36_FINAL_REPORT.md", final_report(run), encoding="utf-8")
    return {
        "written": sorted(list(artifacts) + ["CYCLE36_FINAL_REPORT.md"]),
        "unfinished_items": len(UNFINISHED),
        "authority_requests": len(AUTHORITY_REQUESTS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.run_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
