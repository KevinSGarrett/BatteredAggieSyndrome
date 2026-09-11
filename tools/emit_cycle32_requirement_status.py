"""Emit Cycle32 requirement ledger with honest current states. Not acceptance."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle30.cycle_completion import validate_ledger  # noqa: E402

REGISTER = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle32\REQUIREMENT_REGISTER.json")
OUT = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle32\runs\20260911T045553Z\implementation_output"
)

STATES = {
    "R32-01": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "Dirty Cycle31+32 tree committed on codex/BAT-706-cycle32. Tests bind this commit; hosted exact-head checks remain R32-19.",
    ),
    "R32-02": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "Predecessor Cycle30 outputs left in place. CYCLE32_PREDECESSOR_SUCCESSOR_MAP.json and CYCLE32_TAMU_GATE_RECORD_COMPARISON.json classify dirty TAMU/gate deltas. Identity rebinds are not predecessor overwrites. Historical test expectations were not rewritten to bless current output.",
    ),
    "R32-03": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "266/266 current programs have verified identity-bound official staff bindings. Utah Tech=utahtechtrailblazers.com; Washington=gohuskies.com (HTML, not the missing media-guide PDF). Washington 2026 OC is Jedd Fisch by operator dual-occupancy; the captured page still does not print an OC title.",
    ),
    "R32-04": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "Successor matrix 661 CONFIRMED / 112 CO_SHARED / 25 UNKNOWN. Unique people 6215. Excluded spans 2606 with reason codes. Minnesota DC is Danny Collins (Defensive Coordinator / Safeties) and Nick Monroe (Cornerbacks / Co-Defensive Coordinator) from same-row official titles, not Vue zip. Special-assistant-to-coordinator titles are not OC/DC. One official play-caller title was sourced (Maurice Crum Jr., Co-Defensive Coordinator / Play Caller). National play-calling remains incomplete. Model admission NOT_ADMITTED.",
    ),
    "R32-07": (
        "IN_PROGRESS",
        "Cache-only predecessor wiki reparse: 17024/17024 rows remain. Every 2013-2023 expected HC/OC/DC cell has an explicit disposition (8355 cells). 4097 OC/DC cells are WIKI_ONLY_NO_INDEPENDENT_PRIMARY. CFBD /coaches is HC-only and not official HTML. Sportradar current roster is not historical official HTML. Wikipedia is not factual verification.",
    ),
    "R32-14": (
        "IN_PROGRESS",
        "Ten material verticals were manually traced, including national-game-core and 2013-2023 HC/OC/DC dispositions. 8111 heuristic plan mappings remain HEURISTIC_MAPPED_OWNER_REVIEW_PENDING. All 52 W06 domains remain listed as UNMET_NOT_LATER. action_derived_play_summary_contract, historical_known_at_recovery_contract, and artifact_binding_contract stay GOVERNING_CANDIDATE_ONLY.",
    ),
    "R32-16": (
        "IN_PROGRESS",
        "BAS-owned StaffSnapshotV2/CoachStateV2 docs updated to match the local checker. Private All22/C01 RFC written; All-22 checkouts were not mutated. Adoption not claimed.",
    ),
    "R32-17": (
        "IN_PROGRESS",
        "Seven named three-pass audits emitted. Declared 46,953-row parent independently recounted (observed=46953, unique ids=46953, fitted 2013-2023=9368). Provider agreement is not event truth. all_local_reconstruction_complete=false.",
    ),
    "R32-05": (
        "IN_PROGRESS",
        "Successor as_of is 2026-09-11 not predecessor 2026-09-07. Duplicate person-string cells are 0. Current-occupant career roundtrip: 878 occupants, 565 matched wiki pages (predecessor plus 188 Cycle32 successor pages), 357 nonempty candidate careers, 313 still missing, 0 PIT promotions. Official title scan sourced one play-caller: Maurice Crum Jr. (SRC-002:TEAM:2567) Co-Defensive Coordinator / Play Caller. Wikipedia careers are not verification.",
    ),
    "R32-06": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "CFBD membership keys 1963-2026: predecessor 1963-2023 plus Cycle32 /teams successor for 2024/2025/2026 (794 FBS/FCS rows). Not an NCAA sponsorship census.",
    ),
    "R32-08": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "Malformed/unproven receipts cannot yield PROVEN. Freeze receipts cannot prove feature PIT. Predecessor claimed-PROVEN rows were traced; independently_proven_cycle32 is 0 because contributing receipts/lineage are missing. No positive PIT count was manufactured.",
    ),
    "R32-09": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "fold_local_fit excludes 10 missing-margin games (7 train / 3 eval). Independent recompute of 8216 historical rows exists as UNTRUSTED_SHADOW. No Week1 winner selection.",
    ),
    "R32-10": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "All 216 eval neutrals × 4 candidates: participant-swap team-keyed delta 0. intercept_only is 0.5/NO_DIRECTION. Travel numeric pass is not historical venue truth.",
    ),
    "R32-11": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "3/3 remaining Week1 contests reconstructed from cached NCAA.com scoreboards. Census of those scoreboards: 198 contests bind through _bind_scores_from_same_page. stats.ncaa.org IDs are absent (403). Broader historical NCAA official-final reconstruction is blocked by absent raw contest captures beyond Week1 2026. Trust UNTRUSTED_SHADOW.",
    ),
    "R32-12": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "Live challenge_kernel_rows in _science; coordinated tamper CLI exits nonzero. Full strict/mounted exact-head still required.",
    ),
    "R32-15": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "All 798 successor matrix cells convert through StaffSnapshotV2 (adapter_fail=0). C01 adoption not claimed.",
    ),
    "R32-13": (
        "BLOCKED_EXTERNAL",
        "14 policy/archive pages plus 22 report-hinted assets yielded 0 player-status records. Record-book/media-guide names were rejected as not availability. CFBD /injuries returned HTTP 404 for 2024-2026. Sportradar NCAAFB weekly injuries returned HTTP 404. Required nonempty official-report acquisition remains BLOCKED, not locally complete.",
    ),
    "R32-18": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "Read-only live Jira confirmed BAT-706/701/700 In Review and BAT-523 In Progress. Bounded Cycle32 evidence comments posted: 14924-14928. No Done. Not a BAT-523 completion comment.",
    ),
    "R32-19": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "Isolated non-editable package lane PASS_LOCAL: GameContextV2 schema now ships in-package; Cycle32 manager tests imported from site-packages with PYTHONPATH cleared. Hosted exact-head checks on this commit remain required. Skipped paid review stays NOT_REVIEWED.",
    ),
    "R32-20": (
        "IMPLEMENTED_PENDING_VERIFICATION",
        "Completion-contract states and negative tests are enforced in cycle_completion.py. Headline cannot be CYCLE_COMPLETE.",
    ),
    "R32-21": (
        "PENDING_RELEASE_AUTHORITY",
        "Operator hold ACTIVE. No merge, release, protected-lane activation, or BAT-523 completion comment.",
    ),
}


def main() -> None:
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    git_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr",
        text=True,
    ).strip()
    rows = []
    counts = {}
    for item in register["requirements"]:
        rid = item["requirement_id"]
        state, remaining = STATES.get(
            rid,
            (
                item.get("state") or "NOT_STARTED",
                item.get("remaining_action")
                or "Implement full section; no PASS from ledger generation.",
            ),
        )
        if rid.startswith("WG32-"):
            state = "IN_PROGRESS"
            remaining = (
                "WG32 clauses are bound; Wikipedia discovery is not factual verification. "
                "Exact manager WIKI32-01..05 fixtures now enter production entrypoints. "
                "Full corroboration unfinished."
            )
        updated = {
            **item,
            "state": state,
            "implementation_evidence": [
                str(OUT / "science" / "CYCLE32_OFFICIAL_STAFF_REPARSE_SUMMARY.json"),
                str(OUT / "science" / "CYCLE32_HISTORICAL_EXPECTED_KEYS.json"),
                "tests/test_cycle32_manager_counterexamples.py",
            ]
            if rid in STATES and state != "NOT_STARTED"
            else [],
            "manager_acceptance": "PENDING",
            "remaining_action": remaining,
        }
        rows.append(updated)
        counts[state] = counts.get(state, 0) + 1
    payload = {
        "cycle": 32,
        "headline": "IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED",
        "hold": "ACTIVE",
        "scientific_acceptance": "BLOCKED",
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "worktree": r"C:\BatteredAggieSyndrome.data\worktrees\cycle30-scr",
        "branch": "codex/BAT-706-cycle32",
        "git_head": git_head,
        "actual_git_head": git_head,
        "expected_ids": register.get("expected_ids") or [],
        "committed_submission": True,
        "state_counts": counts,
        "requirements": rows,
        "notes": [
            "Cycle31 is NOT ACCEPTED. Local reconstruction of all named units is not complete.",
            "Fitted outputs remain UNTRUSTED_SHADOW. No BAS/Aggie Excess/production claim.",
            "Nine manager wrong-school programs now have identity-correct captured official staff pages; Utah Tech is a verified trailblazers.com binding.",
        ],
    }
    validate_ledger(payload)
    path = OUT / "CYCLE_REQUIREMENT_STATUS.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    unfinished = {
        "cycle": 32,
        "headline": "IMPLEMENTATION_SUBMITTED_NOT_ACCEPTED",
        "hold": "ACTIVE",
        "scientific_acceptance": "BLOCKED",
        "git_head": git_head,
        "items": [
            {
                "id": "U32-02",
                "requirement_id": "R32-03",
                "local_or_external": "EXTERNAL_PLUS_LOCAL",
                "item": "266/266 current programs have verified official staff bindings. 25 remaining UNKNOWN OC/DC are pass/run-game or unlisted. Washington media-guide PDF remains cache-missing.",
            },
            {
                "id": "U32-04",
                "requirement_id": "R32-05",
                "local_or_external": "LOCAL",
                "item": "Career roundtrip: 878 occupants, 565 matched wiki pages, 313 still missing, 0 PIT promotions. One official play-caller title sourced. Wikipedia careers are not verification.",
            },
            {
                "id": "U32-06",
                "requirement_id": "R32-07",
                "local_or_external": "LOCAL",
                "item": "8355 expected 2013-2023 HC/OC/DC cells have dispositions. 4097 OC/DC cells remain WIKI_ONLY_NO_INDEPENDENT_PRIMARY. Independent official HTML corroboration unfinished.",
            },
            {
                "id": "U32-07",
                "requirement_id": "R32-08",
                "local_or_external": "LOCAL",
                "item": "independently_proven_cycle32=0. No positive PIT count was manufactured.",
            },
            {
                "id": "U32-08",
                "requirement_id": "R32-11",
                "local_or_external": "EXTERNAL_PLUS_LOCAL",
                "item": "Week1 2026 NCAA.com scoreboards bind 198 contests. Broader historical NCAA official-final reconstruction is blocked by absent raw captures. stats.ncaa.org 403.",
            },
            {
                "id": "U32-09",
                "requirement_id": "R32-13",
                "local_or_external": "EXTERNAL",
                "item": "0 player-status records after policy pages, report-hinted assets, CFBD /injuries 404, and Sportradar weekly injuries 404. Required nonempty official-report acquisition is BLOCKED_EXTERNAL.",
            },
            {
                "id": "U32-10",
                "requirement_id": "R32-14",
                "local_or_external": "LOCAL",
                "item": "Ten material verticals traced. 8111 heuristic mappings remain candidates. 52-domain union unmet.",
            },
            {
                "id": "U32-11",
                "requirement_id": "R32-16",
                "local_or_external": "LOCAL",
                "item": "All22/C01 adoption remains owner-controlled. All-22 checkouts were not mutated.",
            },
            {
                "id": "U32-12",
                "requirement_id": "R32-17",
                "local_or_external": "LOCAL",
                "item": "Seven named three-pass audits emitted; all_local_reconstruction_complete=false. 46953-row provider recount is not independent event truth.",
            },
            {
                "id": "U32-14",
                "requirement_id": "R32-19",
                "local_or_external": "LOCAL",
                "item": "Isolated package lane PASS_LOCAL. Hosted exact-head checks must bind this commit. Skipped paid review stays NOT_REVIEWED.",
            },
            {
                "id": "U32-15",
                "requirement_id": "R32-21",
                "local_or_external": "HOLD",
                "item": "Operator hold ACTIVE. No merge, release, protected-lane activation, or BAT-523 completion comment. Cycle complete is not authorized.",
            },
        ],
    }
    (OUT / "CYCLE32_UNFINISHED_ITEMS.json").write_text(
        json.dumps(unfinished, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"headline": payload["headline"], "state_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
