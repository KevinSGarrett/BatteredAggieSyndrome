"""Exact remaining-audit register for Cycle #30 reconstruction evidence.

Cursor publishes selected revisions and source/population/claim sets.
The manager owns independent interpretation, adversarial review, and
acceptance. These units are not audited merely because they exist.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

REQUIRED_UNIT_FIELDS = (
    "id",
    "jira_owners",
    "implementation_owner",
    "manager_reviewer",
    "status",
    "period_population",
    "source_artifact_claim_sets",
    "blocker",
    "next_action",
    "affected_use_restriction",
    "selected_revisions",
    "scope_provenance_result",
    "semantic_result",
    "adversarial_result",
    "new_claims_independently_verified",
    "failures",
    "remaining_work",
    "not_audited_reason",
)


class AuditRegisterError(ValueError):
    """Raised when an audit unit is missing required accounting fields."""


def require_unit_fields(unit: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_UNIT_FIELDS if field not in unit]
    if missing:
        raise AuditRegisterError(f"audit unit missing required fields: {missing}")
    if unit.get("status") in {"AUDITED", "MANAGER_VERIFIED", "COMPLETE"}:
        raise AuditRegisterError("Cursor cannot declare an audit unit audited")


def remaining_audit_register(
    *,
    head_sha: str,
    kernel_rows: int,
    proven_pit_rows: int,
    current_n: int,
    parent_games: int,
    ties: int,
    neutrals: int,
    official_staff_attempts: int,
    official_staff_not_attempted: int,
    availability_routes_attempted: int = 0,
    membership_1963_2012_rows: int = 0,
    membership_1963_2012_years_attempted: int = 0,
    raw_to_normalized_compared: int = 0,
    historical_wiki_pages: int = 0,
    historical_wiki_episodes: int = 0,
    historical_wiki_incomplete_years: Sequence[int] | None = None,
    availability_candidates_not_joined: int = 0,
    predecessor_payload_mounted: bool = False,
    predecessor_oriented_rows: int = 0,
    predecessor_eligible_rows: int = 0,
    cfbd_historical_absent_from_2026: int = 0,
    ncaa_discontinued_rows: int = 0,
    availability_joined_to_roster: int = 0,
    cfbd_parent_joined_1963_2012: int = 0,
    cfbd_parent_cfbd_rows_1963_2012: int = 0,
    cfbd_note_forfeit_count_1963_2012: int = 0,
    cfbd_note_postponed_count_1963_2012: int = 0,
) -> dict[str, Any]:
    selected = {
        "cycle30_head": head_sha,
        "cycle29_reviewed_head": "0b957ea127ad6a5373901d8ddff47c43a496b100",
        "canonical_main": "55e12a5aad3a7e843204fcba619c3cb3d3d6194d",
        "review_state": "READY_FOR_MANAGER_REVIEW",
        "not_manager_verified": True,
    }
    units: list[dict[str, Any]] = [
        {
            "id": "C30-AUDIT-01",
            "jira_owners": ["BAT-703", "BAT-708", "BAT-696"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending independent review",
            "status": "RECONSTRUCTION_EVIDENCE_SUBMITTED",
            "period_population": (
                "governing-plan requirement union; Cycles 1–29 plus pre-cycle/"
                "unattributed work; current 2026 DI FBS/FCS N="
                f"{current_n}; historical 1963–2026 backlog"
            ),
            "source_artifact_claim_sets": [
                "artifacts/scientific_integrity/cycle30/BAS_CANONICAL_DOMAIN_CATALOG.json",
                "artifacts/scientific_integrity/cycle30/BAS_DOMAIN_CATALOG_CROSSWALK.json",
                "artifacts/scientific_integrity/cycle30/CURRENT_2026_DIVISION_I_PROGRAM_POPULATION.json",
                "artifacts/scientific_integrity/cycle30/HISTORICAL_SCOPE_CONTRACT.json",
                "docs/cycle30/CFIP_RFC_CYCLE30.md",
            ],
            "blocker": "manager_independent_scope_challenge_pending",
            "next_action": (
                "Manager must independently challenge omissions of FCS, "
                "discontinued programs, injuries, HC/OC/DC, position/career "
                "history, and less-prominent plan requirements against this register"
            ),
            "affected_use_restriction": (
                "whole_project_scientific_trust unrecovered; unknown scope "
                "cannot be declared complete"
            ),
            "selected_revisions": selected,
            "scope_provenance_result": "CURSOR_RECONSTRUCTION_ONLY",
            "semantic_result": "PENDING_MANAGER",
            "adversarial_result": "PENDING_MANAGER",
            "new_claims_independently_verified": [],
            "failures": [],
            "remaining_work": [
                "C30-AUDIT-01-FCS",
                "C30-AUDIT-01-DISCONTINUED",
                "C30-AUDIT-01-INJURIES",
                "C30-AUDIT-01-STAFF-ROLES",
                "C30-AUDIT-01-CAREER",
                "C30-AUDIT-01-PLAN-TAIL",
            ],
            "not_audited_reason": "Cursor reconstruction is not manager audit",
        },
        {
            "id": "C30-AUDIT-01-FCS",
            "jira_owners": ["BAT-703"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending",
            "status": "RECONSTRUCTION_EVIDENCE_SUBMITTED",
            "period_population": (
                "FCS–FCS and cross-subdivision games 2013–2023 CFBD tranche plus "
                "1963–2012 CFBD source-classified FCS–FCS rows plus "
                f"parent {parent_games} FBS-filtered games; "
                f"CFBD-parent source-id join {cfbd_parent_joined_1963_2012}/"
                f"{cfbd_parent_cfbd_rows_1963_2012} for 1963–2012; "
                f"source-note forfeits={cfbd_note_forfeit_count_1963_2012} "
                f"postponed={cfbd_note_postponed_count_1963_2012}"
            ),
            "source_artifact_claim_sets": [
                "ops/cycle30_work/outputs/CFBD_FCS_FCS_GAMES_TRANCHE.jsonl",
                "ops/cycle30_work/outputs/CFBD_FCS_FCS_GAMES_1963_2012.jsonl",
                "artifacts/scientific_integrity/cycle30/FCS_SUBSET_FROM_PARENT_SUMMARY.json",
                "artifacts/scientific_integrity/cycle30/HISTORICAL_GAME_PAIR_SUBDIVISION_COVERAGE.json",
                "artifacts/scientific_integrity/cycle30/CFBD_PARENT_IDENTITY_JOIN_1963_2012.json",
                "artifacts/scientific_integrity/cycle30/CFBD_PARENT_IDENTITY_JOIN_2013_2026.json",
                "artifacts/scientific_integrity/cycle30/CFBD_CONTEST_STATUS_NOTE_AUDIT_1963_2012.json",
                "artifacts/scientific_integrity/cycle30/CFBD_CONTEST_STATUS_NOTE_AUDIT_2013_2026.json",
            ],
            "blocker": (
                "national_fcs_completeness_unclaimed"
                if membership_1963_2012_years_attempted
                else "national_fcs_completeness_unclaimed; 1963–2012 membership blocked"
            ),
            "next_action": (
                "Manager semantic review of the CFBD-parent source-id join and "
                "source-note contest-status scan; parent remains FBS-filtered; "
                "do not claim national FCS completeness"
            ),
            "affected_use_restriction": "cross-subdivision strength abstains; no national completeness",
            "selected_revisions": selected,
            "scope_provenance_result": "CURSOR_RECONSTRUCTION_ONLY",
            "semantic_result": "PENDING_MANAGER",
            "adversarial_result": "PENDING_MANAGER",
            "new_claims_independently_verified": [],
            "failures": [],
            "remaining_work": [
                "manager semantic review of Cursor source-id join; parent remains FBS-filtered numerator",
                "source notes scanned; not official NCAA forfeit/canceled adjudication",
            ],
            "not_audited_reason": "bounded tranche is not national FCS certification",
        },
        {
            "id": "C30-AUDIT-01-DISCONTINUED",
            "jira_owners": ["BAT-703", "BAT-708"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending",
            "status": "RECONSTRUCTION_EVIDENCE_SUBMITTED",
            "period_population": "discontinued/lower-division/entry programs 1963–2026",
            "source_artifact_claim_sets": [
                "artifacts/scientific_integrity/cycle30/HISTORICAL_SCOPE_CONTRACT.json",
                "artifacts/scientific_integrity/cycle30/CFBD_MEMBERSHIP_PRESENCE_DELTA.json",
                "artifacts/scientific_integrity/cycle30/NCAA_DISCONTINUED_PROGRAM_CENSUS.json",
            ],
            "blocker": (
                "NCAA discontinued-program census rows="
                f"{ncaa_discontinued_rows}; CFBD presence delta remains a "
                "separate non-census identity"
                if ncaa_discontinued_rows
                else (
                    "CFBD year membership presence delta is not an NCAA "
                    "discontinued-program census"
                )
            ),
            "next_action": (
                "Manager semantic review of NCAA discontinued census against CFBD delta"
                if ncaa_discontinued_rows
                else (
                    "Acquire era-aware discontinued/entry records independent of CFBD; "
                    f"CFBD historical programs absent from 2026 N={cfbd_historical_absent_from_2026}"
                )
            ),
            "affected_use_restriction": "historical opportunity denominators remain incomplete",
            "selected_revisions": selected,
            "scope_provenance_result": (
                "NCAA_CENSUS_SUBMITTED_NOT_AUDITED"
                if ncaa_discontinued_rows
                else "CFBD_PRESENCE_DELTA_NOT_NCAA_CENSUS"
            ),
            "semantic_result": "PENDING_MANAGER",
            "adversarial_result": "PENDING_MANAGER",
            "new_claims_independently_verified": [],
            "failures": [],
            "remaining_work": [
                "era-aware entry/lower-division labels on NCAA census rows",
            ],
            "not_audited_reason": "omission named rather than collapsed into one UNREVIEWED label",
        },
        {
            "id": "C30-AUDIT-01-INJURIES",
            "jira_owners": ["BAT-414"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending",
            "status": "EXPLICIT_UNRESOLVED",
            "period_population": f"current {current_n} DI programs; historical availability unpublished",
            "source_artifact_claim_sets": [
                "artifacts/scientific_integrity/cycle30/AVAILABILITY_POLICY_INVENTORY.json"
            ],
            "blocker": (
                f"attempted_official_report_routes={availability_routes_attempted}; "
                f"candidate_player_rows_not_joined={availability_candidates_not_joined}; "
                f"joined_to_verified_roster={availability_joined_to_roster}; "
                "no_report=UNKNOWN not healthy"
                if availability_routes_attempted
                else "attempted_official_report_routes=0; no_report=UNKNOWN not healthy"
            ),
            "next_action": (
                "Join captured public report pages to verified roster identities under BAT-414"
                if availability_routes_attempted
                else "Authorized public availability-report acquisition under BAT-414"
            ),
            "affected_use_restriction": "injuries/availability out of fitted models; not scientifically reviewed",
            "selected_revisions": selected,
            "scope_provenance_result": (
                "ROUTES_ATTEMPTED_NOT_JOINED"
                if availability_routes_attempted
                else "INVENTORIED_NOT_ACQUIRED"
            ),
            "semantic_result": "NOT_PERFORMED",
            "adversarial_result": "NOT_PERFORMED",
            "new_claims_independently_verified": [],
            "failures": []
            if availability_routes_attempted
            else ["zero_official_availability_report_routes"],
            "remaining_work": ["join player reports to verified roster identities"],
            "not_audited_reason": "staff parsing does not review health evidence",
        },
        {
            "id": "C30-AUDIT-01-STAFF-ROLES",
            "jira_owners": ["BAT-701"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending",
            "status": "RECONSTRUCTION_EVIDENCE_SUBMITTED",
            "period_population": (
                f"current 3x{current_n} HC/OC/DC cells; official HTML attempts="
                f"{official_staff_attempts}"
            ),
            "source_artifact_claim_sets": [
                "artifacts/scientific_integrity/cycle30/CURRENT_NATIONAL_HC_OC_DC_SUMMARY.json",
                "ops/cycle30_work/outputs/CURRENT_NATIONAL_HC_OC_DC_MATRIX.jsonl",
                "artifacts/scientific_integrity/cycle30/OFFICIAL_STAFF_SOURCE_ATTEMPT_SUMMARY.json",
            ],
            "blocker": (
                f"official_staff_html_attempts={official_staff_attempts}; "
                f"not_attempted={official_staff_not_attempted}; "
                "CFBD cannot populate OC/DC; coaching not modeled"
            ),
            "next_action": (
                "Manager semantic review of official staff HTML OC/DC cells"
                if official_staff_attempts
                else "Authorized official staff/media-guide GETs per program with receipts"
            ),
            "affected_use_restriction": "OC/DC remaining UNKNOWN_NOT_LISTED/ACQUISITION_FAILED stay out of models",
            "selected_revisions": selected,
            "scope_provenance_result": "CURSOR_RECONSTRUCTION_ONLY",
            "semantic_result": "PENDING_MANAGER",
            "adversarial_result": "PENDING_MANAGER",
            "new_claims_independently_verified": [],
            "failures": []
            if official_staff_attempts
            else ["official_staff_html_not_attempted_under_scraper_ceiling"],
            "remaining_work": [
                "title-versus-responsibility audit",
                "row-bound OC/DC remaining UNKNOWN_NOT_LISTED",
            ],
            "not_audited_reason": "matrix presence is not official-source semantic review",
        },
        {
            "id": "C30-AUDIT-01-CAREER",
            "jira_owners": ["BAT-701", "BAT-388"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending",
            "status": "EXPLICIT_UNRESOLVED",
            "period_population": "pre-1963/professional/other-level career context plus 2013–2023 HC backbone",
            "source_artifact_claim_sets": [
                "ops/cycle30_work/outputs/CFBD_COACHES_HC_BACKBONE.jsonl",
                "ops/cycle30_work/outputs/COACHING_PREDECESSOR_ROWS.jsonl",
                "ops/cycle30_work/outputs/WIKIMEDIA_HISTORICAL_STAFF_CANDIDATES.jsonl",
            ],
            "blocker": (
                f"historical Wikimedia season pages={historical_wiki_pages}, "
                f"episodes={historical_wiki_episodes}; "
                f"incomplete_years={list(historical_wiki_incomplete_years or [])}; "
                "PAGE_MISSING is a recorded gap, not a vacancy; no guessed dates"
            ),
            "next_action": "Official guides plus school-matched PAGE_MISSING search; no guessed dates; no cross-program season-page binds",
            "affected_use_restriction": "career context is not PIT; not a fitted feature",
            "selected_revisions": selected,
            "scope_provenance_result": "PARTIAL_PREDECESSOR_PLUS_CFBD_HC",
            "semantic_result": "NOT_PERFORMED",
            "adversarial_result": "NOT_PERFORMED",
            "new_claims_independently_verified": [],
            "failures": ["position_career_history_not_nationally_acquired"],
            "remaining_work": ["stratified raw parser-family expansion"],
            "not_audited_reason": "CFBD HC seasons are not complete career graphs",
        },
        {
            "id": "C30-AUDIT-01-PLAN-TAIL",
            "jira_owners": ["BAT-708", "BAT-696"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending",
            "status": "EXPLICIT_UNRESOLVED",
            "period_population": "standing 50-domain split plus later plan requirements; 52 original domains",
            "source_artifact_claim_sets": [
                "artifacts/scientific_integrity/cycle30/BAS_DOMAIN_POPULATION_AND_GRAIN_CONTRACT.json",
                "artifacts/scientific_integrity/cycle30/NATIONAL_DATA_COMPLETENESS_SUCCESSOR_GATE.json",
            ],
            "blocker": "less-prominent plan requirements remain named gaps, not unmapped0",
            "next_action": "Manager challenge of domain crosswalk omissions",
            "affected_use_restriction": "unmapped domains cannot be treated as complete",
            "selected_revisions": selected,
            "scope_provenance_result": "CROSSWALK_SUBMITTED",
            "semantic_result": "PENDING_MANAGER",
            "adversarial_result": "PENDING_MANAGER",
            "new_claims_independently_verified": [],
            "failures": [],
            "remaining_work": [
                "weather/rest/timezone/BAS inference separate evidence stages"
            ],
            "not_audited_reason": "catalog existence is not requirement satisfaction",
        },
        {
            "id": "C30-AUDIT-02",
            "jira_owners": ["BAT-700", "BAT-696", "BAT-417"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending independent review",
            "status": "RECONSTRUCTION_EVIDENCE_SUBMITTED",
            "period_population": (
                "proposed active kernel: 2006–2023 observed FBS–FBS binary win, "
                f"ties excluded, 2024/25 exposed excluded; rows={kernel_rows}; "
                f"proven_pit={proven_pit_rows}"
            ),
            "source_artifact_claim_sets": [
                "ops/cycle30_work/outputs/PIT_KERNEL_ROWS.jsonl",
                "artifacts/scientific_integrity/cycle30/PIT_KERNEL_POPULATION_MANIFEST.json",
                "artifacts/scientific_integrity/cycle30/PIT_KERNEL_INDEPENDENT_RECONSTRUCTION.json",
                "artifacts/scientific_integrity/cycle30/PIT_KERNEL_FULL_CHAIN_RECONSTRUCTION.json",
                "artifacts/scientific_integrity/cycle30/KERNEL_CANDIDATE_FITS.json",
                "artifacts/scientific_integrity/cycle30/PIT_KERNEL_TRUST_GATE.json",
                "artifacts/scientific_integrity/cycle30/CYCLE30_DEPENDENCY_GRAPH.json",
            ],
            "blocker": (
                "PRIMARY_KERNEL_OBJECTIVE_INCOMPLETE because proven PIT rows=0; "
                "manager must verify entire consumed chain"
                if proven_pit_rows <= 0
                else (
                    f"proven PIT rows={proven_pit_rows} from forecast-freeze receipts; "
                    "manager must verify entire consumed chain; UNTRUSTED_SHADOW"
                )
            ),
            "next_action": (
                "Independent verify raw/source identities, filters, labels/ties, "
                "temporal authority, priors, neutral/site, design columns, partitions, "
                "fitted parameters, probability/distribution, metrics on all comparison rows"
            ),
            "affected_use_restriction": (
                "exact scientific kernel output blocked; UNTRUSTED_SHADOW only; "
                "no production/champion/A&M claim"
            ),
            "selected_revisions": selected,
            "scope_provenance_result": "CURSOR_RECONSTRUCTION_ONLY",
            "semantic_result": "PENDING_MANAGER",
            "adversarial_result": "PENDING_MANAGER",
            "new_claims_independently_verified": [],
            "failures": (
                ["proven_pit_rows_zero", "publication_receipts_absent"]
                if proven_pit_rows <= 0
                else []
            ),
            "remaining_work": (
                ["source publication evidence for PIT admission"]
                if proven_pit_rows <= 0
                else ["manager verification of freeze-bound prospective rows"]
            ),
            "not_audited_reason": "passing fixtures cannot establish this result",
        },
        {
            "id": "C30-AUDIT-03",
            "jira_owners": ["BAT-703", "BAT-700", "BAT-696"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending independent review",
            "status": "BOUNDED_TRANCHE_EVIDENCE_SUBMITTED",
            "period_population": (
                f"parent normalized games={parent_games}; ties={ties}; "
                f"provider-neutral={neutrals}; predecessor oriented rows="
                f"{predecessor_oriented_rows if predecessor_payload_mounted else 0}; "
                f"payload_mounted={predecessor_payload_mounted}"
            ),
            "source_artifact_claim_sets": [
                "canonical/national_foundation_reconciliation national_normalized_games.jsonl",
                "artifacts/scientific_integrity/cycle30/HISTORICAL_TIE_AUDIT.json",
                "artifacts/scientific_integrity/cycle30/HISTORICAL_NEUTRAL_SITE_AUDIT_SUMMARY.json",
                "artifacts/scientific_integrity/cycle30/CAPTURE_INVENTORY_EXACT_RECONCILE.json",
                "artifacts/scientific_integrity/cycle30/PIT_PREDECESSOR_POPULATION_RECONCILIATION.json",
                "artifacts/scientific_integrity/cycle30/HISTORICAL_RAW_TO_NORMALIZED_SEMANTIC_TRACE.json",
                "artifacts/scientific_integrity/cycle30/PARENT_DUPLICATE_CONFLICT_AUDIT.json",
                "artifacts/scientific_integrity/cycle30/PIT_KERNEL_PREDECESSOR_FEATURE_COMPARE.json",
            ],
            "blocker": (
                f"raw_to_normalized_compared={raw_to_normalized_compared}; "
                "not a certification of missing national games; "
                + (
                    f"predecessor payload mounted oriented={predecessor_oriented_rows} "
                    f"eligible={predecessor_eligible_rows}"
                    if predecessor_payload_mounted
                    else "national_pit_eligible_team_features.jsonl not mounted"
                )
            ),
            "next_action": (
                "Manager raw-to-normalized/feature comparisons against the expanded "
                "stratified sample; do not repeat count scan as new semantic work"
            ),
            "affected_use_restriction": (
                "does not certify missing national games or every earlier cycle"
            ),
            "selected_revisions": selected,
            "scope_provenance_result": "CURSOR_BOUNDED_TRANCHE",
            "semantic_result": "PENDING_MANAGER",
            "adversarial_result": "PENDING_MANAGER",
            "new_claims_independently_verified": [],
            "failures": (
                []
                if predecessor_payload_mounted
                else ["predecessor_90198_payload_not_mounted"]
            ),
            "remaining_work": [
                "manager semantic review of pair-date site-class collisions",
                "1963-2012 historical travel backlog",
            ],
            "not_audited_reason": "count presence is not semantic certification",
        },
        {
            "id": "C30-AUDIT-04",
            "jira_owners": ["BAT-701", "BAT-703"],
            "implementation_owner": "Cursor Cycle #30",
            "manager_reviewer": "BAS manager (Codex) — pending independent review",
            "status": "TRANCHE_EVIDENCE_SUBMITTED",
            "period_population": (
                "2,251 accepted + 2,382 provisional predecessor identities; "
                "CFBD 2013–2023/2026 HC backbone; current 3N matrix"
            ),
            "source_artifact_claim_sets": [
                "artifacts/scientific_integrity/cycle30/COACHING_PREDECESSOR_CONSERVATION.json",
                "ops/cycle30_work/outputs/CFBD_COACHES_HC_BACKBONE.jsonl",
                "artifacts/scientific_integrity/cycle30/HISTORICAL_ROLE_LATTICE_SUMMARY.json",
            ],
            "blocker": (
                "staff_parser_family_expansion_pending; official HTML remaining "
                "UNKNOWN_NOT_LISTED/empty-parse cells"
                if official_staff_attempts
                else "staff_parser_family_expansion_pending; official HTML not attempted"
            ),
            "next_action": (
                "Independently trace a declared historical/current FBS/FCS source "
                "sample and expand failed extraction families; keep injuries/rosters/"
                "recruiting/transfers on separate evidence stages"
            ),
            "affected_use_restriction": "coaching not scientifically reviewed; not modeled",
            "selected_revisions": selected,
            "scope_provenance_result": "CURSOR_TRANCHE_EVIDENCE",
            "semantic_result": "PENDING_MANAGER",
            "adversarial_result": "PENDING_MANAGER",
            "new_claims_independently_verified": [],
            "failures": []
            if official_staff_attempts
            else ["equal_length_array_join_rejected_in_tests_only_until_official_html"],
            "remaining_work": [
                "vacancy/unknown source dates",
                "title-versus-responsibility",
            ],
            "not_audited_reason": "conservation counts are not content validation",
        },
    ]
    for unit in units:
        require_unit_fields(unit)
    return {
        "artifact_type": "C30_REMAINING_AUDIT_REGISTER",
        "artifact_class": "BLOCKER_METADATA",
        "review_state": "READY_FOR_MANAGER_REVIEW",
        "not_manager_verified": True,
        "operator_hold": "ACTIVE",
        "selected_revisions": selected,
        "units": units,
        "unknown_scope_cannot_be_declared_complete": True,
        "one_unreviewed_label_forbidden": True,
    }


def official_staff_attempt_rows(
    programs: Sequence[Mapping[str, Any]],
    *,
    scraper_credits: int,
    live_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    live_by_id = {str(row.get("program_id")): row for row in (live_rows or [])}
    rows: list[dict[str, Any]] = []
    for program in programs:
        live = live_by_id.get(str(program["program_id"]))
        if live:
            status = str(live.get("status") or "NOT_ATTEMPTED")
            receipt = live.get("receipt_identity")
            if status != "NOT_ATTEMPTED" and not receipt:
                raise AuditRegisterError(
                    "official staff attempt claimed without receipt identity"
                )
            rows.append(
                {
                    "program_id": program["program_id"],
                    "display_name": program.get("display_name"),
                    "classification": program.get("classification"),
                    "declared_route": live.get(
                        "declared_route", "official_staff_directory_or_media_guide"
                    ),
                    "status": status,
                    "http_status": live.get("http_status"),
                    "receipt_identity": receipt,
                    "parser": live.get("parser"),
                    "page_url": live.get("page_url"),
                    "attempt_count": int(live.get("attempt_count") or 0),
                    "reason": live.get("reason"),
                    "artifact_class": live.get("artifact_class")
                    or (
                        "REAL_EVIDENCE"
                        if status != "NOT_ATTEMPTED"
                        else "BLOCKER_METADATA"
                    ),
                }
            )
            continue
        rows.append(
            {
                "program_id": program["program_id"],
                "display_name": program.get("display_name"),
                "classification": program.get("classification"),
                "declared_route": "official_staff_directory_or_media_guide",
                "status": "NOT_ATTEMPTED",
                "http_status": None,
                "receipt_identity": None,
                "parser": None,
                "reason": (
                    "metered_scraper_credits="
                    f"{scraper_credits}; official HTML not fetched; "
                    "CFBD coaches used for HC fields actually returned only"
                ),
                "artifact_class": "BLOCKER_METADATA",
            }
        )
    return rows
