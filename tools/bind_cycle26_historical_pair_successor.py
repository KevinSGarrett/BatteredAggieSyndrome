"""Bind Cycle #26 artifacts to the historical saved-pair successor."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\BatteredAggieSyndrome.data\worktrees\BAT-690-c26-scr")
OPS = Path(r"C:\BatteredAggieSyndrome.data\ops\cycle26")
ART = REPO / "artifacts/scientific_integrity/cycle26"
HEAD = "LIVE_PR_678_TIP"


def rnd(value: float | None) -> float | None:
    return None if value is None else round(float(value), 8)


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    gate = json.loads(
        (
            REPO
            / "artifacts/experimentation/historical_saved_pair_game_grain_successor_gate.json"
        ).read_text(encoding="utf-8")
    )
    week1_focus = Path(
        r"C:\BatteredAggieSyndrome.data\canonical\week1_2026_game_grain_national_forecast_successor"
        r"\sha256\770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939"
        r"\week1_2026_game_grain_focus_contest_packet.jsonl"
    )
    am_rows = [
        json.loads(line)
        for line in week1_focus.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    am_ridge = next(
        row for row in am_rows if row["candidate_id"] == "national_margin_ridge"
    )
    am_both = {
        "contest_identity": am_ridge["contest_identity"],
        "ncaa_contest_id": am_ridge["ncaa_contest_id"],
        "home_canonical_team_id": am_ridge["home_canonical_team_id"],
        "away_canonical_team_id": am_ridge["away_canonical_team_id"],
        "probability_home": am_ridge["probability_home"],
        "probability_away": am_ridge["probability_away"],
        "probability_sum": am_ridge["probability_home"] + am_ridge["probability_away"],
        "expected_margin_home": am_ridge["expected_margin_home"],
        "expected_margin_away": am_ridge["expected_margin_away"],
        "margin_sum": am_ridge["expected_margin_home"]
        + am_ridge["expected_margin_away"],
        "joint_coherence": am_ridge["joint_coherence"],
        "publication_label": am_ridge["trust_classification"],
    }
    c20 = gate["cycles"]["20"]["metrics"]["by_candidate"]
    skill = {
        "artifact_type": "CYCLE26_PREDICTIVE_SKILL_EVIDENCE",
        "issued_at_utc": now,
        "PREDICTIVE_SKILL_EVIDENCE_STATE": "DEVELOPMENT_EVIDENCE_ONLY",
        "code_head_binding": HEAD,
        "pr": "https://github.com/KevinSGarrett/BatteredAggieSyndrome/pull/678",
        "evaluation_cohort": "FROZEN_2023_NATIONAL_DEVELOPMENT_PARTITION_GAME_GRAIN_SUCCESSOR",
        "source_gate_relative_path": "artifacts/experimentation/historical_saved_pair_game_grain_successor_gate.json",
        "source_gate_identity": gate["gate_identity"],
        "source_dataset_identity": gate["dataset_identity"],
        "source_result": gate["result"],
        "predecessor_c20_metrics_status": "DEPRECATED_INCOHERENT_TEAM_GRAIN_NOT_AUTHORITATIVE",
        "denominator": "UNIQUE_GAME_NOT_ORIENTED_ROW",
        "orientation_convention": "LEXICOGRAPHIC_FIRST_CANONICAL_TEAM_ID",
        "joint_probability_margin_interval": False,
        "cohort": {
            "unique_games": 910,
            "candidates": 5,
            "prospective_seasons_excluded": [2026],
            "protected_seasons_excluded": [2024, 2025],
            "season": 2023,
            "tamu_ridge_oriented_rows": gate["cycles"]["20"][
                "tamu_ridge_oriented_row_count"
            ],
        },
        "candidates": [
            {
                "candidate_id": row["candidate_id"],
                "unique_games": row["unique_games"],
                "brier": rnd(row["brier"]),
                "log_loss": rnd(row["log_loss"]),
                "accuracy": rnd(row["accuracy"]),
                "mean_predicted": rnd(row["mean_predicted"]),
                "observed_rate": rnd(row["observed_rate"]),
                "promoted": False,
                "authority": "DEVELOPMENT_ONLY_UNPROTECTED_CANDIDATE",
                "control_only": row["candidate_id"] == "national_base_rate",
            }
            for row in c20
        ],
        "limitations": [
            "Unique-game successor of frozen 2023 national development partition only; not Week 1 prospective skill.",
            "Original C20 team-grain metrics are deprecated because pair probabilities were not complementary.",
            "Successor probabilities are pair-normalized; ridge margins are antisymmetric projections of saved team margins.",
            "Fold-local Normal residual scale is not in the saved C20 files; no joint probability/margin/interval claim for C20/C21.",
            "Lexicographic first-team orientation makes observed_rate differ from 0.5; Brier is complementary-pair invariant.",
            "2024/2025 protected seasons excluded. No champion, promotion, BAS/Aggie Excess, or A&M-lift claim.",
            "Does not open ALL_CYCLE_SCIENTIFIC_TRUST_GATE or MERGE_AUTHORIZATION_GATE.",
        ],
        "nonclaims": {
            "future_predictive_skill": False,
            "production_credibility": False,
            "week1_outcome_tuned": False,
            "bas_or_aggie_excess": False,
            "original_c20_metrics_authoritative": False,
        },
        "week1_am_ridge_both_orientations": am_both,
    }
    (ART / "CYCLE26_PREDICTIVE_SKILL_EVIDENCE.json").write_text(
        json.dumps(skill, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    r26_20 = {
        "artifact_type": "CYCLE26_R26_20_CONTAINMENT",
        "issued_at_utc": now,
        "finding": "R26-20",
        "disposition": "CONFIRMED_FIXED",
        "owner": "BAT-693",
        "historical_payloads": "Immutable C20/C21/C25 saved pairs preserved unrepaired as deprecated evidence",
        "historical_successor": {
            "gate_identity": gate["gate_identity"],
            "dataset_identity": gate["dataset_identity"],
            "c20_failing_pairs": gate["cycles"]["20"]["failing_pairs"],
            "c21_failing_pairs": gate["cycles"]["21"]["failing_pairs"],
            "c20_unique_games_per_candidate": 910,
            "c21_unique_games_per_candidate": 5035,
            "joint_probability_margin_interval": False,
        },
        "week1_successor": {
            "gate_identity": "aa4ff84b16e9f00b1e68965cef7ea8730adc456ad16bda6ed1ff564b5bcdcb43",
            "dataset_identity": "770d25449a89f55353749c8c1f920253a509adb42a336c9c0f9dfc7dd4143939",
            "failing_pairs": 0,
            "ridge_emitted": 79,
            "oriented_rows": 158,
            "publication": "UNTRUSTED_SHADOW",
            "am_both_orientations": am_both,
        },
        "adversarial_proof": [
            "test_25_oriented_rows_use_team_probability",
            "test_25_historical_saved_pairs_are_not_cosmetically_rewritten",
            "test_32_probability_only_does_not_certify_joint_path",
            "tests/test_historical_saved_pair_game_grain_successor.py",
        ],
        "note": "Do not cosmetically renormalize old outputs; successor is the corrected path. Original C20/C21 metrics are not authoritative.",
        "code_head_binding": HEAD,
        "residual_risk": "C20/C21 joint Normal interval remains unavailable without fold-local residual scale; Week 1 joint path is separate.",
    }
    (ART / "CYCLE26_R26_20_CONTAINMENT.json").write_text(
        json.dumps(r26_20, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    matrix_path = ART / "CYCLE26_FINDING_DISPOSITION_MATRIX.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    matrix["issued_at_utc"] = now
    for entry in matrix["entries"]:
        if entry.get("id") == "R26-20":
            entry.update(
                {
                    "disposition": "CONFIRMED_FIXED",
                    "correction": (
                        "New historical game-grain successor emits complementary pairs and "
                        "antisymmetric ridge margins without rewriting C20/C21/C25 payloads; "
                        "Week 1 joint Normal successor unchanged; original team-grain metrics deprecated."
                    ),
                    "successor_gate": gate["gate_identity"],
                    "week1_successor_gate": "aa4ff84b16e9f00b1e68965cef7ea8730adc456ad16bda6ed1ff564b5bcdcb43",
                    "red_before_green_after": (
                        "tests/test_historical_saved_pair_game_grain_successor.py + "
                        "test_25_historical_saved_pairs_are_not_cosmetically_rewritten"
                    ),
                    "residual_risk": (
                        "Joint Normal interval not claimed for C20/C21; predecessor files remain as deprecated evidence."
                    ),
                    "independently_reconstructed": True,
                }
            )
    matrix_path.write_text(
        json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    acc_path = ART / "CYCLE26_ACTIVE_PATH_ACCEPTANCE.json"
    acc = json.loads(acc_path.read_text(encoding="utf-8"))
    acc["issued_at_utc"] = now
    acc["PREDICTIVE_SKILL_EVIDENCE_STATE"] = "DEVELOPMENT_EVIDENCE_ONLY"
    acc["historical_pair_successor"] = {
        "gate_identity": gate["gate_identity"],
        "dataset_identity": gate["dataset_identity"],
        "c20_failing_pairs": 0,
        "c21_failing_pairs": 0,
        "joint_probability_margin_interval": False,
    }
    acc["PRIMARY_OBJECTIVE_NOTE"] = (
        "PRIMARY_TRUST_RECOVERY_INCOMPLETE: R26-09 CONFIRMED_UNRESOLVED pass-two backlog; "
        "R26-13 admin thresholds; R26-21/R26-22 CONFIRMED_CONTAINED_NOT_FIXED; "
        "R26-20 pair complement CONFIRMED_FIXED via historical successor without rewriting predecessors. "
        "Joint Week 1 successor remains UNTRUSTED_SHADOW. Pass3 PENDING_INDEPENDENT_REVIEWER. "
        "Predictive skill is DEVELOPMENT_EVIDENCE_ONLY on unique-game C20 successor — not prospective Week1 skill."
    )
    acc["week1_am_ridge_both_orientations"] = am_both
    acc_path.write_text(
        json.dumps(acc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for name in (
        "CYCLE26_PREDICTIVE_SKILL_EVIDENCE.json",
        "CYCLE26_R26_20_CONTAINMENT.json",
        "CYCLE26_FINDING_DISPOSITION_MATRIX.json",
        "CYCLE26_ACTIVE_PATH_ACCEPTANCE.json",
    ):
        shutil.copy2(ART / name, OPS / name)
    print(
        json.dumps(
            {
                "now": now,
                "hist_gate": gate["gate_identity"],
                "am_p_sum": am_both["probability_sum"],
                "am_m_sum": am_both["margin_sum"],
                "c20_ridge_brier": rnd(
                    next(
                        row
                        for row in c20
                        if row["candidate_id"] == "national_margin_ridge"
                    )["brier"]
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
