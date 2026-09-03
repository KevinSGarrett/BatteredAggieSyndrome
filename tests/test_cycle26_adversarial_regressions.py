"""Cycle #26 adversarial regressions for R26-01 through R26-26 and section 11."""

from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.protected_evaluation_replacement_protocol import (  # noqa: E402
    replacement_protocol,
)
from aggie_analytics.data.tamu_official_statcrew_preformatted import (  # noqa: E402
    parse_table_players,
)
from aggie_analytics.data.week1_2026_current_contest_binding_successor import (  # noqa: E402
    build_current_contest_row,
)
from aggie_analytics.data.week1_2026_game_grain_distribution_successor import (  # noqa: E402
    game_grain_forecast,
    oriented_rows_from_game,
)
from aggie_analytics.data.week1_2026_market_integrity_successor import (  # noqa: E402
    classify_crosswalk,
    consensus_from_quotes,
    freeze_vs_market,
)
from aggie_analytics.governance.branch_worktree_hygiene import (  # noqa: E402
    classify_branch,
    deletion_allowed,
    local_prune_is_not_remote_deletion,
)
from aggie_analytics.governance.cycle_identity import (  # noqa: E402
    CYCLE_25_5,
    CYCLE_26,
    CycleIdentityError,
    parse_cycle_identity,
    reject_cycle_collision,
)
from aggie_analytics.governance.scientific_dependency_graph import (  # noqa: E402
    circular_authority_from_edges,
    directed_cycles,
    transitive_affected,
)
from aggie_analytics.governance.scientific_trust_recovery_hold import (  # noqa: E402
    validate_hold,
)
from aggie_analytics.operations.backup import _normalize_relpath  # noqa: E402
from aggie_analytics.scientific_reference.coherence import (  # noqa: E402
    inverse_normal_cdf,
    joint_distribution_coherent,
    pair_normalize,
    standard_normal_cdf,
)
from aggie_analytics.scientific_reference.metrics import (  # noqa: E402
    brier_score,
    calibration_bins,
    log_loss,
    source_coverage,
)
from tools.validate_codex_scientific_review import (  # noqa: E402
    validate_review_outcome,
)
from tools.validate_cross_output_coherence import main as cross_output_main  # noqa: E402
from tools.validate_independent_scientific_reference import (  # noqa: E402
    validate as validate_independence,
)
from tools.validate_pr_review_finding_ledger import validate as validate_ledger  # noqa: E402
from tools.validate_raw_to_forecast_trace import (  # noqa: E402
    validate_payload as validate_trace_payload,
)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
INVARIANTS = [
    "pit_known_at",
    "target_game_exclusion",
    "current_opponent_binding",
    "game_grain_pair_coherence",
    "probability_margin_distribution_coherence",
    "immutable_forecasts",
    "protected_exposure",
    "report_artifact_agreement",
    "producer_validator_independence",
]


