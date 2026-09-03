"""Bind Cycle #26 passing-section and status-successor evidence."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\BatteredAggieSyndrome.data\worktrees\BAT-690-c26-scr")
OPS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle26")
ART = REPO / "artifacts/scientific_integrity/cycle26"
HEAD = "LIVE_PR_678_TIP"
PR = "https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/678"
BASE = "55e12a5aad3a7e843204fcba619c3cb3d3d6194d"
WEEK1_GATE = "aa4ff84b16e9f00b1e68965cef7ea8730adc456ad16bda6ed1ff564b5bcdcb43"
WEEK1_DATASET = "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
HIST_GATE = "1bb15df0bfc466dfaeaa730e7895d12db965b8a79542d6e750ba3871133d43b0"
HIST_DATASET = "f52d01aaa68543ead9067c1886ab5e6b40fdaeb6f009c9f8bdf5b61d7fecbfb9"


def dump(path: Path, payload: dict) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_bytes(text.encode("utf-8"))


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    passing_gate = json.loads(
        (
            REPO
            / "artifacts/data_lake/tamu_official_passing_section_successor_gate.json"
        ).read_text(encoding="utf-8")
    )
    status_gate = json.loads(
        (
            REPO / "artifacts/data_lake/national_foundation_status_successor_gate.json"
        ).read_text(encoding="utf-8")
    )
    hist_gate = json.loads(
        (
            REPO
            / "artifacts/experimentation/historical_saved_pair_game_grain_successor_gate.json"
        ).read_text(encoding="utf-8")
    )
    pred_c20 = json.loads(
        (
            REPO
            / "artifacts/experimentation/national_expectation_baselines_and_peers_gate.json"
        ).read_text(encoding="utf-8")
    )
    pred_metrics = {row["candidate_id"]: row["brier"] for row in pred_c20["candidates"]}
    succ_metrics = {
        row["candidate_id"]: row["brier"]
        for row in hist_gate["cycles"]["20"]["metrics"]["by_candidate"]
    }
    impact_c20 = {
        "artifact_type": "CYCLE26_R26_20_OLD_NEW_IMPACT",
        "issued_at_utc": now,
        "predecessor_rewritten": False,
        "predecessor_metrics_status": "DEPRECATED_INCOHERENT_TEAM_GRAIN_NOT_AUTHORITATIVE",
        "successor_gate_identity": hist_gate["gate_identity"],
        "successor_dataset_identity": hist_gate["dataset_identity"],
        "denominator_old": "TEAM_ORIENTED_ROWS_1820_NOT_AUTHORITATIVE",
        "denominator_new": "UNIQUE_GAME_NOT_ORIENTED_ROW",
        "orientation_convention": "LEXICOGRAPHIC_FIRST_CANONICAL_TEAM_ID",
        "joint_probability_margin_interval": False,
        "candidates": [
            {
                "candidate_id": candidate,
                "predecessor_team_grain_brier_deprecated": pred_metrics[candidate],
                "successor_unique_game_brier": succ_metrics[candidate],
                "disagreement_attributable_to": (
                    "pair_normalization_and_unique_game_denominator_not_cosmetic_renorm"
                ),
            }
            for candidate in sorted(succ_metrics)
        ],
        "scientific_nonclaims": [
            "Numerical agreement with deprecated team-grain metrics is not required.",
            "Does not restore original C20 metrics as authoritative.",
            "Does not claim Week 1 prospective skill.",
        ],
    }
    dump(ART / "CYCLE26_R26_20_OLD_NEW_IMPACT.json", impact_c20)

    r26_21 = {
        "artifact_type": "CYCLE26_R26_21_CONTAINMENT",
        "issued_at_utc": now,
        "finding": "R26-21",
        "disposition": "CONFIRMED_FIXED",
        "owner": "BAT-692",
        "parser_helpers": (
            "src/aggie_analytics/data/tamu_official_statcrew_preformatted.py "
            "recognizes Att-Cmp-Int/Cmp-Att-Int; successor materializes corrected rows"
        ),
        "historical_census": {
            "confirmed_mislabeled_passing_rows": 429,
            "confirmed_affected_raw_pages": 125,
            "screened_nonpassing_triple_rows": passing_gate["census"][
                "screened_nonpassing_triple_rows"
            ],
            "unresolved_section_matches": passing_gate["census"][
                "unresolved_section_matches"
            ],
            "corpus_path": passing_gate["predecessor"]["relative_path"],
            "predecessor_sha256": passing_gate["predecessor"]["sha256"],
            "rewritten": False,
        },
        "successor": {
            "gate_identity": passing_gate["gate_identity"],
            "dataset_identity": passing_gate["dataset_identity"],
            "changed_stat_group_rows": 429,
            "unchanged_rows": passing_gate["impact"]["unchanged_rows"],
            "unresolved_rows": passing_gate["impact"]["unresolved_rows"],
            "confirmed_team_attributed_rows": passing_gate["impact"][
                "confirmed_team_attributed_rows"
            ],
            "counts_by_season": passing_gate["census"]["counts_by_season"],
            "independent_reconstruction": "PASS",
        },
        "national_forecast_consumption_proven": False,
        "active_path_effect": (
            "Declared Week1 national fitted successor does not consume the player corpus; "
            "join_audit active_path_import_edges=0"
        ),
        "active_path_import_closure_bat591_edges": 0,
        "adversarial_proof": [
            "test_26_passing_header_does_not_inherit_rushing",
            "test_r26_21_active_path_does_not_import_statcrew",
            "tests/test_tamu_official_passing_section_successor.py",
        ],
        "pr": PR,
        "base_sha": BASE,
        "active_path_gate_identity": WEEK1_GATE,
        "code_head_binding": HEAD,
        "residual_risk": (
            "45 unresolved ambiguous-section screen candidates remain unlabeled as passing; "
            "full season-domain parser cascade was not replayed; national model join is unproven."
        ),
    }
    dump(ART / "CYCLE26_R26_21_CONTAINMENT.json", r26_21)

    status = {
        "artifact_type": "CYCLE26_7A7_FALSE_QUARANTINE_312472199",
        "issued_at_utc": now,
        "finding": "C26-7A7-FALSE-QUARANTINE-312472199",
        "disposition": "CONFIRMED_FIXED",
        "owner": "BAT-651",
        "predecessor_quarantine_rewritten": False,
        "source_identity": {
            "canonical_game_id": "SRC-002:GAME:312472199",
            "season": 2011,
            "home_team_name": "Eastern Michigan",
            "away_team_name": "Howard",
            "home_points": 41,
            "away_points": 9,
            "outcome_result": "HOME_WIN",
            "venue_name": "Rynearson Stadium",
            "note": (
                "Informal Howard-EMU 41-9 naming is not home-away order; "
                "authority is CFBD GAME-grain source: EMU home 41, Howard away 9."
            ),
        },
        "successor": {
            "gate_identity": status_gate["gate_identity"],
            "dataset_identity": status_gate["dataset_identity"],
            "disposition": "RESTORE_FALSE_SUBSTRING_QUARANTINE",
            "pit_feature_eligible": False,
            "independent_reconstruction": "PASS",
        },
        "completed_string_not_coerced": True,
        "pr": PR,
        "code_head_binding": HEAD,
        "residual_risk": (
            "Predecessor national foundation remains quarantined for this id; "
            "consumers must bind the successor explicitly. PIT admission stays closed."
        ),
    }
    dump(ART / "CYCLE26_7A7_FALSE_QUARANTINE_312472199.json", status)

    matrix_path = ART / "CYCLE26_FINDING_DISPOSITION_MATRIX.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["issued_at_utc"] = now
    matrix["code_head_binding"] = HEAD
    found_r21 = False
    for entry in matrix["entries"]:
        if entry.get("id") == "R26-21":
            found_r21 = True
            entry.update(
                {
                    "disposition": "CONFIRMED_FIXED",
                    "correction": (
                        "Immutable passing-section successor recodes 429 confirmed rows to passing "
                        "without rewriting the 1996-2009 predecessor; TEAM rows stay team-attributed; "
                        "45 unresolved screen candidates remain unresolved."
                    ),
                    "successor_gate": passing_gate["gate_identity"],
                    "independently_reconstructed": True,
                    "red_before_green_after": (
                        "tests/test_tamu_official_passing_section_successor.py + "
                        "tools/validate_tamu_official_passing_section_successor.py"
                    ),
                    "residual_risk": r26_21["residual_risk"],
                }
            )
    extra_ids = {entry.get("id") for entry in matrix["entries"]}
    if "C26-7A7-FALSE-QUARANTINE-312472199" not in extra_ids:
        matrix["entries"].append(
            {
                "acceptance_authority": "USER_EXPLICIT_ONLY",
                "id": "C26-7A7-FALSE-QUARANTINE-312472199",
                "owner": "BAT-651",
                "severity": "P1",
                "disposition": "CONFIRMED_FIXED",
                "correction": (
                    "Structured-status successor restores SRC-002:GAME:312472199 from verified "
                    "boolean completed + scores; predecessor quarantine preserved."
                ),
                "successor_gate": status_gate["gate_identity"],
                "independently_reconstructed": True,
                "red_before_green_after": (
                    "tests/test_national_foundation_status_successor.py + "
                    "tools/validate_national_foundation_status_successor.py"
                ),
                "residual_risk": status["residual_risk"],
            }
        )
    if not found_r21:
        raise SystemExit("R26-21 missing from matrix")
    dump(matrix_path, matrix)

    acc_path = ART / "CYCLE26_ACTIVE_PATH_ACCEPTANCE.json"
    acc = json.loads(acc_path.read_text(encoding="utf-8"))
    acc["issued_at_utc"] = now
    acc["passing_section_successor"] = {
        "gate_identity": passing_gate["gate_identity"],
        "dataset_identity": passing_gate["dataset_identity"],
        "confirmed_rows": 429,
        "active_path_import_edges": 0,
    }
    acc["status_successor"] = {
        "gate_identity": status_gate["gate_identity"],
        "dataset_identity": status_gate["dataset_identity"],
        "restored_game": "SRC-002:GAME:312472199",
        "pit_feature_eligible": False,
    }
    acc["R26_21_NOTE"] = (
        "R26-21 CONFIRMED_FIXED via passing-section successor; Week1 path still has zero StatCrew import edges."
    )
    acc["PRIMARY_OBJECTIVE_NOTE"] = (
        "PRIMARY_TRUST_RECOVERY_INCOMPLETE: R26-09 CONFIRMED_UNRESOLVED pass-two backlog; "
        "R26-13 admin thresholds; R26-22 CONFIRMED_CONTAINED_NOT_FIXED; "
        "R26-20/R26-21 and 312472199 restored via successors without rewriting predecessors. "
        "Joint Week 1 successor remains UNTRUSTED_SHADOW. Pass3 PENDING_INDEPENDENT_REVIEWER. "
        "Predictive skill is DEVELOPMENT_EVIDENCE_ONLY."
    )
    dump(acc_path, acc)

    backlog_path = ART / "CYCLE26_REMAINING_AUDIT_BACKLOG.json"
    backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
    backlog["issued_at_utc"] = now
    backlog["code_head_binding"] = HEAD
    for item in backlog.get("named_open_scientific_units", []):
        if item.get("id") == "R26-21":
            item["state"] = "CONFIRMED_FIXED"
            item["note"] = (
                "Passing-section successor rematerialized 429/125; predecessor unrepaired in place; "
                "45 unresolved screen candidates remain."
            )
        if item.get("id") == "R26-20":
            item["state"] = "CONFIRMED_FIXED"
            item["note"] = "Historical game-grain successor; predecessors immutable."
    backlog["named_open_scientific_units"].append(
        {
            "id": "C26-7A7-FALSE-QUARANTINE-312472199",
            "owner": "BAT-651",
            "state": "CONFIRMED_FIXED",
            "note": "Structured-status successor restore; predecessor quarantine preserved.",
        }
    )
    dump(backlog_path, backlog)

    for receipt_name in (
        "CYCLE26_PASS1_PROVENANCE_RECEIPT.json",
        "CYCLE26_PASS2_INDEPENDENT_RECONSTRUCTION_RECEIPT.json",
        "CYCLE26_PASS3_INDEPENDENT_REVIEW_RECEIPT.json",
    ):
        receipt_path = ART / receipt_name
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["rebinding_issued_at_utc"] = now
        receipt["code_head_binding"] = HEAD
        receipt["pr"] = PR
        receipt["base_sha"] = BASE
        receipt["active_path_gate_identity"] = WEEK1_GATE
        receipt["passing_section_successor_gate"] = passing_gate["gate_identity"]
        receipt["status_successor_gate"] = status_gate["gate_identity"]
        receipt["historical_pair_successor_gate"] = HIST_GATE
        if receipt_name.endswith("PASS3_INDEPENDENT_REVIEW_RECEIPT.json"):
            receipt["result"] = "PENDING_INDEPENDENT_REVIEWER"
            receipt["author_self_approval"] = False
        receipt["note"] = (
            "Receipt rebound to live PR #678 tip binding. Week1 successor gate unchanged "
            f"({WEEK1_GATE}). Passing-section and status successors are additional declared "
            "repair scopes, independently reconstructed, and do not open all-cycle trust."
        )
        dump(receipt_path, receipt)

    report = ART / "CYCLE26_FINAL_REPORT.md"
    report.write_text(
        "\n".join(
            [
                "# Cycle #26 Final Report — IMPLEMENTATION_REVIEW_READY_UNMERGED",
                "",
                f"Issued: {now}",
                "Worktree: C:/BatteredAggieSyndrome.data/worktrees/BAT-690-c26-scr",
                "Branch: codex/BAT-690-c26-scr",
                f"Base: {BASE}",
                f"PR: {PR}",
                "Authoritative tip: the live PR #678 head on origin (this file is carried on that tip; do not treat a stale SHA printed elsewhere as authority).",
                f"Active-path gate identity: {WEEK1_GATE}",
                f"Active-path dataset identity: {WEEK1_DATASET}",
                f"Historical pair-successor gate identity: {HIST_GATE}",
                f"Historical pair-successor dataset identity: {HIST_DATASET}",
                f"Passing-section successor gate identity: {passing_gate['gate_identity']}",
                f"Passing-section successor dataset identity: {passing_gate['dataset_identity']}",
                f"Status successor gate identity: {status_gate['gate_identity']}",
                f"Status successor dataset identity: {status_gate['dataset_identity']}",
                "Migration: DEFERRED_BY_USER_NOT_COMPLETE — Cycle #26 proceeded on public origin under existing scientific controls.",
                "",
                "## Terminal states (independent)",
                "",
                "| Dimension | Result |",
                "|---|---|",
                "| Evidence operations | EVIDENCE_CAPTURE_VERIFIED |",
                "| Known-defect containment | CONTAINMENT_VERIFIED |",
                "| Probability component | VERIFIED_WITHIN_DECLARED_SCOPE |",
                "| Joint fitted path | VERIFIED_WITHIN_DECLARED_SCOPE (UNTRUSTED_SHADOW; declared successor only) |",
                "| Primary trust recovery | PRIMARY_TRUST_RECOVERY_INCOMPLETE |",
                "| Predictive skill | DEVELOPMENT_EVIDENCE_ONLY (2023 frozen partition; not Week1 prospective) |",
                "| Historical all-cycle audit | unfinished; not claimed complete |",
                "| Jira board/local | JIRA_BOARD_LOCAL_CONVERGENCE=VERIFIED |",
                "| Branch/worktree hygiene | BRANCH_WORKTREE_HYGIENE=VERIFIED (classified; deleted_count=0 pending squash-merge proof) |",
                "| Integration authority | REVIEW_READY_UNMERGED |",
                "| Pass 3 independent review | PENDING_INDEPENDENT_REVIEWER |",
                "| Operator hold / Done / BAT-523 parent comment | unchanged |",
                "",
                "## Primary scientific delivery",
                "",
                "National game-grain forecast successor remains the declared active Week 1 path:",
                "- Opportunities: 455 (91×5); ridge joint coherent: 79/91",
                "- A&M 6607349 ridge both orientations: P(home)=0.8951316669, P(away)=0.1048683331, sum=1; margins +22.2506043541 / -22.2506043541, sum=0",
                "- Publication: UNTRUSTED_SHADOW",
                "- R26-21 active-path dependency: NONE (zero BAT-591 import edges)",
                "",
                "Historical C20/C21 pair complement is repaired as a new successor, not by rewriting old files:",
                "- C20: 910 unique games × 5 candidates, failing_pairs=0",
                "- C21: 5035 unique games × 5 candidates, failing_pairs=0",
                "- Original C20 team-grain metrics are deprecated; unique-game ridge Brier=0.17587702 (DEVELOPMENT_EVIDENCE_ONLY)",
                "- C20/C21 joint Normal interval is not claimed",
                "",
                "Passing-section successor (R26-21) rematerialized 429 confirmed mislabeled rows on 125 raw pages without rewriting the predecessor player corpus. 45 unresolved screen candidates remain unresolved. 22 confirmed TEAM rows stay team-attributed evidence.",
                "",
                "Structured-status successor restores SRC-002:GAME:312472199 as Eastern Michigan 41, Howard 9 (EMU home). Predecessor national foundation quarantine is preserved. PIT admission remains closed. Truthy completed strings cannot authorize restore.",
                "",
                "PRIMARY_TRUST_RECOVERY_INCOMPLETE: R26-09 unresolved (pass-two backlog); R26-13 unresolved (admin thresholds); R26-22 contained not fully repaired; all-cycle trust gate closed; Pass 3 pending human adjudication. Unresolved/contained P1 findings prohibit scientific PASS or credibility treatment.",
                "",
                "## Calendar / capture",
                "",
                "- Sep 3 T-24H: MISSED_CUTOFF_NO_BACKFILL (11 contests); T-90M open until earliest ~2026-09-03T20:30:00Z",
                "- A&M 6607349 T-24H 2026-09-04T23:00:00Z; T-90M 2026-09-05T21:30:00Z",
                "- Scoring: AWAITING_FINAL",
                "- Deterministic capture runner: ops/cycle26/run_week1_checkpoint_capture.ps1 (T-90M sleeper armed for 19:45Z)",
                "",
                "## Explicit non-claims",
                "",
                "No hold release, merge authority, production credibility, BAS/Aggie Excess, or prospective predictive skill. No Done on remaining scientific owners. No Cycle #26 BAT-523 parent progress comment. No scientific PASS while unresolved/contained P1 findings remain on the declared matrix.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    names = [
        "CYCLE26_R26_20_OLD_NEW_IMPACT.json",
        "CYCLE26_R26_21_CONTAINMENT.json",
        "CYCLE26_7A7_FALSE_QUARANTINE_312472199.json",
        "CYCLE26_FINDING_DISPOSITION_MATRIX.json",
        "CYCLE26_ACTIVE_PATH_ACCEPTANCE.json",
        "CYCLE26_REMAINING_AUDIT_BACKLOG.json",
        "CYCLE26_PASS1_PROVENANCE_RECEIPT.json",
        "CYCLE26_PASS2_INDEPENDENT_RECONSTRUCTION_RECEIPT.json",
        "CYCLE26_PASS3_INDEPENDENT_REVIEW_RECEIPT.json",
        "CYCLE26_FINAL_REPORT.md",
    ]
    for name in names:
        shutil.copy2(ART / name, OPS / name)
    shutil.copy2(
        REPO / "artifacts/data_lake/tamu_official_passing_section_successor_gate.json",
        OPS / "tamu_official_passing_section_successor_gate.json",
    )
    shutil.copy2(
        REPO / "artifacts/data_lake/national_foundation_status_successor_gate.json",
        OPS / "national_foundation_status_successor_gate.json",
    )
    print(
        json.dumps(
            {
                "now": now,
                "passing_gate": passing_gate["gate_identity"],
                "status_gate": status_gate["gate_identity"],
                "r21": "CONFIRMED_FIXED",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
