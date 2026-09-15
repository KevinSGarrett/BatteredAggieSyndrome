"""Cycle 33 targeted closeout: schemes, titles, remaining domains, approval.

Does not rematerialize predecessor lake gates. Does not invent careers or PIT.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aggie_analytics.cycle33.role_taxonomy import assignments_from_title
from aggie_analytics.cycle33.scheme_tenure import family_tags_from_source

SCI = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\runs\20260914T130736Z"
    r"\implementation_output\science"
)
REPO = Path(r"C:\BatteredAggieSyndrome.data\worktrees\cycle33-scr")
CROSSWALK = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_review\TECHNICAL_PLAN_DOMAIN_CROSSWALK.csv"
)
DOMAIN_MATRIX = Path(
    r"C:\BatteredAggieSyndrome.data\ops\manager_review\DOMAIN_REVIEW_MATRIX.csv"
)
PARSED = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z"
    r"\implementation_output\science\CYCLE32_OFFICIAL_STAFF_PARSED.jsonl"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def review_schemes() -> dict[str, Any]:
    claims_path = SCI / "CYCLE33_SCHEME_TENURE_CLAIMS.jsonl"
    unnorm: Counter[str] = Counter()
    field_by_text: dict[str, Counter[str]] = {}
    samples: dict[str, list[dict[str, Any]]] = {}
    for line in claims_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("claim_kind") != "SCHEME":
            continue
        if row.get("disposition") != "SOURCE_REPORTED_UNNORMALIZED":
            continue
        text = str(row.get("source_text") or "")
        unnorm[text] += 1
        field_by_text.setdefault(text, Counter())[str(row.get("field") or "")] += 1
        bucket = samples.setdefault(text, [])
        if len(bucket) < 2:
            bucket.append(
                {
                    "page_title": row.get("page_title"),
                    "season": row.get("season"),
                    "field": row.get("field"),
                }
            )
    values: list[dict[str, Any]] = []
    would_tag_if_forced = 0
    for text, count in unnorm.most_common():
        fields = field_by_text.get(text) or Counter()
        tags_by_field = {
            field: [item["code"] for item in family_tags_from_source(text, field)]
            for field in fields
        }
        any_tags = any(tags_by_field.values())
        if any_tags:
            would_tag_if_forced += count
        disposition = "RETAIN_UNSUPPORTED_OR_AMBIGUOUS"
        if any_tags:
            disposition = "RETAIN_UNTAGGED_FIELD_OR_AMBIGUOUS_CONTEXT"
        values.append(
            {
                "source_text": text,
                "count": count,
                "fields": dict(fields),
                "family_tags_if_reapplied": tags_by_field,
                "forced_tag": False,
                "disposition": disposition,
                "sample_context": samples.get(text, []),
            }
        )
    payload = {
        "artifact_type": "CYCLE33_SCHEME_UNNORMALIZED_REVIEW",
        "as_of_utc": utc_now(),
        "unnormalized_claim_count": sum(unnorm.values()),
        "distinct_source_texts": len(unnorm),
        "forced_tag": False,
        "would_tag_if_forced_but_not_applied": would_tag_if_forced,
        "values": values,
        "no_forced_taxonomy": True,
        "wikipedia_is_not_official": True,
        "pit_admitted": False,
    }
    write_json(SCI / "CYCLE33_SCHEME_UNNORMALIZED_REVIEW.json", payload)
    return payload


def review_unmapped_titles() -> dict[str, Any]:
    wanted = {"Assistant", "Assistant Western Coach", "she/her/hers"}
    found: list[dict[str, Any]] = []
    for line in PARSED.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        title = str(row.get("source_title") or row.get("title") or "")
        if title not in wanted:
            continue
        mapped = assignments_from_title(title)
        found.append(
            {
                "program_id": row.get("program_id") or row.get("display_name"),
                "person": row.get("person"),
                "source_title": title,
                "source_url": row.get("source_url") or row.get("url"),
                "raw_role": row.get("role"),
                "taxonomy_assignments": mapped,
            }
        )
    payload = {
        "artifact_type": "CYCLE33_UNMAPPED_TITLE_SOURCE_REVIEW",
        "as_of_utc": utc_now(),
        "source_parsed": str(PARSED),
        "rows": found,
        "count": len(found),
        "extraction_contamination_not_coaching_title": [
            {
                "person": "Yumi Kuscher, MS, LAT, ATC, CSCS",
                "source_title": "she/her/hers",
                "note": "Pronouns/credentials from a trainer/ATC listing; must not become a coaching role."
            }
        ],
        "unspecified_assistant_may_be_legitimate": True,
        "western_coach_is_unmapped_review_not_forced": True,
        "raw_evidence_preserved": True,
        "pit_admitted": False,
    }
    write_json(SCI / "CYCLE33_UNMAPPED_TITLE_SOURCE_REVIEW.json", payload)
    return payload


def file_sha(rel: str) -> dict[str, Any]:
    path = REPO / rel
    return {
        "path": rel,
        "exists": path.is_file(),
        "sha256": sha256_file(path) if path.is_file() else None,
    }


def remaining_domain_backlog() -> dict[str, Any]:
    matrix: dict[str, dict[str, str]] = {}
    with DOMAIN_MATRIX.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            matrix[row["domain_id"]] = row
    crosswalk: list[dict[str, str]] = []
    with CROSSWALK.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            crosswalk.append(row)

    tranche = {
        "coaching": {
            "governing_requirement": "R33-03/R33-04/R33-08 plus D11-D15",
            "plan_sections": [
                file_sha("docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md"),
                file_sha("governance/COACH_ROLE_EPISODE_CONTRACTS.csv"),
            ],
            "implementation_data_state": (
                "Local taxonomy and current staff mapping exist; unmapped titles "
                "remain an explicit review queue; Wikipedia is not PIT."
            ),
            "owner": "BAT-701",
            "dependencies": ["R33-05", "R33-06", "R33-23"],
            "next_deliverable": "Independent manager acceptance of lossless mapping; no role invention.",
            "cycle33_implements_domain": True,
        },
        "scheme": {
            "governing_requirement": "R33-07 / D28 / DOM-020",
            "plan_sections": [
                file_sha("governance/SCHEME_PLAY_CALLER_TENDENCY_CONTRACTS.csv"),
                file_sha("docs/29_COACHING_INTELLIGENCE_ARCHITECTURE.md"),
            ],
            "implementation_data_state": (
                "National wiki scheme/tenure claims extracted; family tags are not "
                "official, film, or causal; official HTML independently corroborated=0."
            ),
            "owner": "BAT-164",
            "dependencies": ["R33-05"],
            "next_deliverable": "Retain unsupported strings; owner film/official corroboration.",
            "cycle33_implements_domain": True,
        },
        "availability": {
            "governing_requirement": "R33-11/R33-14 / D16 / DOM-011/DOM-012",
            "plan_sections": [
                file_sha("docs/36_AVAILABILITY_EVIDENCE_AND_OFFICIAL_REPORTS.md"),
                file_sha("docs/35_PLAYER_VALUE_REPLACEMENT_AND_AVAILABILITY.md"),
            ],
            "implementation_data_state": (
                "Cache-hit status unknown unless original HTTP status supplied; "
                "0 complete player+team+vintage+game statements; /injuries NOT_ATTEMPTED; "
                "no report is not healthy."
            ),
            "owner": "BAT-324",
            "dependencies": ["R33-02"],
            "next_deliverable": "Do not reacquire unchanged unavailable routes; injuries remain NOT_ATTEMPTED.",
            "cycle33_implements_domain": True,
        },
        "neutral": {
            "governing_requirement": "R33-14 / D19-D20 / DOM-026-DOM-028",
            "plan_sections": [file_sha("governance/VENUE_TRAVEL_REST_CONTRACTS.csv")],
            "implementation_data_state": (
                "Ordinary home advantage is 0 when venue_confirmed; timezone/rest "
                "contracts exist as CTX-TR-* rows, not Cycle 33 fitted features."
            ),
            "owner": "BAT-417",
            "dependencies": ["R33-02"],
            "next_deliverable": "Keep PIT-safe itinerary rules; no future itinerary.",
            "cycle33_implements_domain": True,
        },
        "identity": {
            "governing_requirement": "R33-01/R33-06 / D01/D14",
            "plan_sections": [
                file_sha("docs/15_SOURCE_MAPPING_AND_EVIDENCE_IDENTITY.md"),
                file_sha("docs/62_EXPERIMENT_IDENTITY_LINEAGE_AND_REPLAY.md"),
            ],
            "implementation_data_state": (
                "Starting stack bound; career joins evidence-bound or exact missing/"
                "name-only/ambiguous; name agreement is not a verified career."
            ),
            "owner": "BAT-701",
            "dependencies": ["R33-05"],
            "next_deliverable": "Keep unresolved career keys; no same-name promotion.",
            "cycle33_implements_domain": True,
        },
        "c01": {
            "governing_requirement": "R33-16",
            "plan_sections": [
                file_sha("docs/contracts/proposed/StaffSnapshotV2.md"),
                file_sha("docs/cycle30/CFIP_RFC_CYCLE30.md"),
            ],
            "implementation_data_state": "StaffSnapshotV1 is lossy. C01_OWNER_ADOPTION_PENDING.",
            "owner": "BAT-704",
            "dependencies": ["R33-03", "R33-15"],
            "next_deliverable": "Owner adoption workflow; do not mutate dirty All-22 checkouts.",
            "cycle33_implements_domain": False,
            "owner_decision_required": True,
        },
    }

    remaining = {
        "injuries": {
            "dom": "DOM-011/DOM-012",
            "d_ids": ["D16"],
            "owner": "BAT-324",
            "covered_under": "availability tranche / R33-11/R33-14",
            "implementation_data_state": "NOT_ATTEMPTED /injuries; unknown remains unknown.",
            "next_deliverable": "National report-policy inventory under existing availability owner.",
        },
        "recruiting": {
            "dom": "DOM-013",
            "d_ids": ["D09"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Plan/contracts exist; Cycle 33 did not implement recruiting.",
            "next_deliverable": "Prospect-provider-vintage acquisition owned outside this staff cycle.",
        },
        "rosters": {
            "dom": "DOM-009",
            "d_ids": ["D07"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Roster contracts exist; not this cycle's staff mapping.",
            "next_deliverable": "Person-program-effective-episode membership with missingness.",
        },
        "resources": {
            "dom": "DOM-021",
            "d_ids": ["D35"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Unimplemented fiscal-year domain.",
            "next_deliverable": "Published-scope finance facts; no fabricated NIL spend.",
        },
        "weather": {
            "dom": "DOM-023/DOM-024",
            "d_ids": ["D21"],
            "owner": "BAT-417",
            "covered_under": None,
            "implementation_data_state": "Forecast vs observed remain distinct; not Cycle 33 materialization.",
            "next_deliverable": "Issue-time vs valid-hour weather with PIT cutoffs.",
        },
        "games": {
            "dom": "DOM-001",
            "d_ids": ["D01", "D03", "D04"],
            "owner": "BAT-705",
            "covered_under": "R33-02/R33-13 Week2 + official finals successor",
            "implementation_data_state": "Week2 census and official-final successor exist; not full historical spine claim.",
            "next_deliverable": "Keep unique-game denominators; no first/last-win.",
        },
        "plays": {
            "dom": "DOM-002/DOM-003/DOM-007",
            "d_ids": ["D24"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "TAMU lake play/drive gates exist historically; national play domain unfinished.",
            "next_deliverable": "Contest-event-sequence completeness outside this staff cycle.",
        },
        "markets": {
            "dom": "DOM-039",
            "d_ids": ["D26"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Unimplemented this cycle.",
            "next_deliverable": "Two-sided prices with timestamps; missing markets explicit.",
        },
        "officials": {
            "dom": "DOM-040/DOM-041",
            "d_ids": ["D25"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Unimplemented this cycle.",
            "next_deliverable": "Pregame assignment vs postgame observation.",
        },
        "penalties": {
            "dom": "DOM-040",
            "d_ids": ["D25"],
            "owner": "BAT-708",
            "covered_under": "officials (D25 contest-official/event)",
            "implementation_data_state": "No separate Cycle 33 penalty producer.",
            "next_deliverable": "Keep under D25; do not invent a new omnibus domain.",
        },
        "transfers": {
            "dom": "DOM-014",
            "d_ids": ["D10"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Unimplemented this cycle.",
            "next_deliverable": "Portal entry vs commitment vs enrollment vs inferred roster change.",
        },
        "snap_counts": {
            "dom": "DOM-008",
            "d_ids": ["D17"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Unimplemented this cycle.",
            "next_deliverable": "Pregame depth separate from observed participation.",
        },
        "tracking": {
            "dom": "DOM-051",
            "d_ids": ["D49"],
            "owner": "BAT-704",
            "covered_under": None,
            "implementation_data_state": "All-22/C01 pending; no tracking admission.",
            "next_deliverable": "Rights/coverage/annotator agreement before any film proxy.",
        },
        "depth_charts": {
            "dom": "DOM-010",
            "d_ids": ["D17"],
            "owner": "BAT-708",
            "covered_under": "snap_counts / D17",
            "implementation_data_state": "Unimplemented this cycle.",
            "next_deliverable": "Person-contest-status with unknown explicit.",
        },
        "nil": {
            "dom": "DOM-022",
            "d_ids": ["D36"],
            "owner": "BAT-708",
            "covered_under": "D36 NIL and revenue-sharing context",
            "no_match_reason": (
                "Token 'nil' missed path/heading search; governing domain is D36 / "
                "DOM-022 and SRC-056 regulatory context, not a fabricated spend metric."
            ),
            "plan_sections": [
                file_sha("docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md")
            ],
            "implementation_data_state": "Not implemented; policy context only if sourced.",
            "next_deliverable": "Verified policy/disclosure facts; no invented team NIL dollars.",
        },
        "returning_production": {
            "dom": None,
            "d_ids": ["D99"],
            "owner": "BAT-708",
            "covered_under": None,
            "no_match_reason": (
                "Not a named D01-D50 domain. D99 forbids stuffing into an omnibus bucket."
            ),
            "implementation_data_state": "Proposed requirement, not invented Cycle 33 authority.",
            "next_deliverable": "Owner names an explicit domain before any producer.",
        },
        "special_teams_units": {
            "dom": "DOM-031",
            "d_ids": ["D47"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Unimplemented this cycle.",
            "next_deliverable": "Component definitions with opponent adjustment, not staff-cycle success.",
        },
        "tempo": {
            "dom": "DOM-029",
            "d_ids": ["D47"],
            "owner": "BAT-708",
            "covered_under": "special_teams_units / D47",
            "implementation_data_state": "Unimplemented this cycle.",
            "next_deliverable": "Play-accounting tempo with calibration.",
        },
        "rest": {
            "dom": "DOM-036",
            "d_ids": ["D20", "D48"],
            "owner": "BAT-417",
            "covered_under": "neutral CTX-TR-04",
            "implementation_data_state": "Contract row exists; not fitted.",
            "next_deliverable": "Days since previous completed game only.",
        },
        "travel": {
            "dom": "DOM-027",
            "d_ids": ["D20"],
            "owner": "BAT-417",
            "covered_under": "neutral CTX-TR-01",
            "implementation_data_state": "Contract row exists; not fitted.",
            "next_deliverable": "Great-circle origin-to-venue; not blindly Kyle Field.",
        },
        "altitude": {
            "dom": "DOM-025",
            "d_ids": ["D19"],
            "owner": "BAT-417",
            "covered_under": "venue coordinates/elevation D19",
            "no_match_reason": (
                "Token 'altitude' missed headings; SRC-031 USGS elevation and D19 "
                "venue-effective-episode are the governing terms."
            ),
            "plan_sections": [
                file_sha("docs/data_research/w06/SOURCE_PRIORITY_DECISIONS.md")
            ],
            "implementation_data_state": "Not Cycle 33 materialization.",
            "next_deliverable": "Elevation as venue property, distinct from actual kickoff venue.",
        },
        "timezone": {
            "dom": "DOM-026",
            "d_ids": ["D20"],
            "owner": "BAT-417",
            "covered_under": "neutral CTX-TR-02/CTX-TR-03",
            "no_match_reason": (
                "Token 'timezone' missed remaining-union headings; governing rows are "
                "TIMEZONE_SHIFT and BODY_CLOCK in VENUE_TRAVEL_REST_CONTRACTS.csv."
            ),
            "plan_sections": [file_sha("governance/VENUE_TRAVEL_REST_CONTRACTS.csv")],
            "implementation_data_state": "Contract present; not Cycle 33 fitted feature.",
            "next_deliverable": "IANA/DST-aware shift; scheduled kickoff only.",
        },
        "high_school": {
            "dom": "DOM-015",
            "d_ids": ["D09", "D50"],
            "owner": "BAT-708",
            "covered_under": "freshman/prospect priors and recruiting",
            "no_match_reason": (
                "Token 'high_school' missed headings; D09 recruiting and D50 prospect "
                "priors are the catalog terms. No separate high-school domain invented."
            ),
            "implementation_data_state": "Not implemented this cycle.",
            "next_deliverable": "Prospect-provider-vintage with publication time; no future-info.",
        },
        "nfl_draft": {
            "dom": "DOM-016",
            "d_ids": ["D41"],
            "owner": "BAT-708",
            "covered_under": None,
            "implementation_data_state": "Unimplemented this cycle.",
            "next_deliverable": "Completed draft events excluded from earlier prospect features.",
        },
        "betting_splits": {
            "dom": "DOM-039",
            "d_ids": ["D26"],
            "owner": "BAT-708",
            "covered_under": "markets",
            "implementation_data_state": "Not a separate catalog domain; do not invent authority.",
            "next_deliverable": "If splits are required, owner names them under D26 or D99.",
        },
        "substitution": {
            "dom": None,
            "d_ids": ["D49", "D17"],
            "owner": "BAT-704",
            "covered_under": "personnel/tracking D49 and participation D17 if later specified",
            "no_match_reason": (
                "No DOM-xxx named 'substitution'. Not found as a plan heading. Closest "
                "catalog terms are D49 formation/personnel/tracking and D17 participation. "
                "Not treated as approved Cycle 33 authority."
            ),
            "implementation_data_state": "Genuinely absent as a named plan domain; proposed only.",
            "next_deliverable": "Owner decision whether to create an explicit D99/D-named domain.",
            "invented_plan_authority": False,
        },
        "play_calling_observed": {
            "dom": None,
            "d_ids": ["D15", "D28"],
            "owner": "BAT-164",
            "covered_under": "play-calling responsibility D15 vs film scheme D28",
            "implementation_data_state": "Titles are not play-caller inference; film not admitted.",
            "next_deliverable": "Keep explicit responsibility evidence distinct from titles.",
        },
        "film_formation": {
            "dom": "DOM-051",
            "d_ids": ["D28", "D49"],
            "owner": "BAT-704",
            "covered_under": "scheme D28 / tracking D49 / C01",
            "implementation_data_state": "Wikipedia scheme is not observed film formation.",
            "next_deliverable": "No All-22 dirty-checkout mutation; C01 pending.",
        },
    }
    for row in remaining.values():
        row["cycle33_implements_every_remaining_domain"] = False
        row["domains"] = [matrix[did] for did in row.get("d_ids") or [] if did in matrix]

    payload = {
        "artifact_type": "CYCLE33_PLAN_REMAINING_UNION",
        "as_of_utc": utc_now(),
        "remaining_named_not_manager_pending": True,
        "heading_keyword_search_is_not_substantive_review": True,
        "heuristic_8111_not_semantic_acceptance": True,
        "no_100_percent_mapped_claim": True,
        "national_fbs_fcs_historical_scope_preserved": True,
        "cycle33_does_not_implement_every_remaining_domain": True,
        "adjudicated_tranche": tranche,
        "remaining_full_system_union": remaining,
        "no_match_token_investigation": {
            "nil": remaining["nil"]["no_match_reason"],
            "altitude": remaining["altitude"]["no_match_reason"],
            "timezone": remaining["timezone"]["no_match_reason"],
            "high_school": remaining["high_school"]["no_match_reason"],
            "substitution": remaining["substitution"]["no_match_reason"],
        },
        "crosswalk_source": str(CROSSWALK),
        "domain_matrix_source": str(DOMAIN_MATRIX),
        "crosswalk_row_count": len(crosswalk),
        "predecessor_path_token_union_superseded": True,
    }
    write_json(SCI / "CYCLE33_PLAN_REMAINING_UNION.json", payload)
    write_json(
        SCI / "CYCLE33_PLAN_TRANCHE.json",
        {
            "artifact_type": "CYCLE33_PLAN_TRANCHE",
            "as_of_utc": utc_now(),
            "heuristic_8111_not_semantic_acceptance": True,
            "adjudicated_tranche": tranche,
            "remaining_union": "EXPLICITLY_UNFINISHED_FULL_SYSTEM_REQUIREMENT_UNION",
            "cs13_adopted_locally": True,
            "no_100_percent_mapped_claim": True,
            "consumers_named": {
                "coaching": ["cycle33.role_taxonomy", "cycle33.query", "CS-05 labels"],
                "scheme": ["cycle33.scheme_tenure", "cycle33.query"],
                "availability": ["cycle33.availability_cache", "cycle30.availability"],
                "neutral": ["cycle33.neutral"],
                "identity": ["cycle33.career_identity", "CYCLE33_STARTING_STACK"],
                "c01": ["cycle33.all22_adapter (lossy; adoption pending)"],
            },
        },
    )
    return payload


def approval_request() -> dict[str, Any]:
    payload = {
        "artifact_type": "CYCLE33_BAT649_BAT637_APPROVAL_REQUEST",
        "as_of_utc": utc_now(),
        "request_id": "CYCLE33-APPROVAL-LAKE-SUCCESSOR-001",
        "owners": ["BAT-649", "BAT-637"],
        "affected_paths": [
            "artifacts/data_lake/tamu_official_1998_2009_rejection_integrity_gate.json",
            "src/aggie_analytics/data/tamu_official_1998_2009_rejection_integrity.py",
            "artifacts/data_lake/tamu_official_gamebook_union_1998_expanded_gate.json",
            "src/aggie_analytics/data/tamu_official_gamebook_union_1998_rejection_complete.py",
            "artifacts/data_lake/tamu_official_1996_2009_structured_row_corpus_gate.json",
            "src/aggie_analytics/data/tamu_official_1996_2009_structured_row_corpus.py",
            "artifacts/data_lake/tamu_official_1998_2009_structured_row_corpus_integrity_gate.json",
            "src/aggie_analytics/data/tamu_official_1998_2009_structured_row_corpus_integrity.py",
        ],
        "proposed_operation": (
            "Publish versioned successor pin/gate/ledger pairs from independent "
            "reconstruction against the current immutable DATA_ROOT union manifest. "
            "Preserve predecessor bytes unchanged. Do not retarget pins to current "
            "hashes in place."
        ),
        "preservation_evidence": {
            "cycle32_head": "ca8e0a1f4ef3b30e4b50505e98b463daabcd7185",
            "cycle33_checked_head": "7918ab428b4d01f757b31686177ab44ff1849f36",
            "producer_and_gate_blobs_identical_at_both_heads": True,
            "focused_unittest_cycle32": "8 fail + 4 error",
            "focused_unittest_cycle33_before_family_a": "8 fail + 4 error",
            "data_root": "C:\\BatteredAggieSyndrome.data",
        },
        "validation_plan": (
            "After authorized successor publication: reconstruct in an isolated "
            "directory; compare successor identities; leave predecessor gates on "
            "disk; re-run the 12 focused tests plus mounted acceptance twice."
        ),
        "consequences_if_not_approved": (
            "Mounted full unittest and mounted acceptance remain FAIL. Cycle 33 "
            "must not describe the mounted validation dimension as PASS. Family A "
            "stale EXPECTED hashes are locally correctable without this approval."
        ),
        "not_requested": [
            "Overwrite historical gates in place",
            "Replace expected hashes to hide reconstruction mismatch for Family B",
            "Skip failing tests",
        ],
    }
    write_json(SCI / "CYCLE33_BAT649_BAT637_APPROVAL_REQUEST.json", payload)
    return payload


def update_failure_ledger() -> dict[str, Any]:
    ledger_path = SCI / "CYCLE33_MOUNTED_FAILURE_LEDGER.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["as_of_utc"] = utc_now()
    ledger["reproduction"] = {
        "data_root": "C:\\BatteredAggieSyndrome.data",
        "cycle32_worktree": r"C:\BatteredAggieSyndrome.data\ops\cycle33\diag_cycle32_ca8e0a1f",
        "cycle32_head": "ca8e0a1f4ef3b30e4b50505e98b463daabcd7185",
        "cycle33_head_at_reproduction": "7918ab428b4d01f757b31686177ab44ff1849f36",
        "focused_result_both_heads": "Ran 11 tests: failures=8 errors=4",
        "not_inferred_solely_from_unchanged_producer_files": True,
        "controlled_imports": True,
    }
    ledger["rows"] = [
        row
        for row in (ledger.get("rows") or [])
        if row.get("id") not in {"CORPUS-1996-2009", "CORPUS-INTEGRITY-1998-2009"}
    ]
    extra = [
        {
            "id": "CORPUS-1996-2009",
            "family": "1996_2009_structured_row_corpus",
            "test": "test_tamu_official_1996_2009_structured_row_corpus.Corpus19962009Tests.test_gate_reconstructs",
            "assertion_or_exception": (
                "AuthorityViolation: committed 1996-2009 corpus gate does not "
                "match independent reconstruction"
            ),
            "first_known_failing_baseline": "Cycle 32 HEAD ca8e0a1f against the same DATA_ROOT",
            "root_cause": (
                "Independent reconstruction mismatches the committed corpus gate. "
                "Same exception at Cycle 32 and Cycle 33."
            ),
            "affected_consumers": [
                "mounted full unittest",
                "mounted acceptance (if included)",
                "downstream 1998-2009 corpus integrity",
            ],
            "correction_or_authority": "Versioned successor requires owner approval; do not overwrite predecessor.",
        },
        {
            "id": "CORPUS-INTEGRITY-1998-2009",
            "family": "1998_2009_structured_row_corpus_integrity",
            "test": "test_tamu_official_1998_2009_structured_row_corpus_integrity.CorpusIntegrityTests.test_gate_reconstructs",
            "assertion_or_exception": "AuthorityViolation: external corpus-integrity manifest mismatch",
            "first_known_failing_baseline": "Cycle 32 HEAD ca8e0a1f against the same DATA_ROOT",
            "root_cause": (
                "External integrity manifest / reconstruction mismatch. Same at both heads."
            ),
            "affected_consumers": ["mounted full unittest", "mounted acceptance"],
            "correction_or_authority": "Versioned successor requires owner approval; do not overwrite predecessor.",
        },
    ]
    ledger["rows"].extend(extra)
    ledger["family_a_local_repair"] = (
        "Successor-labeled 2000-2005 and StatCrew test EXPECTED identities to the "
        "independently reconstructed committed gates. Predecessor hashes retained."
    )
    ledger["family_b_blocked"] = (
        "Rejection-integrity, BAT-637 pin, 1996-2009 corpus, and 1998-2009 corpus "
        "integrity remain FAIL pending CYCLE33-APPROVAL-LAKE-SUCCESSOR-001."
    )
    ledger["mounted_validation_dimension"] = "FAIL"
    ledger["repeatability_is_not_correctness"] = True
    write_json(ledger_path, ledger)
    return ledger


def main() -> int:
    scheme = review_schemes()
    titles = review_unmapped_titles()
    remaining = remaining_domain_backlog()
    approval = approval_request()
    ledger = update_failure_ledger()
    print(
        json.dumps(
            {
                "scheme_distinct": scheme["distinct_source_texts"],
                "scheme_claims": scheme["unnormalized_claim_count"],
                "unmapped_source_rows": titles["count"],
                "remaining_domains": len(remaining["remaining_full_system_union"]),
                "approval": approval["request_id"],
                "ledger_rows": len(ledger.get("rows") or []),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
