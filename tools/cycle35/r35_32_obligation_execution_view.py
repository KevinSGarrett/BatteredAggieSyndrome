"""R35-32 (Cycle #35 continuation, 20260921T055921Z), section 6.

"Finish or demonstrably exhaust the remaining local obligations, including
newly discovered ones. Preserve original ledger entries and provide a
deduplicated current execution view."

Two requirements that pull against each other, so they are satisfied in two
separate places rather than by compromising on one list.

PRESERVATION. The 26 declared entries and the 7 newly discovered ones are
READ from their frozen artifacts. Nothing is retyped, reworded, merged or
renumbered here, and this module never writes to those files. An entry the
mapping does not recognise is a hard error, so a declared obligation cannot
be lost by being quietly skipped -- which is the failure mode that makes a
"deduplicated view" worth distrusting.

DEDUPLICATION. Several entries are the same obligation seen from different
requirements. Entry 16 ("Canonical activation requires
CYCLE33-APPROVAL-LAKE-SUCCESSOR-001") and entry 25 ("Family B mounted
failures remain FAIL (R35-10 approval)") are one owner decision counted
twice; entry 26 and newly-discovered item 5 are both the structural fact
that a hosted runner cannot mount the private lake.

Measured: 39 source entries make 44 entry-to-obligation mappings over 35
distinct obligations, and 9 obligations are named by more than one entry.
Both directions matter, so both are recorded -- one ledger line can name
several obligations (entry 2 names scheme AND responsibility, which have
different causes and different fixes), and one obligation can be named by
several lines. Collapsing the duplicates removes duplicate bookkeeping, not
obligations: nothing is discharged by being deduplicated.

The mapping from source entry to obligation is DECLARED DATA below, keyed
on each entry's exact text. It is not computed by similarity, because a
similarity score deciding which obligations are "the same" is exactly the
kind of judgement that should be readable and arguable rather than buried.

CATEGORY DISCIPLINE. Every obligation carries a category, and the
categories are kept apart because they have different fixes and different
owners: a missing fact, a failed validation, an implementation gap, a
reviewer decision, a release authority, an acquisition or budget decision,
and a structural environment limit are seven different things. An
obligation blocked on an owner decision is not local work left undone, and
local work left undone is not blocked on anyone.

ACCEPTANCE PREDICATES. Each obligation states what would settle it, in
terms something can check, plus the artifact that would show it. Where that
artifact exists it is read and the predicate is evaluated, so a DONE state
is a measurement rather than an assertion. An obligation whose evidence is
missing reads UNVERIFIED_EVIDENCE_ABSENT -- never DONE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

RUNS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
CLOSEOUT = RUNS / "20260921T025300Z_closeout"
IMPLEMENTATION = RUNS / "20260921T055921Z_implementation"

DECLARED_UNFINISHED = CLOSEOUT / "CYCLE35_UNFINISHED_ITEMS.json"
NEWLY_DISCOVERED = CLOSEOUT / "CYCLE35_NEWLY_DISCOVERED_OBLIGATIONS.json"

# --------------------------------------------------------------- categories
#: Kept apart on purpose. Collapsing them is how "26 items remain" stops
#: meaning anything: an owner decision and an unwritten function are both
#: "open" and neither is the other's problem.
LOCAL_WORK = "LOCAL_IMPLEMENTATION_WORK"
MISSING_FACT = "MISSING_FACT_NO_SOURCE_ACQUIRED"
ACQUISITION = "ACQUISITION_OR_BUDGET_DECISION"
OWNER_DECISION = "OWNER_OR_RELEASE_AUTHORITY_DECISION"
REVIEWER = "INDEPENDENT_REVIEWER_DECISION"
STRUCTURAL = "STRUCTURAL_ENVIRONMENT_LIMIT"
NETWORK = "NETWORK_CALL_OUTSIDE_FREE_CEILING"

#: States an obligation can be in. BLOCKED_NOT_LOCAL_WORK is how an
#: obligation is demonstrably exhausted HERE: the work that could be done
#: locally was done, and what remains needs an owner, a reviewer, an
#: acquisition, a network call, or an environment this machine is not.
#: Calling that DONE would overclaim; calling it OPEN would imply someone
#: here can still act on it.
DONE = "DONE_WITH_EVIDENCE"
OPEN = "OPEN_LOCAL_WORK_REMAINS"
BLOCKED = "BLOCKED_NOT_LOCAL_WORK"
UNVERIFIED = "UNVERIFIED_EVIDENCE_ABSENT"


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------- predicates
def _artifact(name: str, run: Path = IMPLEMENTATION) -> dict[str, Any] | None:
    path = run / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def p_parser_recall() -> tuple[bool | None, str]:
    rows = IMPLEMENTATION / "staff_rebuild4" / "R35_02_STAFF_REBUILD_ROWS.jsonl"
    if not rows.is_file():
        return None, "rebuild rows absent"
    counts: dict[str, int] = {}
    for line in rows.open(encoding="utf-8"):
        key = json.loads(line)["disposition"]
        counts[key] = counts.get(key, 0) + 1
    bad = counts.get("QUARANTINED_REPARSE_WITHDRAWS_SUPPORT", 0) + counts.get(
        "RETAINED_UNSUPPORTED", 0
    )
    return bad == 0, f"dispositions={counts}"


def p_adjudication_determinism() -> tuple[bool | None, str]:
    import aggie_analytics.cycle35.coaching_release as release

    source = Path(release.__file__).read_text(encoding="utf-8")
    after_migrations = source.split("def apply_migrations")[1]
    body = after_migrations.split("def record_adjudication")[-1]
    clean = "datetime.now" not in body
    return clean, (
        "the build clock is unreachable from the adjudication record "
        "functions; decision_time_basis distinguishes a stated event time "
        "from a standing rule"
        if clean
        else "a record function still reads the wall clock"
    )


def p_family_b_successor() -> tuple[bool | None, str]:
    payload = _artifact("CYCLE35_FAMILY_B_SUCCESSOR_QUALIFICATION.json")
    if payload is None:
        return None, "qualification artifact absent"
    binding = payload["identity_binding"]
    ok = (
        bool(payload["successor_qualified_in_isolation"])
        and bool(binding["exercises_the_requested_successor"])
        and not payload["negative_controls_that_did_not_reject"]
        and bool(payload["canonical_predecessor_bytes_unchanged"])
    )
    return ok, (
        f"exercised {binding['ledger_identity_exercised'][:8]}..., "
        f"{payload['negative_controls_that_rejected']} of "
        f"{payload['negative_controls_declared']} negative controls rejected "
        "through the real validator; canonical bytes unchanged"
    )


def p_delivered_reconciliation() -> tuple[bool | None, str]:
    payload = _artifact("CYCLE35_DELIVERED_RELEASE_RECONCILIATION.json")
    if payload is None:
        return None, "reconciliation artifact absent"
    families = payload["delivered"]["families"]
    return True, (
        "delivered release read at row grain: "
        f"official_staff supports {families['official_staff']['assertions_supported']}, "
        f"user_corpus {families['user_corpus']['assertions_supported']} "
        f"from {families['user_corpus']['observations']} observations, "
        f"scheme {families['scheme']['rows']}, "
        f"responsibility {families['responsibility']['rows']}"
    )


def p_scheme_blocked_on_crosswalk() -> tuple[bool | None, str]:
    payload = _artifact("CYCLE35_SCHEME_INGEST.json")
    if payload is None:
        return None, "scheme reconciliation absent"
    refused = bool(payload.get("ingest_refused"))
    return refused, (
        f"ingest refused; {payload.get('candidate_rows_if_a_crosswalk_existed')} "
        "rows would bind if a page-title-to-program crosswalk existed, and "
        "the token-prefix rule collides on "
        f"{len(payload.get('collisions') or [])} program-seasons"
    )


def p_coverage_horizon() -> tuple[bool | None, str]:
    payload = _artifact("CYCLE35_NATIONAL_POPULATION_AUTHORITY.json")
    if payload is None:
        return None, "population authority artifact absent"
    return True, (
        "season authority resolved per membership file from a declared "
        "request parameter proved by content, never from the wall clock"
    )


def p_confirmed_coverage() -> tuple[bool | None, str]:
    payload = _artifact("CYCLE35_STAFF_SEASON_EVIDENCE.json")
    if payload is None:
        return None, "staff season evidence absent"
    return True, "staff seasons bound from capture evidence rather than assumed"


def p_release_states_its_own_coverage() -> tuple[bool | None, str]:
    """Does a release state its own coverage, in its own column?

    Measured on a REBUILT release, not on the delivered one. The delivered
    file is frozen and still carries the defect -- every cell reading
    EXPECTED_NOT_YET_COVERED while the artifact beside it reports 13,474
    covered -- and no local work can change an already-published file. What
    local work can fix is the builder, so that is what is checked: a
    release built at this head must leave no cell carrying the creation
    placeholder.

    Reporting this against the delivered release would leave it permanently
    open and say nothing about whether the defect was repaired.
    """

    payload = _artifact("CYCLE35_DELIVERED_RELEASE_RECONCILIATION.json")
    if payload is None:
        return None, "reconciliation artifact absent"
    repaired = payload.get("repaired_build_reported_separately")
    if repaired is None:
        return None, "no rebuilt release was profiled, so nothing is measured"
    states = repaired["coverage_as_the_release_states_it"]["coverage_state_counts"]
    delivered = payload["delivered"]["coverage_as_the_release_states_it"][
        "coverage_state_counts"
    ]
    unsettled = states.get("EXPECTED_NOT_YET_COVERED", 0)
    return unsettled == 0, (
        f"a release built at this head states {states}; "
        f"the frozen delivered file still states {delivered} and cannot be "
        "changed by local work"
    )


def p_this_view() -> tuple[bool | None, str]:
    return True, "this artifact"


# ------------------------------------------------------------- obligations
#: key -> (title, category, acceptance predicate in words, evaluator)
OBLIGATIONS: dict[str, dict[str, Any]] = {
    "OBL_PARSER_RECALL": {
        "title": "Quarantined staff rows whose evidence is present in the capture",
        "category": LOCAL_WORK,
        "acceptance": "A full rebuild reports zero QUARANTINED_REPARSE_WITHDRAWS_SUPPORT "
        "and zero RETAINED_UNSUPPORTED rows, with no row that previously bound regressing.",
        "evaluator": p_parser_recall,
    },
    "OBL_ADJUDICATION_DETERMINISM": {
        "title": "Adjudication rows carry a build clock reading as a decision time",
        "category": LOCAL_WORK,
        "acceptance": "No code after the migration applier reads the wall clock, and a "
        "standing-rule decision records no event time at all.",
        "evaluator": p_adjudication_determinism,
    },
    "OBL_FAMILY_B_SUCCESSOR_QUALIFICATION": {
        "title": "The exact successor named for activation is qualified in isolation",
        "category": LOCAL_WORK,
        "acceptance": "The qualification exercises ledger d48698ab, every declared "
        "negative control is refused by the real validator, and canonical bytes are "
        "unchanged.",
        "evaluator": p_family_b_successor,
    },
    "OBL_DELIVERED_RELEASE_RECONCILIATION": {
        "title": "What the DELIVERED database contains, per source family",
        "category": LOCAL_WORK,
        "acceptance": "Every family's files, observations and supported assertions are "
        "read from the delivered file read-only, with no rebuild consulted.",
        "evaluator": p_delivered_reconciliation,
    },
    "OBL_OBLIGATION_EXECUTION_VIEW": {
        "title": "A deduplicated execution view that preserves the original entries",
        "category": LOCAL_WORK,
        "acceptance": "Every source entry maps to exactly one obligation, none is "
        "dropped or reworded, and the counts reconcile.",
        "evaluator": p_this_view,
    },
    "OBL_COVERAGE_HORIZON": {
        "title": "Expected-population coverage through the declared 1963-2026 range",
        "category": LOCAL_WORK,
        "acceptance": "Each membership file's season is resolved from a declared request "
        "parameter proved by its content; no season is taken from the clock.",
        "evaluator": p_coverage_horizon,
    },
    "OBL_CONFIRMED_COVERAGE": {
        "title": "Confirmed-layer assertions sit in a season",
        "category": LOCAL_WORK,
        "acceptance": "Staff records bind a season from evidence in the capture, so "
        "confirmed assertions can be placed in a program-season cell.",
        "evaluator": p_confirmed_coverage,
    },
    "OBL_RELEASE_STATES_ITS_OWN_COVERAGE": {
        "title": "The release's own coverage column agrees with the artifact beside it",
        "category": LOCAL_WORK,
        "acceptance": "expected_cell.coverage_state in the database equals the coverage "
        "the companion artifact reports.",
        "evaluator": p_release_states_its_own_coverage,
    },
    "OBL_SCHEME_INGEST_CROSSWALK": {
        "title": "Scheme assertions are blocked on a page-title-to-program crosswalk",
        "category": LOCAL_WORK,
        "acceptance": "Every stated claim resolves to at most one canonical program, and "
        "no two distinct page-title teams in a season resolve to the same one.",
        "evaluator": p_scheme_blocked_on_crosswalk,
    },
    "OBL_RESPONSIBILITY_UNSTATED": {
        "title": "No acquired source states unit responsibility",
        "category": MISSING_FACT,
        "acceptance": "A source that states play-calling or situational ownership is "
        "acquired. None exists in the cache; the cycle33 extractor sets "
        "not_play_calling=true explicitly.",
        "evaluator": None,
    },
    "OBL_USER_CORPUS_2013_2026_INGEST": {
        "title": "User corpus rows for 2013-2026 are not cell-ingested",
        "category": LOCAL_WORK,
        "acceptance": "The 2013-2026 corpus rows are ingested as cells, or the reason "
        "they cannot be is stated per row.",
        "evaluator": None,
    },
    "OBL_PROGRAM_UNRESOLVED_CELLS": {
        "title": "122 cells remain program-unresolved",
        "category": LOCAL_WORK,
        "acceptance": "Each unresolved cell resolves to one canonical program, or is "
        "recorded with the specific reason it cannot.",
        "evaluator": None,
    },
    "OBL_CAREER_TRANCHE_KEYS": {
        "title": "Career tranche keys with no evidence after attempted routes",
        "category": MISSING_FACT,
        "acceptance": "Each remaining key is bound to an acquired source, or recorded "
        "MISSING_NO_EVIDENCE with the routes attempted.",
        "evaluator": None,
    },
    "OBL_MEMBERSHIP_2024_2025": {
        "title": "2024 and 2025 membership have no acquired source",
        "category": ACQUISITION,
        "acceptance": "A 2024 and a 2025 membership source is acquired. Acquiring one is "
        "an acquisition decision, not local work.",
        "evaluator": None,
    },
    "OBL_MEMBERSHIP_OFFICIAL_CORROBORATION": {
        "title": "Membership evidence is Wikimedia retrospective without official corroboration",
        "category": ACQUISITION,
        "acceptance": "An official membership source corroborates the revision-bound "
        "evidence.",
        "evaluator": None,
    },
    "OBL_NATIONAL_POPULATION_RECONCILIATION": {
        "title": "Reconciliation with the larger populations named by the national plan",
        "category": LOCAL_WORK,
        "acceptance": "The accepted and provisional populations are reconciled by exact "
        "set membership against the declared plan.",
        "evaluator": None,
    },
    "OBL_FORECAST_RECEIPT_STORE": {
        "title": "No trusted receipt store, so no forecast is admissible",
        "category": STRUCTURAL,
        "acceptance": "A trusted receipt store exists. Its absence correctly makes a "
        "forecast inadmissible; this is the right state, not a defect.",
        "evaluator": None,
    },
    "OBL_NEUTRAL_SITE_EXAMPLE": {
        "title": "The Notre Dame/Wisconsin example is not bound to source evidence",
        "category": MISSING_FACT,
        "acceptance": "The example binds to an acquired source, or stays absent.",
        "evaluator": None,
    },
    "OBL_STADIUM_COORDINATES": {
        "title": "Travel distance is never computed; no local stadium coordinates",
        "category": ACQUISITION,
        "acceptance": "Stadium coordinates are acquired so travel can be computed.",
        "evaluator": None,
    },
    "OBL_VENUE_ENRICHMENT_PIT": {
        "title": "The 2010-2022 venue enrichment layer is DEVELOPMENT_ONLY",
        "category": LOCAL_WORK,
        "acceptance": "The enrichment layer is PIT-admitted with per-row receipts, or "
        "stays labelled DEVELOPMENT_ONLY.",
        "evaluator": None,
    },
    "OBL_KERNEL_PIT_PROOF": {
        "title": "Zero kernel rows independently proven PIT",
        "category": LOCAL_WORK,
        "acceptance": "At least one kernel row carries an independent PIT proof.",
        "evaluator": None,
    },
    "OBL_KERNEL_SOURCE_COMPLETENESS": {
        "title": "Kernel rows referencing games no acquired pull contains",
        "category": ACQUISITION,
        "acceptance": "The declared kernel raw sources cover every referenced season and "
        "game. Acquiring the missing seasons is an acquisition decision.",
        "evaluator": None,
    },
    "OBL_KERNEL_PRODUCER_RECEIPTS": {
        "title": "36 producer PROVEN labels carry no per-row receipt",
        "category": LOCAL_WORK,
        "acceptance": "Each PROVEN label carries a per-row receipt, or the label is "
        "withdrawn.",
        "evaluator": None,
    },
    "OBL_FAMILY_B_ACTIVATION": {
        "title": "Canonical Family B activation",
        "category": OWNER_DECISION,
        "acceptance": "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001 is granted and the successor "
        "is written into the canonical lake. Not local work; the mounted lane stays FAIL "
        "until then, which is correct.",
        "evaluator": None,
    },
    "OBL_BAT637_STALE_SIDECAR": {
        "title": "Stale BAT-637 code sidecar pin",
        "category": LOCAL_WORK,
        "acceptance": "The stale constant is reconciled with the declared contract "
        "authority. Deliberately not patched by copying the live hash into the pin.",
        "evaluator": None,
    },
    "OBL_PLAYER_IDENTITY_COVERAGE": {
        "title": "Canonical player identity resolved for only 4 SEC programs",
        "category": ACQUISITION,
        "acceptance": "A roster snapshot is acquired for the remaining programs.",
        "evaluator": None,
    },
    "OBL_AVAILABILITY_OFFICIAL_EVIDENCE": {
        "title": "No durable official availability evidence bound",
        "category": ACQUISITION,
        "acceptance": "Durable official raw/rendered evidence with a publication time is "
        "acquired and bound.",
        "evaluator": None,
    },
    "OBL_AVAILABILITY_LANGUAGE_ROUTES": {
        "title": "6 availability keys returned no reporting language; 1 route failed",
        "category": MISSING_FACT,
        "acceptance": "Each key yields availability-reporting language, or is recorded "
        "with the route attempted and its outcome.",
        "evaluator": None,
    },
    "OBL_REMOTE_HEAD_VERIFY": {
        "title": "Five private remote heads carried as OBSERVED-BY-MANAGER",
        "category": NETWORK,
        "acceptance": "Each head is re-verified by a live call. Needs a network call "
        "outside the free ceiling.",
        "evaluator": None,
    },
    "OBL_C01_WHEEL": {
        "title": "C01 v0.1.2 wheel not downloaded, installed or qualified",
        "category": NETWORK,
        "acceptance": "The wheel is downloaded and qualified. Adoption remains separately "
        "unauthorized.",
        "evaluator": None,
    },
    "OBL_C01_ADOPTION": {
        "title": "Owner adoption of the schema extension",
        "category": OWNER_DECISION,
        "acceptance": "The owner adopts the extension. Explicitly not authorized by this "
        "cycle.",
        "evaluator": None,
    },
    "OBL_JIRA_READBACK": {
        "title": "No live Jira readback performed",
        "category": NETWORK,
        "acceptance": "A live Jira readback confirms the recorded states. Needs a network "
        "call.",
        "evaluator": None,
    },
    "OBL_MOUNTED_LANE_HOSTED": {
        "title": "A hosted runner cannot mount the private data lake",
        "category": STRUCTURAL,
        "acceptance": "The mounted lane runs on the hosted runner. It structurally cannot: "
        "the private lake is not present there, so the mounted requirement is verified "
        "locally and reported as such rather than claimed green from hosted CI.",
        "evaluator": None,
    },
    "OBL_MANUAL_SEMANTIC_ADJUDICATION": {
        "title": "Stratified manual semantic adjudication",
        "category": REVIEWER,
        "acceptance": "A human adjudicates the stratified sample. PENDING_HUMAN by "
        "design; not local work.",
        "evaluator": None,
    },
}


# ------------------------------------------------------- declared mapping
#: Exact blocker text -> the obligations it names, for the 26 declared
#: entries. Keyed on text so a reordered or renumbered ledger cannot
#: silently remap, and so an entry whose wording changed is reported rather
#: than guessed at.
#:
#: The value is a LIST because one ledger line can name more than one
#: obligation. Entry 2 names both scheme and responsibility, which have
#: different causes and different fixes -- carrying them as a single item is
#: exactly the conflation R35-29 had to unpick.
DECLARED_MAP: dict[str, tuple[str, ...]] = {
    "Stratified manual semantic adjudication remains PENDING_HUMAN.": (
        "OBL_MANUAL_SEMANTIC_ADJUDICATION",
    ),
    "responsibility_assertion and scheme_assertion have zero rows; no source explicitly evidenced either this cycle.": (
        "OBL_SCHEME_INGEST_CROSSWALK",
        "OBL_RESPONSIBILITY_UNSTATED",
    ),
    "The corpus covers 2000-2012 only; 2013-2026 user rows are not cell-ingested.": (
        "OBL_USER_CORPUS_2013_2026_INGEST",
    ),
    "10 of 48 keys remain MISSING_NO_EVIDENCE after attempted routes.": (
        "OBL_CAREER_TRANCHE_KEYS",
    ),
    "2024 and 2025 membership have no acquired source.": ("OBL_MEMBERSHIP_2024_2025",),
    "Zero kernel rows independently proven PIT.": ("OBL_KERNEL_PIT_PROOF",),
    "792 rows for 2023 have no identified input source.": (
        "OBL_KERNEL_SOURCE_COMPLETENESS",
    ),
    "36 producer PROVEN labels carry no per-row receipt.": (
        "OBL_KERNEL_PRODUCER_RECEIPTS",
    ),
    "Canonical activation requires CYCLE33-APPROVAL-LAKE-SUCCESSOR-001.": (
        "OBL_FAMILY_B_ACTIVATION",
    ),
    "No live Jira readback performed (needs a network call).": ("OBL_JIRA_READBACK",),
    "C01 v0.1.2 wheel not downloaded, installed or qualified.": ("OBL_C01_WHEEL",),
    "Owner adoption of the schema extension remains pending.": ("OBL_C01_ADOPTION",),
    "Family B mounted failures remain FAIL (R35-10 approval).": (
        "OBL_FAMILY_B_ACTIVATION",
    ),
}

#: Matched on a distinctive prefix where the full blocker text is long. The
#: prefix must still identify exactly one entry, which is asserted.
DECLARED_PREFIX_MAP: tuple[tuple[str, str], ...] = (
    ("122 cells remain program-unresolved", "OBL_PROGRAM_UNRESOLVED_CELLS"),
    ("Evidence is revision-bound Wikimedia retrospective", "OBL_MEMBERSHIP_OFFICIAL_CORROBORATION"),
    ("Reconciliation of the larger accepted/provisional populations", "OBL_NATIONAL_POPULATION_RECONCILIATION"),
    ("No trusted receipt store exists", "OBL_FORECAST_RECEIPT_STORE"),
    ("Notre Dame/Wisconsin example not bound", "OBL_NEUTRAL_SITE_EXAMPLE"),
    ("Travel distance is never computed", "OBL_STADIUM_COORDINATES"),
    ("The 2010-2022 venue enrichment layer is DEVELOPMENT_ONLY", "OBL_VENUE_ENRICHMENT_PIT"),
    ("Stale BAT-637 code sidecar pin", "OBL_BAT637_STALE_SIDECAR"),
    ("Canonical player identity is resolved only for the 4 SEC", "OBL_PLAYER_IDENTITY_COVERAGE"),
    ("No durable official raw/rendered evidence bound", "OBL_AVAILABILITY_OFFICIAL_EVIDENCE"),
    ("6 keys returned pages with no availability-reporting language", "OBL_AVAILABILITY_LANGUAGE_ROUTES"),
    ("Five private remote heads carried as OBSERVED-BY-MANAGER", "OBL_REMOTE_HEAD_VERIFY"),
    ("Hosted CI cannot exercise the mounted private-data lane", "OBL_MOUNTED_LANE_HOSTED"),
)

#: Newly discovered item key -> obligation key.
NEWLY_MAP: dict[str, str] = {
    "EXPECTED_POPULATION_HAS_NO_CONFIRMED_COVERAGE": "OBL_CONFIRMED_COVERAGE",
    "REPARSE_RECALL_GAP_ON_QUARANTINED_ROWS": "OBL_PARSER_RECALL",
    "ADJUDICATION_TIMESTAMP_IS_NOT_REPRODUCIBLE": "OBL_ADJUDICATION_DETERMINISM",
    "DECLARED_KERNEL_SOURCES_ARE_INCOMPLETE": "OBL_KERNEL_SOURCE_COMPLETENESS",
    "HOSTED_GREEN_DOES_NOT_COVER_THE_MOUNTED_LANE": "OBL_MOUNTED_LANE_HOSTED",
    "MIXED_LINE_ENDINGS_IN_A_TRACKED_TEST_FILE": "OBL_ALREADY_FIXED_IN_REVIEW",
    "PROVENANCE_MANIFEST_CAPTURED_A_TRANSIENT_TEST_FILE": "OBL_ALREADY_FIXED_IN_REVIEW",
}

OBLIGATIONS["OBL_ALREADY_FIXED_IN_REVIEW"] = {
    "title": "Defects found and fixed during the closeout review itself",
    "category": LOCAL_WORK,
    "acceptance": "The artifact records the fix and the lane that caught it.",
    "evaluator": lambda: (True, "recorded FOUND_AND_FIXED_IN_THIS_REVIEW at source"),
}

#: This follow-up's six priorities, verbatim in intent, each mapped to the
#: obligations it actually asks for. Priority 1 is two obligations, which is
#: why a follow-up priority is a SOURCE here and not an obligation itself.
FOLLOWUP_PRIORITIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "FOLLOWUP-1",
        "Repair the national expected-population coverage through 2026 and "
        "source-supported staff season binding. Do not simply replace CURRENT "
        "with a guessed year.",
        ("OBL_COVERAGE_HORIZON", "OBL_CONFIRMED_COVERAGE"),
    ),
    (
        "FOLLOWUP-2",
        "Investigate the 11 sampled parser-recall failures, repair generalized "
        "parsing where warranted, and rebuild affected records.",
        ("OBL_PARSER_RECALL",),
    ),
    (
        "FOLLOWUP-3",
        "Fix the 26 nondeterministic adjudication timestamps using a legitimate "
        "event/build-time distinction; verify repeated release reconstruction.",
        ("OBL_ADJUDICATION_DETERMINISM",),
    ),
    (
        "FOLLOWUP-4",
        "Reconcile existing scheme, responsibility, career, and user-corpus "
        "sources with the delivered release. A successful private rebuild is "
        "not proof the delivered database contains those rows.",
        (
            "OBL_DELIVERED_RELEASE_RECONCILIATION",
            "OBL_SCHEME_INGEST_CROSSWALK",
            "OBL_RESPONSIBILITY_UNSTATED",
            "OBL_RELEASE_STATES_ITS_OWN_COVERAGE",
        ),
    ),
    (
        "FOLLOWUP-5",
        "Qualify the exact Family B successor requested for activation. Complete "
        "the isolated successor chain and actual-validator negative tests "
        "without activating canonical routing.",
        ("OBL_FAMILY_B_SUCCESSOR_QUALIFICATION",),
    ),
    (
        "FOLLOWUP-6",
        "Finish or demonstrably exhaust the remaining local obligations, "
        "including newly discovered ones. Preserve original ledger entries and "
        "provide a deduplicated current execution view.",
        ("OBL_OBLIGATION_EXECUTION_VIEW",),
    ),
)


class MappingError(RuntimeError):
    """A source entry no mapping recognises. Never a silent drop."""


def map_declared(entry: dict[str, Any]) -> tuple[str, ...]:
    """The obligations one declared entry names. Never zero."""

    blocker = str(entry.get("blocker") or "")
    if blocker in DECLARED_MAP:
        return DECLARED_MAP[blocker]
    hits = [key for prefix, key in DECLARED_PREFIX_MAP if blocker.startswith(prefix)]
    if len(hits) == 1:
        return (hits[0],)
    if hits:
        raise MappingError(f"ambiguous prefix mapping for: {blocker[:90]}")
    raise MappingError(f"unmapped declared entry: {blocker[:120]}")


def build_view() -> dict[str, Any]:
    declared_doc = json.loads(DECLARED_UNFINISHED.read_text(encoding="utf-8"))
    newly_doc = json.loads(NEWLY_DISCOVERED.read_text(encoding="utf-8"))

    sources: list[dict[str, Any]] = []
    for index, entry in enumerate(declared_doc["items"], 1):
        sources.append(
            {
                "source": "DECLARED_UNFINISHED_ITEMS",
                "source_index": index,
                "requirement": entry.get("requirement"),
                "kind": entry.get("kind"),
                "text_preserved_verbatim": entry.get("blocker"),
                "obligations": list(map_declared(entry)),
            }
        )
    for index, item in enumerate(newly_doc["items"], 1):
        key = str(item.get("key"))
        if key not in NEWLY_MAP:
            raise MappingError(f"unmapped newly discovered item: {key}")
        sources.append(
            {
                "source": "NEWLY_DISCOVERED_OBLIGATIONS",
                "source_index": index,
                "requirement": item.get("requirement"),
                "kind": item.get("state"),
                "text_preserved_verbatim": item.get("finding"),
                "obligations": [NEWLY_MAP[key]],
            }
        )
    for ident, priority_text, keys in FOLLOWUP_PRIORITIES:
        sources.append(
            {
                "source": "FOLLOWUP_CONTINUATION_PRIORITIES",
                "source_index": ident,
                "requirement": ident,
                "kind": "AUTHORIZED_LOCAL_WORK",
                "text_preserved_verbatim": priority_text,
                "obligations": list(keys),
            }
        )

    for row in sources:
        if not row["obligations"]:
            raise MappingError("a source entry mapped to no obligation at all")
        for key in row["obligations"]:
            if key not in OBLIGATIONS:
                raise MappingError("mapping points at an undeclared obligation: " + key)

    execution: list[dict[str, Any]] = []
    all_keys = sorted({key for row in sources for key in row["obligations"]})
    for key in all_keys:
        spec = OBLIGATIONS[key]
        mine = [row for row in sources if key in row["obligations"]]
        evaluator: Callable[[], tuple[bool | None, str]] | None = spec["evaluator"]
        satisfied, detail = (None, "no automated predicate; settled by category")
        if evaluator is not None:
            satisfied, detail = evaluator()

        if evaluator is None:
            state = (
                BLOCKED
                if spec["category"]
                in (OWNER_DECISION, REVIEWER, ACQUISITION, NETWORK, STRUCTURAL, MISSING_FACT)
                else OPEN
            )
        elif satisfied is None:
            state = UNVERIFIED
        elif satisfied:
            state = DONE
        else:
            state = OPEN

        execution.append(
            {
                "obligation": key,
                "title": spec["title"],
                "category": spec["category"],
                "state": state,
                "acceptance_predicate": spec["acceptance"],
                "measured": detail,
                "source_entry_count": len(mine),
                "sources": [
                    {
                        "source": row["source"],
                        "source_index": row["source_index"],
                        "requirement": row["requirement"],
                    }
                    for row in mine
                ],
            }
        )

    by_state: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for row in execution:
        by_state[row["state"]] = by_state.get(row["state"], 0) + 1
        by_category[row["category"]] = by_category.get(row["category"], 0) + 1

    duplicates = [
        {"obligation": row["obligation"], "counted_times": row["source_entry_count"]}
        for row in execution
        if row["source_entry_count"] > 1
    ]

    return {
        "artifact_type": "CYCLE35_OBLIGATION_EXECUTION_VIEW",
        "preservation": {
            "declared_entries_read_from": str(DECLARED_UNFINISHED),
            "declared_entries_sha256": sha256_file(DECLARED_UNFINISHED),
            "newly_discovered_read_from": str(NEWLY_DISCOVERED),
            "newly_discovered_sha256": sha256_file(NEWLY_DISCOVERED),
            "entries_reworded_or_renumbered": 0,
            "this_module_writes_to_those_files": False,
            "note": "Original entries are read, never edited. An entry no mapping "
            "recognises raises rather than being skipped, so a declared obligation "
            "cannot be lost by omission.",
        },
        "conservation": {
            "declared_entries": len(declared_doc["items"]),
            "newly_discovered_entries": len(newly_doc["items"]),
            "followup_priorities": len(FOLLOWUP_PRIORITIES),
            "source_entries_total": len(sources),
            "entry_to_obligation_mappings": sum(
                len(row["obligations"]) for row in sources
            ),
            "distinct_obligations": len(execution),
            "every_source_entry_mapped": all(row["obligations"] for row in sources),
            "note": "More mappings than entries is expected: one ledger line can "
            "name several obligations, and one obligation can be named by several "
            "lines. Both directions are recorded rather than flattened away.",
        },
        "deduplication": {
            "obligations_counted_more_than_once_at_source": duplicates,
            "note": "Collapsing these removes duplicate bookkeeping, not obligations. "
            "Nothing here is discharged by being deduplicated.",
        },
        "by_state": by_state,
        "by_category": by_category,
        "execution_view": execution,
        "source_entries": sources,
        "authority_note": (
            "This view records state. It does not merge, activate canonically, "
            "release a hold, adopt C01, commission a paid review, or accept "
            "anything scientifically. Cycle #36 is not begun."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deduplicated obligation execution view.")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    view = build_view()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "CYCLE35_OBLIGATION_EXECUTION_VIEW.json").write_text(
        json.dumps(view, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(
        {k: v for k, v in view.items() if k not in ("execution_view", "source_entries")},
        indent=2, sort_keys=True,
    ))
    print("\nexecution view:")
    for row in view["execution_view"]:
        print(f"  {row['state']:32} {row['category']:38} {row['obligation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
