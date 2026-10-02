"""Cycle #35 continuation (20260921T055921Z), section 5.

"Qualify the exact Family B successor requested for activation. The current
qualification still exercises ledger 1b79..., while the request names
d486.... Complete the isolated successor chain and actual-validator negative
tests without activating canonical routing."

Two failures were being made at once, and these tests pin the fix for both.

The harness qualified the PREDECESSOR ledger and the request named the
SUCCESSOR, so `exercises_the_requested_successor` is asserted against the
constant rather than inferred from a run that went green.

And the old tamper probes called a function that computes hashes and raises
nothing, so both recorded ACCEPTED while reading as negative controls. The
`expect_rejection` tests below are the important ones here: a case passes
only when the real validator RAISES, and a clean return is a failure to
reject however plausible the case name.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools" / "cycle35"))

from aggie_analytics.data.tamu_official_historical_boxscores import (  # noqa: E402
    AuthorityViolation,
)
from r35_31_family_b_successor_qualification import (  # noqa: E402
    COMMITTED_PREDECESSOR_LEDGER_IDENTITY,
    REQUESTED_SUCCESSOR_LEDGER_IDENTITY,
    expect_pass,
    expect_rejection,
)

ARTIFACT = (
    Path(r"C:\BatteredAggieSyndrome.data\ops\cycle35\runs")
    / "20260921T055921Z_implementation"
    / "CYCLE35_FAMILY_B_SUCCESSOR_QUALIFICATION.json"
)


class NegativeControlSemanticsTests(unittest.TestCase):
    """A negative control that does not reject has not controlled anything."""

    def test_a_raised_authority_violation_is_a_rejection(self) -> None:
        def raises() -> None:
            raise AuthorityViolation("external rejection ledger payload mismatch")

        result = expect_rejection("TAMPERED_CHILD_SEMANTIC_REJECTED", raises)
        self.assertEqual(result["outcome"], "REJECTED")
        self.assertIn("payload mismatch", result["raised"])

    def test_a_clean_return_is_recorded_as_a_failure_to_reject(self) -> None:
        """The exact shape of the previous harness's two tamper cases: a
        value came back, nothing refused it, and it read as ACCEPTED."""

        result = expect_rejection(
            "TAMPERED_CHILD_BYTES_ONLY_REJECTED", lambda: {"union_identity": "abc"}
        )
        self.assertEqual(result["outcome"], "DID_NOT_REJECT")
        self.assertIn("accepted a case declared as a negative control", result["note"])

    def test_an_unrelated_crash_is_not_counted_as_a_rejection(self) -> None:
        """A typo that raises KeyError must not read as the validator
        refusing a tampered candidate."""

        def wrong_error() -> None:
            raise KeyError("ledger_identity")

        result = expect_rejection("MISSING_CHILD_REJECTED", wrong_error)
        self.assertEqual(result["outcome"], "DID_NOT_REJECT")
        self.assertIn("KeyError", result["detail"])

    def test_a_positive_case_that_raises_is_recorded_as_rejected(self) -> None:
        def raises() -> None:
            raise AuthorityViolation("gate does not match reconstruction")

        result = expect_pass("SUCCESSOR_VALIDATES_IN_ISOLATION", raises)
        self.assertEqual(result["outcome"], "REJECTED")

    def test_a_positive_case_that_returns_is_accepted(self) -> None:
        result = expect_pass("SUCCESSOR_VALIDATES_IN_ISOLATION", lambda: {"result": "PASS"})
        self.assertEqual(result["outcome"], "ACCEPTED")
        self.assertEqual(result["value"], {"result": "PASS"})


class IdentityBindingTests(unittest.TestCase):
    def test_the_two_identities_are_not_the_same_artifact(self) -> None:
        self.assertNotEqual(
            REQUESTED_SUCCESSOR_LEDGER_IDENTITY, COMMITTED_PREDECESSOR_LEDGER_IDENTITY
        )

    def test_the_requested_successor_is_the_one_named_in_the_request(self) -> None:
        self.assertTrue(REQUESTED_SUCCESSOR_LEDGER_IDENTITY.startswith("d48698ab"))
        self.assertTrue(COMMITTED_PREDECESSOR_LEDGER_IDENTITY.startswith("1b79f1ba"))


@unittest.skipUnless(ARTIFACT.is_file(), "qualification artifact has not been produced")
class ProducedArtifactTests(unittest.TestCase):
    """What the real run must have established, read from its artifact."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def test_it_exercised_the_requested_successor_not_the_predecessor(self) -> None:
        binding = self.payload["identity_binding"]
        self.assertEqual(
            binding["ledger_identity_exercised"], REQUESTED_SUCCESSOR_LEDGER_IDENTITY
        )
        self.assertTrue(binding["exercises_the_requested_successor"])
        self.assertTrue(binding["committed_pin_is_the_predecessor"])

    def test_the_successor_was_23_supersessions_beyond_the_predecessor(self) -> None:
        self.assertEqual(self.payload["identity_binding"]["supersession_rows"], 23)

    def test_every_negative_control_actually_rejected(self) -> None:
        self.assertEqual(self.payload["negative_controls_that_did_not_reject"], [])
        self.assertGreaterEqual(self.payload["negative_controls_declared"], 5)
        self.assertEqual(
            self.payload["negative_controls_declared"],
            self.payload["negative_controls_that_rejected"],
        )

    def test_the_inert_byte_tamper_was_refused_without_the_identity_moving(self) -> None:
        """The case R35-21 could only describe in prose."""

        case = next(
            c for c in self.payload["cases"]
            if c["case"] == "TAMPERED_CHILD_INERT_BYTES_REJECTED"
        )
        self.assertEqual(case["outcome"], "REJECTED")
        self.assertFalse(case["identity_hash_moved"])

    def test_the_successor_validated_twice_with_one_answer(self) -> None:
        self.assertTrue(self.payload["replay"]["identical"])
        for name in ("SUCCESSOR_VALIDATES_IN_ISOLATION", "SUCCESSOR_VALIDATES_ON_REPLAY"):
            case = next(c for c in self.payload["cases"] if c["case"] == name)
            self.assertEqual(case["outcome"], "ACCEPTED")

    def test_nothing_canonical_was_written(self) -> None:
        self.assertTrue(self.payload["canonical_predecessor_bytes_unchanged"])
        self.assertFalse(self.payload["canonical_activation_performed"])
        self.assertFalse(self.payload["canonical_activation_requested_by_this_tool"])
        self.assertEqual(
            self.payload["canonical_activation_state"],
            "NOT_AUTHORIZED_SEPARATE_OWNER_DECISION",
        )

    def test_the_successor_child_was_not_planted_in_the_mounted_lake(self) -> None:
        """Qualification must not leave the successor installed."""

        self.assertIsNone(
            self.payload["canonical_bytes_after"][
                "MOUNTED_SUCCESSOR_CHILD_MUST_NOT_EXIST"
            ]
        )
        self.assertFalse(
            self.payload["identity_binding"]["successor_child_existed_before_this_run"]
        )

    def test_qualified_does_not_claim_activation(self) -> None:
        self.assertTrue(self.payload["successor_qualified_in_isolation"])
        self.assertIn("does not mean", self.payload["what_qualified_means_here"])
        self.assertIn("FAIL", self.payload["mounted_family_b_lane"])


if __name__ == "__main__":
    unittest.main()