def _digest(paths: list[str]) -> str:
    encoded = json.dumps(sorted(paths), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _passing_review(*, verdict: str = "PASS", p0: list[str] | None = None) -> dict:
    files = ["src/aggie_analytics/data/week1_2026_game_grain_distribution_successor.py"]
    return {
        "pr_number": 700,
        "base_sha": SHA_A,
        "head_sha": SHA_B,
        "reviewed_merge_sha": SHA_C,
        "changed_file_inventory": files,
        "changed_file_digest": _digest(files),
        "review_rule_identity": "cycle26_scientific_review",
        "model": "gpt-5.4",
        "reasoning_effort": "high",
        "findings_p0": list(p0 or []),
        "findings_p1": [],
        "findings_p2": [],
        "scientific_invariants_checked": INVARIANTS,
        "critical_files_not_reviewed": [],
        "limitations": ["hosted model review is not pass 3"],
        "verdict": verdict,
    }


class Cycle26AdversarialRegressions(unittest.TestCase):
    def test_01_schema_valid_fail_is_not_merge_success(self) -> None:
        payload = _passing_review(verdict="FAIL", p0=["p0"])
        result = validate_review_outcome(
            payload,
            expected_pr=700,
            expected_base=SHA_A,
            expected_head=SHA_B,
            expected_merge=SHA_C,
            expected_files=payload["changed_file_inventory"],
        )
        self.assertTrue(result["schema_valid"])
        self.assertFalse(result["merge_success"])
        self.assertIn("CODEX_REVIEW_UNSUCCESSFUL_VERDICT:FAIL", result["merge_findings"])

    def test_01_blocked_and_unknown_are_not_merge_success(self) -> None:
        blocked = _passing_review(verdict="BLOCKED")
        blocked_result = validate_review_outcome(blocked, expected_files=blocked["changed_file_inventory"])
        self.assertTrue(blocked_result["schema_valid"])
        self.assertFalse(blocked_result["merge_success"])
        unknown = _passing_review(verdict="UNKNOWN")
        unknown_result = validate_review_outcome(unknown, expected_files=unknown["changed_file_inventory"])
        self.assertFalse(unknown_result["merge_success"])
        self.assertIn("CODEX_REVIEW_UNKNOWN_VERDICT:UNKNOWN", unknown_result["merge_findings"])

    def test_02_pr_changing_own_checker_is_rejected(self) -> None:
        payload = _passing_review()
        payload["changed_file_inventory"] = ["tools/validate_codex_scientific_review.py"]
        payload["changed_file_digest"] = _digest(payload["changed_file_inventory"])
        result = validate_review_outcome(
            payload, expected_files=payload["changed_file_inventory"]
        )
        self.assertFalse(result["merge_success"])
        self.assertIn("CODEX_REVIEW_PR_CHANGED_OWN_CHECKER", result["merge_findings"])

    def test_02_stale_head_is_rejected(self) -> None:
        payload = _passing_review()
        result = validate_review_outcome(
            payload,
            expected_head="d" * 40,
            expected_files=payload["changed_file_inventory"],
        )
        self.assertFalse(result["schema_valid"])
        self.assertIn("CODEX_REVIEW_HEAD_SHA_STALE", result["schema_findings"])

    def test_03_unscoped_release_and_missing_action_context(self) -> None:
        findings = validate_hold(
            REPO_ROOT,
            proposed_done_keys=["BAT-690"],
            proposed_merges=["scientific:unrelated"],
        )
        self.assertIn("HOLD_ACTION_CONTEXT_MISSING", findings)
        unrelated = validate_hold(
            REPO_ROOT,
            proposed_action="done",
            proposed_done_keys=["BAT-690"],
        )
        self.assertTrue(any("HOLD_" in item for item in unrelated))
        completion = validate_hold(
            REPO_ROOT,
            proposed_action="completion_claim",
            proposed_completion_claim="Cycle #26 complete",
        )
        self.assertIn("HOLD_COMPLETION_CLAIM_WHILE_ACTIVE", completion)

    def test_04_cycle_identity_collision_and_boolean_rejection(self) -> None:
        with self.assertRaises(CycleIdentityError):
            parse_cycle_identity(True)
        with self.assertRaises(CycleIdentityError):
            parse_cycle_identity(25.5)
        mapped = parse_cycle_identity(26, comment_id="14723")
        self.assertEqual(mapped.canonical_id, CYCLE_25_5)
        with self.assertRaises(CycleIdentityError):
            parse_cycle_identity(26)
        twenty_six = parse_cycle_identity(CYCLE_26)
        self.assertEqual(twenty_six.canonical_id, CYCLE_26)
        with self.assertRaises(CycleIdentityError):
            reject_cycle_collision(CYCLE_25_5, 26, right_comment_id="14723")

    def test_05_empty_null_trace_and_missing_payload(self) -> None:
        self.assertIn("TRACE_PAYLOAD_EMPTY", validate_trace_payload({}))
        findings = validate_trace_payload(
            {
                "expected_opportunity_ids": ["g1"],
                "traces": [
                    {
                        "raw_source_identity": None,
                        "raw_sha256": None,
                        "canonical_game_id": None,
                        "feature_row_identity": None,
                        "forecast_row_identity": None,
                        "known_at_utc": None,
                        "cutoff_utc": None,
                        "current_opponent_key": None,
                        "trust_classification": None,
                    }
                ],
            }
        )
        self.assertTrue(any("TRACE_NULL_ONLY" in item for item in findings))
        self.assertIn(
            "TRACE_EMPTY_UNEXPECTED_POPULATION",
            validate_trace_payload({"expected_opportunity_ids": ["g1"], "traces": []}),
        )
        self.assertEqual(cross_output_main([]), 1)

    def test_06_producer_reference_independence(self) -> None:
        self.assertEqual([], validate_independence(REPO_ROOT))

    def test_07_invalid_probability_scale_interval(self) -> None:
        broken = pair_normalize(1.2, -0.2, 1.0, -1.0)
        self.assertFalse(broken["coherent"])
        reversed_interval = joint_distribution_coherent(
            {
                "expected_margin_home": 1.0,
                "home_win_probability": 0.6,
                "interval_lower": 2.0,
                "interval_upper": -2.0,
            },
            residual_stdev=1.0,
            quantile=-2.0,
        )
        self.assertFalse(reversed_interval["coherent"])
        with self.assertRaises(ValueError):
            log_loss([0.5], [2])
        with self.assertRaises(ValueError):
            source_coverage(["false"], [False])

    def test_08_joint_distribution_uses_independent_ppf(self) -> None:
        expected = 0.0
        stdev = 1.0
        z = inverse_normal_cdf(0.975)
        result = joint_distribution_coherent(
            {
                "expected_margin_home": expected,
                "home_win_probability": 0.5,
                "interval_lower": expected - z * stdev,
                "interval_upper": expected + z * stdev,
            },
            residual_stdev=stdev,
            interval_mass=0.95,
        )
        self.assertTrue(result["coherent"])
        disagree = joint_distribution_coherent(
            {
                "expected_margin_home": expected,
                "home_win_probability": 0.5,
                "interval_lower": -1.0,
                "interval_upper": 1.0,
            },
            residual_stdev=stdev,
            interval_mass=0.95,
            quantile=1.0,
        )
        self.assertFalse(disagree["coherent"])

    def test_09_multi_game_first_match_rejected(self) -> None:
        contests = [
            {
                "contest_id": "g1",
                "home_team_key": "texas a&m",
                "away_team_key": "b",
            },
            {
                "contest_id": "g2",
                "home_team_key": "texas a&m",
                "away_team_key": "c",
            },
        ]
        first = build_current_contest_row(
            team_key="texas a&m",
            contests=contests,
            historical_priors={},
            current_conference="SEC",
            current_subdivision="FBS",
            current_rank=None,
            rank_admitted=False,
            official_2026_finals_known_before_cutoff={},
            trust_gate_open=False,
        )
        reversed_order = build_current_contest_row(
            team_key="texas a&m",
            contests=list(reversed(contests)),
            historical_priors={},
            current_conference="SEC",
            current_subdivision="FBS",
            current_rank=None,
            rank_admitted=False,
            official_2026_finals_known_before_cutoff={},
            trust_gate_open=False,
        )
        self.assertEqual(first["row_state"], "ABSTAIN_AMBIGUOUS_CURRENT_CONTEST")
        self.assertEqual(reversed_order["row_state"], "ABSTAIN_AMBIGUOUS_CURRENT_CONTEST")

    def test_10_empty_ids_do_not_match(self) -> None:
        row = build_current_contest_row(
            team_key=" ",
            contests=[{"contest_id": "g1", "home_team_key": " ", "away_team_key": "x"}],
            historical_priors={},
            current_conference=None,
            current_subdivision=None,
            current_rank=None,
            rank_admitted=False,
            official_2026_finals_known_before_cutoff={},
            trust_gate_open=False,
        )
        self.assertEqual(row["row_state"], "ABSTAIN_EMPTY_TEAM_ID")

    def test_11_market_name_date_and_made_up_source(self) -> None:
        self.assertEqual(
            classify_crosswalk(
                participants_authoritative=True,
                schedule_evidence=True,
                name_date_only=True,
            ),
            "NAME_DATE_ONLY_NOT_STRONG_IDENTITY",
        )
        self.assertEqual(
            freeze_vs_market(
                model_freeze_utc="2026-09-01T00:00:00Z",
                market_acquisition_utc="2026-09-02T00:00:00Z",
                acquisition_source="supplied_cli_time",
            ),
            "PRE_MARKET_FREEZE_NOT_PROVEN",
        )

    def test_14_sportsbook_alias_and_empty_book(self) -> None:
        consensus = consensus_from_quotes([0.1, 0.1, 0.9], ["DraftKings", "Draft Kings", "Bovada"])
        self.assertEqual(consensus["median_devigged_home"], 0.5)
        with self.assertRaises(ValueError):
            from aggie_analytics.scientific_reference.market import normalize_sportsbook

            normalize_sportsbook("")
        empty = consensus_from_quotes([0.6], [""])
        self.assertFalse(empty["usable_moneyline"])

    def test_19_author_self_adjudication_and_placeholders(self) -> None:
        findings = validate_ledger(
            {
                "independently_verified_zero_applicable_findings": False,
                "findings": [
                    {
                        "reviewer": "codex",
                        "reviewed_sha": SHA_A,
                        "finding": "p0",
                        "severity": "P0",
                        "affected_files": ["src/x.py"],
                        "implementing_author": "agent",
                        "implementation_response": "fixed",
                        "adjudicator": "agent",
                        "disposition": "FALSE_POSITIVE_PROVEN",
                        "evidence": "none",
                        "regression_test": "tests/x.py",
                        "follow_up_review_identity": "n/a",
                        "final_authority": "agent",
                    }
                ],
            }
        )
        self.assertTrue(any("LEDGER_AUTHOR_SELF_ADJUDICATION" in item for item in findings))
        self.assertTrue(any("LEDGER_PLACEHOLDER_EVIDENCE" in item for item in findings))

    def test_21_cycle_ids_not_coerced(self) -> None:
        self.assertEqual(parse_cycle_identity("CYCLE-25").canonical_id, "CYCLE-25")
        self.assertEqual(parse_cycle_identity("CYCLE-25.5").canonical_id, CYCLE_25_5)
        self.assertEqual(parse_cycle_identity("CYCLE-26").canonical_id, CYCLE_26)

    def test_23_dag_cycle_and_transitive_omission(self) -> None:
        cyclic = directed_cycles([{"from": "A", "to": "B"}, {"from": "B", "to": "A"}])
        self.assertTrue(cyclic)
        self.assertTrue(circular_authority_from_edges([{"from": "A", "to": "B"}, {"from": "B", "to": "A"}]))
        affected = transitive_affected(
            [{"from": "A", "to": "B"}, {"from": "B", "to": "C"}],
            "A",
        )
        self.assertEqual(affected, {"B", "C"})
        omitted_c = transitive_affected([{"from": "A", "to": "B"}], "A")
        self.assertEqual(omitted_c, {"B"})
        self.assertNotIn("C", omitted_c)

    def test_24_protected_protocol_rejects_truthy_string(self) -> None:
        inactive = replacement_protocol(user_approved_activation=False)
        self.assertEqual(inactive["protocol_status"], "DESIGNED_INACTIVE")
        self.assertFalse(inactive["user_approved_activation"])
        self.assertTrue(inactive["stages"])
        string_active = replacement_protocol(user_approved_activation="true")  # type: ignore[arg-type]
        self.assertEqual(string_active["protocol_status"], "DESIGNED_INACTIVE")

    def test_25_oriented_rows_use_team_probability(self) -> None:
        game = game_grain_forecast(
            contest_id="g1",
            home_team_key="texas a&m",
            away_team_key="missouri state",
            expected_margin_home=3.0,
            residual_stdev=12.0,
        )
        rows = oriented_rows_from_game(game)
        self.assertAlmostEqual(rows[0]["team_win_probability"] + rows[1]["team_win_probability"], 1.0)
        self.assertEqual(rows[1]["orientation"], "AWAY")

    def test_26_passing_header_does_not_inherit_rushing(self) -> None:
        block = "\n".join(
            [
                "Texas A&M",
                "Rushing  No.  Yds  TD",
                "Smith  12  80  1",
                "Passing  Cmp-Att-Int  Yds  TD  Int",
                "Jones  12-20-1  180  2",
                "TEAM  0  0  0",
                "Passing notes",
                "Ghost  1  1  0",
            ]
        )
        rows = parse_table_players(block)
        passing = [row for row in rows if row["stat_group"] == "passing" and not row["header_only"]]
        self.assertTrue(passing)
        self.assertEqual(passing[0]["stat_group"], "passing")
        team = [row for row in rows if row["identity_status"] == "TEAM_ATTRIBUTED"]
        self.assertTrue(team)
        ghost = [row for row in rows if row["name_raw"] == "Ghost"]
        self.assertEqual(ghost, [])

    def test_28_windows_filename_hazards(self) -> None:
        with self.assertRaises(ValueError):
            _normalize_relpath("file:stream")
        with self.assertRaises(ValueError):
            _normalize_relpath("CON")
        with self.assertRaises(ValueError):
            _normalize_relpath("NUL.txt")
        with self.assertRaises(ValueError):
            _normalize_relpath("notes.txt.")
        with self.assertRaises(ValueError):
            _normalize_relpath("notes.txt ")

    def test_29_digest_failure_is_not_p0_verdict_success(self) -> None:
        payload = _passing_review(verdict="FAIL", p0=["real-p0"])
        payload["changed_file_digest"] = "0" * 64
        result = validate_review_outcome(
            payload, expected_files=payload["changed_file_inventory"]
        )
        self.assertFalse(result["schema_valid"])
        self.assertFalse(result["merge_success"])
        self.assertIn("CODEX_REVIEW_CHANGED_FILE_DIGEST_MISMATCH", result["schema_findings"])
        self.assertNotEqual(result["schema_findings"], [])

    def test_30_inverse_normal_cdf_ppf_roundtrip(self) -> None:
        for p in (0.025, 0.5, 0.975):
            reconstructed = standard_normal_cdf(inverse_normal_cdf(p))
            self.assertAlmostEqual(reconstructed, p, places=7)
            self.assertLess(abs(reconstructed - p), 1e-8)
        tail = inverse_normal_cdf(0.975)
        self.assertAlmostEqual(tail, 1.959963984540054, places=6)

    def test_31_empty_calibration_is_null_not_zero(self) -> None:
        self.assertIsNone(brier_score([], []))
        bins = calibration_bins([0.05], [1], bin_count=10)
        empty = [row for row in bins if row["count"] == 0]
        self.assertTrue(empty)
        self.assertIsNone(empty[0]["mean_observed"])

    def test_40_age_or_missing_upstream_not_disposable(self) -> None:
        aged = classify_branch({"age_days": 400, "missing_upstream": True})
        self.assertEqual(aged, "DIVERGED_OR_UNKNOWN_BLOCKED")
        self.assertFalse(deletion_allowed({"age_days": 400}))
        closed = classify_branch({"closed_unmerged_pr": True})
        self.assertEqual(closed, "DIVERGED_OR_UNKNOWN_BLOCKED")

    def test_41_open_pr_and_dirty_worktree_not_deleted(self) -> None:
        self.assertEqual(classify_branch({"open_pr": True}), "ACTIVE_PR")
        self.assertFalse(deletion_allowed({"open_pr": True, "merged_obsolete_proven": True}))
        dirty = classify_branch({"dirty_worktree": True, "unique_unmerged": True})
        self.assertEqual(dirty, "ACTIVE_UNMERGED_WORK")

    def test_42_local_prune_is_not_remote_deletion(self) -> None:
        self.assertTrue(
            local_prune_is_not_remote_deletion(
                {"local_prune_only": True, "remote_compare_and_delete_succeeded": False}
            )
        )


if __name__ == "__main__":
    unittest.main()
