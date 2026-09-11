"""Manually adjudicate material verticals to plan/code. Not 8111 heuristic closure."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


VERTICALS = [
    {
        "vertical_id": "MV-PROGRAM-SOURCE",
        "requirement_ids": ["R32-03", "R32-04"],
        "plan_docs": [
            "50_BAS_INTEGRATION/07_COACH_TEAM_STATE.md",
            "50_BAS_INTEGRATION/01_CONTEXT_PUBLISHING.md",
        ],
        "code_entrypoints": [
            "src/aggie_analytics/cycle30/coaching.py:program_identity_binds",
            "src/aggie_analytics/cycle30/coaching.py:parse_official_staff_html",
            "tools/reparse_cycle32_official_staff.py",
        ],
        "evidence": [
            "science/CYCLE32_SOURCE_BINDINGS.jsonl",
            "science/CYCLE32_OFFICIAL_STAFF_REPARSE_SUMMARY.json",
        ],
        "adjudication": "MANUAL",
        "status": "IN_PROGRESS",
        "finding": (
            "Identity-bound official coaches pages exist for the nine manager "
            "wrong-school programs plus Georgia/Wisconsin. Utah Tech was WAC-"
            "quarantined; identity origin utahtechtrailblazers.com is the remaining "
            "current fetch. Conference hosts are skipped, not used as program origin."
        ),
        "remaining": "Washington media-guide PDF cache miss; not an NCAA census.",
    },
    {
        "vertical_id": "MV-STAFF-ROLES",
        "requirement_ids": ["R32-04", "R32-05", "WG32-01", "WG32-02"],
        "plan_docs": ["50_BAS_INTEGRATION/07_COACH_TEAM_STATE.md"],
        "code_entrypoints": [
            "src/aggie_analytics/cycle30/coaching.py:role_families_from_title",
            "src/aggie_analytics/cycle30/coaching.py:fill_current_role_matrix",
        ],
        "evidence": ["science/CYCLE32_STAFF_CELL_AUDIT.json"],
        "adjudication": "MANUAL",
        "status": "IN_PROGRESS",
        "finding": (
            "Deputy/director/unit head-coach-of-X titles are excluded from program HC. "
            "Bare Vue-mispaired Head Coach rows are dropped when the same person has OC/DC. "
            "Play-caller remains unsourced. Career-episode roundtrip unfinished."
        ),
        "remaining": "Reparse must confirm the nine prior multi-HC cells.",
    },
    {
        "vertical_id": "MV-HISTORICAL-COACHING",
        "requirement_ids": ["R32-06", "R32-07"],
        "plan_docs": ["50_BAS_INTEGRATION/07_COACH_TEAM_STATE.md"],
        "code_entrypoints": [
            "src/aggie_analytics/cycle30/populations.py:historical_program_season_keys",
            "tools/build_cycle32_historical_wiki_successor.py",
        ],
        "evidence": [
            "science/CYCLE32_HISTORICAL_EXPECTED_KEYS.json",
            "science/CYCLE32_HISTORICAL_WIKI_FRAME_COVERAGE.json",
        ],
        "adjudication": "MANUAL",
        "status": "IN_PROGRESS",
        "finding": (
            "Expected keys are CFBD membership (285 programs), not current-266 × years. "
            "Predecessor 17024 wiki rows remain current-survivor driven and are not overwritten. "
            "Wikipedia extraction is not factual verification."
        ),
        "remaining": "Full 2013-2023 HC/OC/DC re-adjudication against the 285-program frame.",
    },
    {
        "vertical_id": "MV-PIT-KERNEL",
        "requirement_ids": ["R32-08", "R32-09"],
        "plan_docs": [
            "50_BAS_INTEGRATION/03_FILM_PIT_SEMANTICS.md",
            "50_BAS_INTEGRATION/05_FILM_MODEL_ABLATION.md",
            "50_BAS_INTEGRATION/09_MODEL_PROMOTION.md",
        ],
        "code_entrypoints": [
            "src/aggie_analytics/cycle30/pit_kernel.py",
            "src/aggie_analytics/cycle30/kernel_model.py",
        ],
        "evidence": ["science/CYCLE32_KERNEL_NEUTRAL_AUDIT.json"],
        "adjudication": "MANUAL",
        "status": "IMPLEMENTED_PENDING_VERIFICATION",
        "finding": (
            "Malformed receipts cannot prove PIT. Missing numeric predictors abstain. "
            "No unrestricted administrative-home intercept. Fitted outputs remain UNTRUSTED_SHADOW. "
            "2024/2025 excluded. No Week1 winner selection."
        ),
        "remaining": "Positive proven-PIT count and independent validator exact-head hosted checks.",
    },
    {
        "vertical_id": "MV-NEUTRAL-TRAVEL",
        "requirement_ids": ["R32-10"],
        "plan_docs": ["50_BAS_INTEGRATION/08_MATCHUP_INTEGRATION.md"],
        "code_entrypoints": [
            "src/aggie_analytics/cycle30/kernel_model.py:swap_participants",
            "src/aggie_analytics/cycle30/kernel_model.py:favorite_direction",
        ],
        "evidence": ["science/CYCLE32_KERNEL_NEUTRAL_AUDIT.json"],
        "adjudication": "MANUAL",
        "status": "IMPLEMENTED_PENDING_VERIFICATION",
        "finding": (
            "216 eval neutrals × 4 candidates: participant-swap team-keyed delta 0. "
            "Travel numeric pass is not historical venue truth."
        ),
        "remaining": "Historical venue coordinates still not a truth set.",
    },
    {
        "vertical_id": "MV-SCORING-VALIDATOR",
        "requirement_ids": ["R32-11", "R32-12"],
        "plan_docs": ["50_BAS_INTEGRATION/10_END_TO_END_FORECAST_FLOW.md"],
        "code_entrypoints": [
            "src/aggie_analytics/cycle30/scoring.py",
            "tools/validate_cycle30_gates.py",
        ],
        "evidence": [],
        "adjudication": "MANUAL",
        "status": "IMPLEMENTED_PENDING_VERIFICATION",
        "finding": (
            "Same-page score bind fail-closes. Validator science path uses live "
            "challenge_kernel_rows. Coordinated tamper exits nonzero."
        ),
        "remaining": "Real scored-row reconstruction from raw captures; exact-head hosted checks.",
    },
    {
        "vertical_id": "MV-AVAILABILITY",
        "requirement_ids": ["R32-13"],
        "plan_docs": ["50_BAS_INTEGRATION/06_PLAYER_STATE_INTEGRATION.md"],
        "code_entrypoints": [
            "src/aggie_analytics/cycle30/availability.py:join_candidates_to_roster",
            "tools/parse_cycle32_availability_cache.py",
        ],
        "evidence": ["science/CYCLE32_AVAILABILITY_CACHE_PARSE.json"],
        "adjudication": "MANUAL",
        "status": "IN_PROGRESS",
        "finding": (
            "Join requires program + name (and season when both present). Cache-first parse: "
            "14 routes, 0 candidate player rows. Acquisition remains BLOCKED, not locally complete."
        ),
        "remaining": "Lawful public report records or exact exhausted route/key blockers.",
    },
    {
        "vertical_id": "MV-C01-ADAPTER",
        "requirement_ids": ["R32-15", "R32-16"],
        "plan_docs": [
            "50_BAS_INTEGRATION/07_COACH_TEAM_STATE.md",
            "50_BAS_INTEGRATION/01_CONTEXT_PUBLISHING.md",
            "50_BAS_INTEGRATION/11_ACCEPTANCE.md",
        ],
        "code_entrypoints": [
            "src/aggie_analytics/cycle30/contracts_v2.py:staff_snapshot_v2_from_bas_matrix_cell",
            "docs/contracts/proposed/StaffSnapshotV2.md",
            "docs/contracts/proposed/CoachStateV2.md",
        ],
        "evidence": ["science/CYCLE32_STAFF_CELL_AUDIT.json"],
        "adjudication": "MANUAL",
        "status": "IN_PROGRESS",
        "finding": (
            "798/798 successor cells convert through StaffSnapshotV2 locally. "
            "Proposed plan RFCs are BAS-owned and unaccepted. All-22 checkouts were not mutated."
        ),
        "remaining": "Owner-controlled C01/CFIP adoption. CFIP-18/20/22/23 coordination.",
    },
    {
        "vertical_id": "MV-NATIONAL-GAME-CORE",
        "requirement_ids": ["R32-17", "R32-11"],
        "plan_docs": ["50_BAS_INTEGRATION/10_END_TO_END_FORECAST_FLOW.md"],
        "code_entrypoints": [
            "tools/audit_cycle32_national_game_core.py",
            "tools/enumerate_cycle32_ncaa_scoreboard_finals.py",
        ],
        "evidence": [
            "science/CYCLE32_NATIONAL_GAME_CORE_AUDIT.json",
            "science/CYCLE32_NCAA_SCOREBOARD_FINALS_CENSUS.json",
        ],
        "adjudication": "MANUAL",
        "status": "IN_PROGRESS",
        "finding": (
            "Cycle32 independently recounts the declared 46,953-row parent. "
            "Provider field presence is not NCAA official-final event truth. "
            "Week1 2026 NCAA.com scoreboards bind 198 contests; broader NCAA raw "
            "captures remain absent."
        ),
        "remaining": "Historical NCAA official-final reconstruction blocked by absent raw captures.",
    },
    {
        "vertical_id": "MV-HISTORICAL-OC-DC",
        "requirement_ids": ["R32-07", "WG32-06", "WG32-08", "WG32-09"],
        "plan_docs": ["50_BAS_INTEGRATION/07_COACH_TEAM_STATE.md"],
        "code_entrypoints": [
            "tools/corroborate_cycle32_historical_staff_cells.py",
            "tools/corroborate_cycle32_wiki_cfbd_hc.py",
        ],
        "evidence": [
            "science/CYCLE32_HISTORICAL_STAFF_CELL_DISPOSITIONS.json",
            "science/CYCLE32_WIKI_CFBD_HC_FIELD_CLAIMS.json",
        ],
        "adjudication": "MANUAL",
        "status": "IN_PROGRESS",
        "finding": (
            "Every 2013-2023 expected HC/OC/DC cell has an explicit disposition. "
            "OC/DC Wikipedia names remain WIKI_ONLY_NO_INDEPENDENT_PRIMARY. "
            "CFBD /coaches is HC-only. Sportradar current roster is not historical official HTML."
        ),
        "remaining": "Independent official historical OC/DC HTML/media-guide captures.",
    },
]


def main() -> int:
    science = OUT / "science"
    payload = {
        "artifact_type": "CYCLE32_MATERIAL_VERTICAL_PLAN_TRACE",
        "adjudication_method": "MANUAL_PER_VERTICAL",
        "heuristic_8111_relationship_rows": {
            "status": "HEURISTIC_MAPPED_OWNER_REVIEW_PENDING",
            "counts_as_r31_18_fulfillment": False,
            "counts_as_r32_14_fulfillment": False,
            "note": (
                "Cycle31 8111 governing-token heuristic mappings remain candidates. "
                "They are not semantic closure and are not reused as PASS."
            ),
        },
        "governing_negative_contracts": [
            {
                "path": "configs/action_derived_play_summary_contract.json",
                "classification": "GOVERNING_CANDIDATE_ONLY",
                "not": "NON_GOVERNING",
                "reason": (
                    "The contract is a negative constraint: action-derived play summaries "
                    "have no native-play, PIT, feature, protected, forecast, or canonical "
                    "admission. Relabeling it NON_GOVERNING would erase required exclusions."
                ),
            },
            {
                "path": "configs/historical_known_at_recovery_contract.json",
                "classification": "GOVERNING_CANDIDATE_ONLY",
                "not": "NON_GOVERNING",
                "reason": (
                    "Known-at recovery is an admission/schema constraint. Treating it as "
                    "descriptive NON_GOVERNING would drop required PIT exclusion rules."
                ),
            },
            {
                "path": "configs/artifact_binding_contract.json",
                "classification": "GOVERNING_CANDIDATE_ONLY",
                "not": "NON_GOVERNING",
                "reason": (
                    "Artifact identity binding governs source/hash admission. It is not a "
                    "narrative-only document."
                ),
            },
        ],
        "unmapped_52_domain_inventory": [
            {"domain_id": domain_id, "label": label, "status": "UNMET_NOT_LATER"}
            for domain_id, label in (
                ("DOM-001", "games/schedules/scores"),
                ("DOM-002", "play-by-play"),
                ("DOM-003", "drives"),
                ("DOM-004", "team statistics"),
                ("DOM-005", "advanced team efficiency"),
                ("DOM-006", "player statistics"),
                ("DOM-007", "play participants"),
                ("DOM-008", "snap counts/participation"),
                ("DOM-009", "rosters"),
                ("DOM-010", "starters/depth charts"),
                ("DOM-011", "injuries/availability current"),
                ("DOM-012", "injuries/availability historical"),
                ("DOM-013", "recruiting"),
                ("DOM-014", "transfers"),
                ("DOM-015", "freshman/prospect priors"),
                ("DOM-016", "NFL draft outcomes"),
                ("DOM-017", "preseason honors/watch lists"),
                ("DOM-018", "head coaches/coordinators"),
                ("DOM-019", "assistant coaches/role histories"),
                ("DOM-020", "scheme/style/tendencies"),
                ("DOM-021", "program resources/finance"),
                ("DOM-022", "NIL/revenue-sharing regulatory context"),
                ("DOM-023", "historical issued weather forecasts"),
                ("DOM-024", "observed weather"),
                ("DOM-025", "venue coordinates/elevation"),
                ("DOM-026", "timezone/body clock"),
                ("DOM-027", "travel distance"),
                ("DOM-028", "home-field/venue effect"),
                ("DOM-029", "possession/tempo"),
                ("DOM-030", "field position/hidden yards"),
                ("DOM-031", "special teams"),
                ("DOM-032", "fourth-down decisions"),
                ("DOM-033", "clock management"),
                ("DOM-034", "garbage time/score state"),
                ("DOM-035", "opponent adjustment"),
                ("DOM-036", "schedule stress/workload"),
                ("DOM-037", "poll rankings"),
                ("DOM-038", "external ratings"),
                ("DOM-039", "markets"),
                ("DOM-040", "officials/crew history"),
                ("DOM-041", "officials upcoming assignments"),
                ("DOM-042", "playing rule era"),
                ("DOM-043", "eligibility/roster/transfer regulatory era"),
                ("DOM-044", "game stakes/CFP state"),
                ("DOM-045", "rivalry/homecoming/senior day"),
                ("DOM-046", "FCS strength"),
                ("DOM-047", "DII/DIII strength"),
                ("DOM-048", "NAIA strength"),
                ("DOM-049", "JUCO strength"),
                ("DOM-050", "live/in-game"),
                ("DOM-051", "advanced formation/personnel/tracking"),
                ("DOM-052", "licensing/redistribution metadata"),
            )
        ],
        "verticals": VERTICALS,
        "unmapped_requirement_union_domains": (
            "The original 52-domain matrix remains an obligation. This trace covers only "
            "the Cycle32 material verticals. Unvisited domains stay unmet, not later."
        ),
        "as_of_utc": utc_now(),
        "c01_adoption_claimed": False,
        "scientific_acceptance": "BLOCKED",
    }
    science.mkdir(parents=True, exist_ok=True)
    (science / "CYCLE32_MATERIAL_VERTICAL_PLAN_TRACE.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verticals": len(VERTICALS), "as_of_utc": payload["as_of_utc"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
