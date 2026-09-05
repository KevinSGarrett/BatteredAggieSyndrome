"""R26-22 fitted-path temporal authority and remaining-claim census regressions."""

from __future__ import annotations

import unittest

from aggie_analytics.data.cycle26_bound_authority_pair_audit import CONSERVATIVE_BOUND
from aggie_analytics.data.cycle26_remaining_claim_census import (
    NAMED_CHECK_RECONSTRUCTED,
    NOT_AUDITED_YET,
    REMAINING_CLAIMS,
    RemainingClaimCensusError,
    validate_census,
)
from aggie_analytics.data.week1_2026_fitted_path_temporal_authority import (
    FittedPathTemporalAuthorityError,
    OBSERVED_PUBLICATION,
    assess_fitted_path_temporal_authority,
)


class FittedPathTemporalAuthorityTests(unittest.TestCase):
    def test_zero_proven_domains_yield_zero_proven_training_rows(self) -> None:
        assessment = assess_fitted_path_temporal_authority(
            authority_counts={
                OBSERVED_PUBLICATION: 0,
                "OBSERVED_EFFECTIVE_TIMESTAMP": 0,
                CONSERVATIVE_BOUND: 2,
            },
            training_row_count=90198,
            week1_trust={
                "ACTIVE_PATH_CORRECTNESS_CLAIM": False,
                "publication_label": "UNTRUSTED_SHADOW",
                "scientific_trust_gate_open": False,
                "recommended": False,
            },
        )
        self.assertEqual(assessment["proven_pit_training_row_count"], 0)
        self.assertEqual(assessment["training_row_count"], 90198)
        self.assertFalse(assessment["refit_without_proxy_pairs_possible"])
        self.assertEqual(
            assessment["primary_trust_recovery"], "PRIMARY_TRUST_RECOVERY_INCOMPLETE"
        )

    def test_active_path_correctness_claim_is_rejected(self) -> None:
        with self.assertRaises(FittedPathTemporalAuthorityError):
            assess_fitted_path_temporal_authority(
                authority_counts={
                    OBSERVED_PUBLICATION: 0,
                    "OBSERVED_EFFECTIVE_TIMESTAMP": 0,
                    CONSERVATIVE_BOUND: 2,
                },
                training_row_count=90198,
                week1_trust={
                    "ACTIVE_PATH_CORRECTNESS_CLAIM": True,
                    "publication_label": "UNTRUSTED_SHADOW",
                    "scientific_trust_gate_open": False,
                    "recommended": False,
                },
            )

    def test_recommended_or_open_trust_is_rejected(self) -> None:
        base_counts = {
            OBSERVED_PUBLICATION: 0,
            "OBSERVED_EFFECTIVE_TIMESTAMP": 0,
            CONSERVATIVE_BOUND: 2,
        }
        with self.assertRaises(FittedPathTemporalAuthorityError):
            assess_fitted_path_temporal_authority(
                authority_counts=base_counts,
                training_row_count=10,
                week1_trust={
                    "ACTIVE_PATH_CORRECTNESS_CLAIM": False,
                    "publication_label": "UNTRUSTED_SHADOW",
                    "scientific_trust_gate_open": True,
                    "recommended": False,
                },
            )
        with self.assertRaises(FittedPathTemporalAuthorityError):
            assess_fitted_path_temporal_authority(
                authority_counts=base_counts,
                training_row_count=10,
                week1_trust={
                    "ACTIVE_PATH_CORRECTNESS_CLAIM": False,
                    "publication_label": "VALIDATED",
                    "scientific_trust_gate_open": False,
                    "recommended": False,
                },
            )


class RemainingClaimCensusTests(unittest.TestCase):
    def test_census_is_nonempty_and_not_semantically_audited(self) -> None:
        validate_census(REMAINING_CLAIMS)
        self.assertGreaterEqual(len(REMAINING_CLAIMS), 31)
        self.assertTrue(
            any(row["status"] == NOT_AUDITED_YET for row in REMAINING_CLAIMS)
        )
        self.assertTrue(
            any(row["status"] == NAMED_CHECK_RECONSTRUCTED for row in REMAINING_CLAIMS)
        )
        self.assertTrue(
            all(
                not str(row["claim_id"]).startswith("C")
                or str(row["claim_id"]).startswith("NAMED-")
                or row["status"] != NAMED_CHECK_RECONSTRUCTED
                for row in REMAINING_CLAIMS
            )
        )

    def test_empty_or_complete_stamp_is_rejected(self) -> None:
        with self.assertRaises(RemainingClaimCensusError):
            validate_census(())
        forged = [
            {
                "claim_id": f"PAD-{index}",
                "cycle_id": "CYCLE-1",
                "status": NOT_AUDITED_YET,
                "remaining": "pad",
            }
            for index in range(30)
        ]
        forged.append(
            {
                "claim_id": "C01-CAPTURE-SEMANTIC-REPLAY-AND-OWNERSHIP",
                "cycle_id": "CYCLE-1",
                "status": NAMED_CHECK_RECONSTRUCTED,
                "remaining": "forged whole-cycle named check",
            }
        )
        with self.assertRaises(RemainingClaimCensusError):
            validate_census(forged)

    def test_leakage_named_check_does_not_complete_cycle_three(self) -> None:
        by_id = {row["claim_id"]: row for row in REMAINING_CLAIMS}
        self.assertEqual(
            by_id["C03-MOUNTED-14-SCENARIO-AND-LEAKAGE"]["status"],
            NOT_AUDITED_YET,
        )
        named = by_id["NAMED-C03-LEAKAGE-BATTERY-14"]
        self.assertEqual(named["status"], NAMED_CHECK_RECONSTRUCTED)
        self.assertIn(
            "2be6b713722382b2c0ea5e86f89a6e6ed57533bab3adbb0bc3cf3a77b46df13a",
            named["remaining"],
        )


if __name__ == "__main__":
    unittest.main()
