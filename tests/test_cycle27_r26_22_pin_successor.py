"""Isolated Cycle #27 R26-22 semantic pin-successor regressions."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from aggie_analytics.data.cycle26_bound_authority_pair_audit import (  # noqa: E402
    CONSERVATIVE_BOUND,
    OBSERVED_EFFECTIVE,
    OBSERVED_PUBLICATION,
    canonical_json_bytes,
    sha256_bytes,
)
from aggie_analytics.data.cycle27_r26_22_pin_successor import (  # noqa: E402
    BLOCKED_STATUS,
    C26_WEEK1_DATASET_IDENTITY,
    C26_WEEK1_GATE_IDENTITY,
    MISMATCHED_PREDECESSOR_PIN,
    PAIR_AUDIT_RELATIVE,
    PREDECESSOR_DISPOSITION_RELATIVE,
    SHADOW_CLASSIFICATION,
    R2622PinSuccessorError,
    assess_clean_slice,
    build_successor_disposition,
    reconstruct_gate_identity,
    resolve_referenced_audit_identity,
)


def _audit(body: dict) -> dict:
    payload = dict(body)
    payload["gate_identity"] = reconstruct_gate_identity(payload)
    return payload


def _trust() -> dict:
    return {
        "ACTIVE_PATH_CORRECTNESS_CLAIM": False,
        "publication_label": SHADOW_CLASSIFICATION,
        "scientific_trust_gate_open": False,
        "recommended": False,
    }


def _counts() -> dict:
    return {
        OBSERVED_PUBLICATION: 0,
        OBSERVED_EFFECTIVE: 0,
        CONSERVATIVE_BOUND: 2,
    }


class SemanticPinResolutionTests(unittest.TestCase):
    def test_declared_identity_must_reconstruct(self) -> None:
        audit = _audit(
            {
                "artifact_type": "CYCLE26_R26_22_PRIOR_TARGET_PAIR_AUDIT",
                "census": {"admitted_proxy_pairs": 3, "near_bound_pairs": 1},
            }
        )
        resolved = resolve_referenced_audit_identity(audit)
        self.assertEqual(resolved["resolved_identity"], audit["gate_identity"])
        self.assertEqual(resolved["resolution"], "SEMANTICALLY_RESOLVED")

    def test_mismatched_claimed_pin_is_rejected(self) -> None:
        audit = _audit({"artifact_type": "PAIR_AUDIT", "n": 1})
        with self.assertRaises(R2622PinSuccessorError) as raised:
            resolve_referenced_audit_identity(
                audit, claimed_identity=MISMATCHED_PREDECESSOR_PIN
            )
        self.assertIn("does not resolve the referenced audit", str(raised.exception))

    def test_manual_hash_acceptance_is_rejected(self) -> None:
        audit = _audit({"artifact_type": "PAIR_AUDIT", "n": 1})
        with self.assertRaises(R2622PinSuccessorError) as raised:
            resolve_referenced_audit_identity(audit, accept_mismatched_hash=True)
        self.assertIn("manual mismatched-hash acceptance is forbidden", str(raised.exception))

    def test_declared_identity_tamper_fails_closed(self) -> None:
        audit = _audit({"artifact_type": "PAIR_AUDIT", "n": 1})
        audit["gate_identity"] = MISMATCHED_PREDECESSOR_PIN
        with self.assertRaises(R2622PinSuccessorError):
            resolve_referenced_audit_identity(audit)


class CleanSliceHonestyTests(unittest.TestCase):
    def test_zero_proven_pit_stays_blocked(self) -> None:
        state = assess_clean_slice(
            proven_pit_training_row_count=0,
            proven_pit_domains=0,
            training_row_count=90198,
        )
        self.assertEqual(state["r26_22_status"], BLOCKED_STATUS)
        self.assertFalse(state["clean_slice_established"])
        self.assertEqual(state["proven_pit_training_row_count"], 0)

    def test_global_flag_cannot_promote_90198_rows(self) -> None:
        with self.assertRaises(R2622PinSuccessorError):
            assess_clean_slice(
                proven_pit_training_row_count=0,
                proven_pit_domains=0,
                training_row_count=90198,
                global_domain_flag_promotion=True,
            )

    def test_fabricated_whistle_timestamps_are_rejected(self) -> None:
        with self.assertRaises(R2622PinSuccessorError):
            assess_clean_slice(
                proven_pit_training_row_count=1,
                proven_pit_domains=1,
                training_row_count=10,
                fabricated_whistle_timestamps=True,
            )

    def test_zero_domains_cannot_claim_nonzero_rows(self) -> None:
        with self.assertRaises(R2622PinSuccessorError):
            assess_clean_slice(
                proven_pit_training_row_count=90198,
                proven_pit_domains=0,
                training_row_count=90198,
            )


class SuccessorDispositionTests(unittest.TestCase):
    def test_successor_binds_reconstructed_audit_not_predecessor_pin(self) -> None:
        audit = _audit(
            {
                "artifact_type": "CYCLE26_R26_22_PRIOR_TARGET_PAIR_AUDIT",
                "census": {"admitted_proxy_pairs": 7, "near_bound_pairs": 2},
                "census_source": "FIXTURE",
                "bound_epistemic_status": "CONDITIONAL_CHRONOLOGY_PROXY_NOT_UNIVERSAL_GUARANTEE",
                "active_week1_path_imports_pit_bound": False,
            }
        )
        predecessor = {
            "pair_audit_gate_identity": MISMATCHED_PREDECESSOR_PIN,
            "pair_audit_relative_path": PAIR_AUDIT_RELATIVE,
        }
        successor = build_successor_disposition(
            predecessor_disposition=predecessor,
            pair_audit=audit,
            authority_counts=_counts(),
            training_row_count=90198,
            week1_trust=_trust(),
            issued_at_utc="2026-09-04T16:45:00Z",
        )
        self.assertEqual(successor["pair_audit_gate_identity"], audit["gate_identity"])
        self.assertNotEqual(successor["pair_audit_gate_identity"], MISMATCHED_PREDECESSOR_PIN)
        self.assertEqual(
            successor["predecessor_claimed_pair_audit_gate_identity"],
            MISMATCHED_PREDECESSOR_PIN,
        )
        self.assertFalse(successor["predecessor_pin_matched_referenced_audit"])
        self.assertEqual(successor["proven_pit_training_row_count"], 0)
        self.assertEqual(successor["r26_22_status"], BLOCKED_STATUS)
        self.assertEqual(successor["publication_label"], SHADOW_CLASSIFICATION)
        self.assertEqual(
            successor["c26_week1_gate_identity_preserved"], C26_WEEK1_GATE_IDENTITY
        )
        self.assertEqual(
            successor["c26_week1_dataset_identity_preserved"],
            C26_WEEK1_DATASET_IDENTITY,
        )
        self.assertTrue(successor["predecessor_disposition_preserved_in_place"])
        reconstructed = sha256_bytes(
            canonical_json_bytes(
                {
                    key: value
                    for key, value in successor.items()
                    if key != "disposition_identity"
                }
            )
        )
        self.assertEqual(successor["disposition_identity"], reconstructed)

    def test_accept_mismatched_hash_cannot_issue_successor(self) -> None:
        audit = _audit({"artifact_type": "PAIR_AUDIT", "n": 2})
        with self.assertRaises(R2622PinSuccessorError):
            build_successor_disposition(
                predecessor_disposition={
                    "pair_audit_gate_identity": MISMATCHED_PREDECESSOR_PIN
                },
                pair_audit=audit,
                authority_counts=_counts(),
                training_row_count=90198,
                week1_trust=_trust(),
                issued_at_utc="2026-09-04T16:45:00Z",
                accept_mismatched_hash=True,
            )


class FrozenCycle26PinMismatchTests(unittest.TestCase):
    def test_committed_disposition_pin_still_mismatches_referenced_audit(self) -> None:
        audit = json.loads((REPO / PAIR_AUDIT_RELATIVE).read_text(encoding="utf-8"))
        disposition = json.loads(
            (REPO / PREDECESSOR_DISPOSITION_RELATIVE).read_text(encoding="utf-8")
        )
        reconstructed = reconstruct_gate_identity(audit)
        self.assertEqual(audit["gate_identity"], reconstructed)
        self.assertEqual(
            reconstructed,
            "e77195d8d88eea55a4af86c7a32a40f857845a89b06a495b000ad7a6666d46c7",
        )
        self.assertEqual(
            disposition["pair_audit_gate_identity"], MISMATCHED_PREDECESSOR_PIN
        )
        self.assertNotEqual(disposition["pair_audit_gate_identity"], reconstructed)

    def test_isolated_temp_files_do_not_rewrite_cycle26_artifacts(self) -> None:
        original_disp = (REPO / PREDECESSOR_DISPOSITION_RELATIVE).read_bytes()
        original_audit = (REPO / PAIR_AUDIT_RELATIVE).read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pair.json").write_bytes(original_audit)
            loaded = json.loads((root / "pair.json").read_text(encoding="utf-8"))
            resolved = resolve_referenced_audit_identity(loaded)
            self.assertEqual(resolved["resolved_identity"], reconstruct_gate_identity(loaded))
        self.assertEqual(
            (REPO / PREDECESSOR_DISPOSITION_RELATIVE).read_bytes(), original_disp
        )
        self.assertEqual((REPO / PAIR_AUDIT_RELATIVE).read_bytes(), original_audit)


if __name__ == "__main__":
    unittest.main()
